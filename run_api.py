"""Launch api test manually - Interactive API Testing Tool

Ce script permet d'envoyer des requêtes HTTP et d'afficher les réponses de manière formatée.
"""

import os
import logging
import json
from typing import Dict, Any, Optional
import requests
import colorlog
import structlog
from dotenv import load_dotenv


class LoggerManager:
    """Gestionnaire centralisé pour la configuration du logging"""
    
    @staticmethod
    def setup_logging() -> structlog.BoundLogger:
        """Configure et retourne un logger structuré avec coloration"""
        
        # Configuration du handler coloré pour les logs standards
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(message)s',
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green', 
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'bold_red',
            }
        ))

        # Définir le niveau de log depuis l'environnement
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            log_level = "INFO"
        logging.basicConfig(level=getattr(logging, log_level), handlers=[handler])

        # Configuration de structlog pour des logs structurés
        renderer = structlog.dev.ConsoleRenderer(colors=True)
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                renderer
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        return structlog.get_logger(__name__)


class ConfigManager:
    """Gestionnaire de configuration pour l'application"""
    
    def __init__(self, env_file: str = '.env.test'):
        self.env_file = env_file
        self._config = None
        self.load_config()
    
    def load_config(self) -> None:
        """Charge la configuration depuis le fichier .env"""
        env_path = os.path.join(os.path.dirname(__file__), '.', self.env_file)
        load_dotenv(dotenv_path=env_path)
        
        self._config = {
            'web_url': os.getenv('WEB_URL'),
            'company_name': os.getenv('COMPANY_NAME'),
            'login': os.getenv('LOGIN'),
            'password': os.getenv('PASSWORD')
        }
    
    @property
    def config(self) -> Dict[str, Any]:
        """Retourne la configuration chargée"""
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de configuration"""
        return self._config.get(key, default)
    
    def display_config(self, logger: structlog.BoundLogger) -> None:
        """Affiche la configuration de manière sécurisée"""
        logger.info("Configuration loaded:")
        for key, value in self._config.items():
            # Masquer les mots de passe dans l'affichage
            display_value = "***" if key.lower() == 'password' else value
            logger.info(f"  {key}: {display_value}")


class APIClient:
    """Client HTTP pour envoyer des requêtes et afficher les réponses"""
    
    def __init__(self, config_manager: ConfigManager, logger: structlog.BoundLogger):
        self.config = config_manager
        self.logger = logger
        self.session = requests.Session()
        self.session.verify = False  # Ignorer les certificats auto-signés pour les tests
        self.is_authenticated = False
        self.auth_cookies = {}
        
    def authenticate(self) -> bool:
        """S'authentifier auprès de l'API et sauvegarder les cookies"""
        login_data = {
            "email": self.config.get('login'),
            "password": self.config.get('password')
        }
        
        try:
            self.logger.info("🔐 Starting authentication process...")
            
            # Utiliser la méthode standardisée pour l'affichage
            response = self.send_request('POST', '/api/auth/login', data=login_data)
            
            if response.status_code == 200:
                # Sauvegarder les cookies pour les requêtes futures
                self.auth_cookies = {cookie.name: cookie.value for cookie in response.cookies}
                self.is_authenticated = True
                
                # Ajouter les cookies à la session pour les requêtes automatiques
                for cookie in response.cookies:
                    self.session.cookies.set(cookie.name, cookie.value, 
                                           domain=cookie.domain, path=cookie.path)
                
                self.logger.info("✅ Authentication successful", 
                               cookies_received=list(self.auth_cookies.keys()))
                return True
            else:
                self.logger.error("❌ Authentication failed", 
                                status_code=response.status_code)
                return False
                
        except Exception as e:
            self.logger.error("❌ Authentication request failed", error=str(e))
            return False
    
    def send_request(self, method: str, endpoint: str, 
                    data: Optional[Dict] = None, 
                    params: Optional[Dict] = None) -> requests.Response:
        """Envoie une requête HTTP et affiche la réponse"""
        
        url = f"{self.config.get('web_url')}{endpoint}"
        
        # Préparer les options de la requête
        kwargs = {
            'cookies': self.auth_cookies if self.is_authenticated else None,
            'params': params,
        }
        
        if data and method.upper() in ['POST', 'PUT', 'PATCH']:
            kwargs['json'] = data
        
        try:
            # Afficher la requête
            self._display_request(method, url, data, params)
            
            # Envoyer la requête
            response = getattr(self.session, method.lower())(url, **kwargs)
            
            # Afficher la réponse
            self._display_response(response)
            
            return response
            
        except requests.RequestException as e:
            self.logger.error("Request failed", error=str(e), url=url)
            raise
    
    def _display_request(self, method: str, url: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> None:
        """Affiche la requête HTTP de manière formatée"""
        
        # En-tête de la requête
        self.logger.info("=" * 60)
        self.logger.info("Sending request", method=method.upper(), url=url, 
                       has_data=bool(data), has_params=bool(params))
        
        # Afficher les paramètres de query si présents
        if params:
            self.logger.info("Query parameters:")
            print(json.dumps(params, indent=2, ensure_ascii=False))
        
        # Afficher le body JSON si présent
        if data:
            self.logger.info("Request body (JSON):")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        
        self.logger.info("=" * 60)
    
    def _display_response(self, response: requests.Response) -> None:
        """Affiche la réponse HTTP de manière formatée"""
        
        # En-tête de la réponse
        self.logger.info("=" * 60)
        self.logger.info("HTTP RESPONSE", 
                        status_code=response.status_code,
                        url=response.url,
                        method=response.request.method)
        
        # Headers de réponse (sélection des plus importants)
        important_headers = ['content-type', 'content-length', 'set-cookie', 'location']
        response_headers = {k: v for k, v in response.headers.items() 
                          if k.lower() in important_headers}
        
        if response_headers:
            self.logger.info("Response headers:", **response_headers)
        
        # Définir la couleur en fonction du code de statut HTTP
        color_code = self._get_status_color(response.status_code)
        reset_code = '\033[0m'  # Reset de la couleur
        
        # Corps de la réponse
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                # JSON formaté avec couleur
                json_data = response.json()
                self.logger.info("Response body (JSON):")
                formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
                print(f"{color_code}{formatted_json}{reset_code}")
            else:
                # Texte brut (limité à 500 caractères) avec couleur
                text_content = response.text[:500]
                if len(response.text) > 500:
                    text_content += "... (truncated)"
                self.logger.info("Response body (Text):")
                print(f"{color_code}{text_content}{reset_code}")
                
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.logger.warning("Could not decode response body")
        
        self.logger.info("=" * 60)
        print()  # Retour chariot pour séparer les requêtes
    
    def _get_status_color(self, status_code: int) -> str:
        """Retourne le code couleur ANSI basé sur le code de statut HTTP"""
        if 200 <= status_code < 300:
            return '\033[92m'  # Vert pour les 2xx (succès)
        elif 300 <= status_code < 400:
            return '\033[94m'  # Bleu pour les 3xx (redirection)
        elif 400 <= status_code < 500:
            return '\033[93m'  # Orange/Jaune pour les 4xx (erreur client)
        elif 500 <= status_code < 600:
            return '\033[91m'  # Rouge pour les 5xx (erreur serveur)
        else:
            return '\033[95m'  # Magenta pour les autres codes


class AppSession:
    """Session principale de l'application pour les tests API interactifs"""
    
    def __init__(self):
        self.logger = LoggerManager.setup_logging()
        self.config_manager = ConfigManager()
        self.api_client = APIClient(self.config_manager, self.logger)
        
    def start(self) -> None:
        """Démarre la session interactive"""
        self.logger.info("🚀 API Testing Tool Started")
        self.config_manager.display_config(self.logger)
        self.logger.info("ℹ️  Use app.authenticate() to login before sending authenticated requests")
        self._show_help()
    
    def _show_help(self) -> None:
        """Affiche l'aide pour utiliser l'outil"""
        help_text = """
📖 Available methods:
  - authenticate() - Login to get access tokens
  - send_request(method, endpoint, data=None, params=None) - Send HTTP requests
  
📝 Examples:
  - app.authenticate()
  - app.send_request('GET', '/api/auth/version')
  - app.send_request('GET', '/api/guardian/policies')  # (after authentication)
  - app.send_request('POST', '/api/guardian/policies', {'name': 'test'})
        """
        print(help_text)
    
    def authenticate(self) -> bool:
        """Interface publique pour s'authentifier"""
        return self.api_client.authenticate()
    
    def send_request(self, method: str, endpoint: str, 
                    data: Optional[Dict] = None, 
                    params: Optional[Dict] = None) -> requests.Response:
        """Interface publique pour envoyer des requêtes"""
        return self.api_client.send_request(method, endpoint, data, params)
    
    def initialize_services(self) -> bool:
        """Initialise les services Identity et Guardian si nécessaire"""
        try:
            # Vérifier l'état d'initialisation de Guardian
            response = self.send_request('GET', '/api/guardian/init-app')
            if response.json().get('initialized'):
                self.logger.info("Guardian service is already initialized")
                return True
            
            self.logger.warning("Guardian service is NOT initialized")
            
            # Initialiser le service Identity d'abord
            identity_params = {
                "company": {
                    "name": self.config_manager.get('company_name')
                },
                "user": {
                    "email": self.config_manager.get('login'),
                    "password": self.config_manager.get('password')
                }
            }
            
            self.logger.info("Initializing Identity service...")
            identity_response = self.send_request('POST', '/api/identity/init-app', data=identity_params)
            
            if identity_response.status_code != 201:
                self.logger.error("❌ Failed to initialize Identity service")
                return False
            
            self.logger.info("✅ Identity service initialized successfully")
            
            # Initialiser le service Guardian avec les données de l'Identity
            identity_data = identity_response.json()
            guardian_params = {
                "company": {
                    "name": self.config_manager.get('company_name'),
                    "id": identity_data.get('company', {}).get('id')
                },
                "user": {
                    "id": identity_data.get('user', {}).get('id'),
                    "email": self.config_manager.get('login'),
                    "password": self.config_manager.get('password')
                }
            }
            
            self.logger.info("Initializing Guardian service...")
            guardian_response = self.send_request('POST', '/api/guardian/init-app', data=guardian_params)
            
            if guardian_response.status_code == 201:
                self.logger.info("✅ Guardian service initialized successfully")
                return True
            else:
                self.logger.error("❌ Failed to initialize Guardian service")
                return False
                
        except Exception as e:
            self.logger.error("Error during services initialization", error=str(e))
            return False


def main():
    """Point d'entrée principal"""
    app = AppSession()
    app.start()
    
    try:
        # Vérifier le statut des services
        app.send_request('GET', '/api/auth/version')
        app.send_request('GET', '/api/auth/health')
        
        # Initialiser les services si nécessaire
        if app.initialize_services():
            app.logger.info("🎉 All services are ready!")
            
            # Authentification maintenant que les services sont prêts
            app.logger.info("🔑 Testing authentication...")
            if app.authenticate():
                app.logger.info("🎉 Authentication successful - ready for authenticated requests!")
            else:
                app.logger.warning("⚠️ Authentication failed")
                raise Exception("Authentication failed")
        else:
            app.logger.warning("⚠️ Some services failed to initialize")
            raise Exception("Service initialization failed")
        
        # Check guardian service
        app.send_request('GET', '/api/guardian/version')
        app.send_request('GET', '/api/guardian/health')
        
        # Check identity status
        app.send_request('GET', '/api/identity/version')
        app.send_request('GET', '/api/identity/health')
        

    except Exception as e:
        app.logger.error("Error during example requests", error=str(e))
    
    app.logger.info("🏁 Session completed - app object is ready for interactive use")


if __name__ == "__main__":
    main()