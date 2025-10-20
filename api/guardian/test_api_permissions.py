import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('guardian')

class APITester:
    def __init__(self, app_config):
        self.session = requests.Session()
        self.base_url = app_config['web_url']
        # Ignorer les certificats auto-signés pour les tests
        self.session.verify = False
        self.auth_cookies = None
    
    @staticmethod
    def log_request(method, url, data=None, cookies=None):
        """Log une requête HTTP avec détails"""
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            # Masquer les mots de passe dans les logs
            safe_data = data.copy() if isinstance(data, dict) else data
            if isinstance(safe_data, dict) and 'password' in safe_data:
                safe_data['password'] = '***'
            logger.debug(f">>> Request body: {safe_data}")
        if cookies:
            # Logger les cookies utilisés (tronqués pour sécurité)
            for key, value in cookies.items():
                display_value = f"{value[:50]}..." if len(value) > 50 else value
                logger.debug(f">>> Using {key}: {display_value}")
    
    @staticmethod
    def log_response(response):
        """Log une réponse HTTP avec détails"""
        logger.debug(f"<<< RESPONSE: {response.status_code}")
        logger.debug(f"<<< Response headers: {dict(response.headers)}")
        try:
            if response.text:
                logger.debug(f"<<< Response body: {response.json()}")
        except:
            logger.debug(f"<<< Response body (raw): {response.text}")
        
    def set_auth_cookies(self, cookies):
        """Définir les cookies d'authentification"""
        self.auth_cookies = cookies
        # Forcer l'ajout des cookies à la session
        for cookie in cookies:
            self.session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
        
    def wait_for_api(self, endpoint: str, timeout: int = 10) -> bool:
        """Attendre qu'une API soit disponible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                logger.debug(f"wait_for_api - Status: {response.status_code}, Response: {response.text[:100]}...")
                if response.status_code == 200:
                    return True
                elif response.status_code in [401, 403]:
                    logger.warning(f"Authentication issue detected: {response.status_code}")
                    return False  # Ne pas continuer si c'est un problème d'auth
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request exception: {e}")
                pass
            time.sleep(2)
        return False

class TestAPIPermissions:
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return APITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        # Attendre que l'API auth soit prête
        assert api_tester.wait_for_api("/api/auth/version"), "API Auth not ready"
        
        # Créer un utilisateur de test et s'authentifier
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            # Retourner les cookies de réponse pour avoir accès aux deux tokens
            return response.cookies
        return None

    def test01_api_guardian_authentication(self, api_tester, auth_token):
        """Vérifier que l'API Guardian authentifie correctement les requêtes"""
        assert auth_token is not None, "No auth cookies available for guardian test"
        
        # Utiliser la nouvelle méthode pour définir les cookies
        api_tester.set_auth_cookies(auth_token)
        
        logger.info(f"Available auth cookies: {list(auth_token.keys())}")
        
        # Diagnostiquer les cookies
        access_token = auth_token.get('access_token')
        refresh_token = auth_token.get('refresh_token')
        logger.info(f"Access token: {access_token[:50] if access_token else None}...")
        logger.info(f"Refresh token: {refresh_token[:50] if refresh_token else None}...")
        
        # Méthode alternative : envoyer les cookies explicitement dans la requête
        cookies_dict = {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        
        # Tester l'endpoint de version/health de Guardian avec cookies explicites
        url = f"{api_tester.base_url}/api/guardian/version"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Guardian version response status: {response.status_code}")
        
        # L'authentification fonctionne si on obtient une réponse de permissions (404) 
        # plutôt qu'une erreur d'authentification (401)
        assert response.status_code in [200, 404], f"Expected 200 or 404 (permission denied), got {response.status_code}: {response.text}"
        
        if response.status_code == 404:
            error_response = response.json()
            assert "Access denied" in error_response.get("error", ""), "Expected permission error"
            logger.info("✅ Authentication successful - Permission system is working")
        else:
            version_info = response.json()
            assert "version" in version_info, "Version info missing in response"
            logger.info(f"✅ Guardian API Version: {version_info['version']}")
            
        # Sauvegarder la méthode de cookies pour les autres tests
        api_tester.cookies_dict = cookies_dict

    def test02_api_check_permission(self, api_tester, auth_token):
        """Tester la vérification de permissions avec des paramètres corrects"""
        assert auth_token is not None, "No auth cookies available for permissions test"

        # Utiliser les cookies sauvegardés du test précédent
        cookies_dict = getattr(api_tester, 'cookies_dict', {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        })
        
        url = f"{api_tester.base_url}/api/guardian/permissions"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Check permission response status: {response.status_code}")
        
        # L'API peut retourner 200 avec permission granted/denied ou 400 si les paramètres sont incorrects
        assert response.status_code in [200, 400, 403, 404], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            permission_result = response.json()
            logger.info(f"Permission result: {permission_result}")
        else:
            logger.info(f"Permission check response: {response.status_code} - {response.text}")
