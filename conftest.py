import os
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv
from pytest import fixture
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import urllib3

# Désactiver les warnings SSL pour les tests (certificats auto-signés)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.', '.env.test'))

# Configuration du logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

# Définir le niveau de log depuis l'environnement ou DEBUG par défaut
log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()

# Logger général pour conftest
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Console seulement pour le logger général
    ]
)

logger = logging.getLogger('test_api')


def get_service_logger(service_name: str) -> logging.Logger:
    """
    Crée ou récupère un logger pour un service spécifique avec son propre fichier de log
    
    Args:
        service_name: Nom du service (ex: 'auth', 'identity', 'guardian')
    
    Returns:
        Logger configuré pour le service
    """
    logger_name = f'test_api.{service_name}'
    service_logger = logging.getLogger(logger_name)
    
    # Éviter d'ajouter des handlers multiples si déjà configuré
    if not service_logger.handlers:
        log_file = log_dir / f'test_api_{service_name}.log'
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        service_logger.addHandler(file_handler)
        service_logger.addHandler(logging.StreamHandler())
        service_logger.setLevel(getattr(logging, log_level))
        service_logger.propagate = False  # Éviter la propagation au logger parent
    
    return service_logger

class TestSelectors:
    """Sélecteurs centralisés pour les tests E2E"""
    # Page d'initialisation
    INIT_COMPANY = "company"
    INIT_USER = "user"
    INIT_PASSWORD = "password"
    INIT_PASSWORD_CONFIRM = "passwordConfirm"
    INIT_SUBMIT = "submit"
    
    # Page de connexion
    LOGIN_EMAIL = "email"
    LOGIN_PASSWORD = "password"
    LOGIN_SUBMIT = "submit"
    LOGIN_ERROR = "login-error-message"  # À ajouter si nécessaire

class AppSession:
    """Classe pour maintenir l'état de session de l'application"""
    def __init__(self):
        self.is_initialized = False
        self.is_logged_in = False
        self.current_user = None
        self.cookies = []

@fixture(scope="session")
def driver():
    # Set up Chrome WebDriver using webdriver-manager with version for Chromium 140
    chrome_service = ChromeService(ChromeDriverManager(chrome_type="chromium").install())
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"  # Specify Chromium path
    options.add_argument("--headless")  # Run in headless mode for testing
    options.add_argument("--no-sandbox")  # Required for some CI environments
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument("--disable-gpu")  # Disable GPU for headless mode
    driver = webdriver.Chrome(service=chrome_service, options=options)
    
    yield driver
    
    # Teardown
    driver.quit()

@fixture(scope="session")
def app_session():
    """Fixture pour maintenir l'état de session entre les tests"""
    return AppSession()

@fixture(scope="session")
def app_config():
    """Fixture pour accéder aux variables de configuration"""
    return {
        'web_url': os.getenv('WEB_URL'),
        'company_name': os.getenv('COMPANY_NAME'),
        'login': os.getenv('LOGIN'),
        'password': os.getenv('PASSWORD')
    }


def check_service_initialized(base_url: str, service: str) -> bool:
    """
    Vérifie si un service est initialisé
    
    Args:
        base_url: URL de base de l'application (ex: http://localhost:3000)
        service: Nom du service à vérifier ('identity' ou 'guardian')
    
    Returns:
        True si le service est initialisé, False sinon
    """
    try:
        url = f"{base_url}/api/{service}/init-db"
        logger.info(f"Checking initialization status for {service}: {url}")
        response = requests.get(url, verify=False, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            initialized = data.get('initialized', False)
            logger.info(f"{service} initialization status: {initialized}")
            return initialized
        else:
            logger.warning(f"Failed to check {service} status: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error checking {service} initialization: {e}")
        return False


def initialize_services(app_config: dict) -> bool:
    """
    Initialise les services Identity et Guardian si nécessaire
    
    Args:
        app_config: Dictionnaire de configuration contenant web_url, company_name, login, password
    
    Returns:
        True si l'initialisation a réussi ou si déjà initialisé, False sinon
    """
    base_url = app_config['web_url']
    
    # Vérifier si Guardian est déjà initialisé
    if check_service_initialized(base_url, 'guardian'):
        logger.info("Application already initialized")
        return True
    
    logger.info("Application not initialized, starting initialization process...")
    
    try:
        # Étape 1: Initialiser Identity
        logger.info("Step 1: Initializing Identity service...")
        identity_url = f"{base_url}/api/identity/init-db"
        identity_payload = {
            "company": {
                "name": app_config['company_name']
            },
            "user": {
                "email": app_config['login'],
                "password": app_config['password']
            }
        }
        
        logger.info(f"Sending POST to {identity_url}")
        identity_response = requests.post(
            identity_url,
            json=identity_payload,
            headers={"Content-Type": "application/json"},
            verify=False,
            timeout=10
        )
        
        if identity_response.status_code != 201:
            logger.error(f"Identity initialization failed: {identity_response.status_code} - {identity_response.text}")
            return False
        
        identity_data = identity_response.json()
        company_id = identity_data.get('company', {}).get('id')
        user_id = identity_data.get('user', {}).get('id')
        
        logger.info(f"Identity initialized successfully - Company ID: {company_id}, User ID: {user_id}")
        
        # Étape 2: Initialiser Guardian
        logger.info("Step 2: Initializing Guardian service...")
        guardian_url = f"{base_url}/api/guardian/init-db"
        guardian_payload = {
            "company": {
                "name": app_config['company_name'],
                "company_id": company_id
            },
            "user": {
                "email": app_config['login'],
                "password": app_config['password'],
                "user_id": user_id
            }
        }
        
        logger.info(f"Sending POST to {guardian_url}")
        guardian_response = requests.post(
            guardian_url,
            json=guardian_payload,
            headers={"Content-Type": "application/json"},
            verify=False,
            timeout=10
        )
        
        if guardian_response.status_code != 201:
            logger.error(f"Guardian initialization failed: {guardian_response.status_code} - {guardian_response.text}")
            return False
        
        logger.info("Guardian initialized successfully")
        logger.info("✅ Application initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        return False


@fixture(scope="session", autouse=True)
def ensure_app_initialized(app_config):
    """
    Fixture automatique qui s'assure que l'application est initialisée avant tous les tests
    """
    logger.info("=" * 60)
    logger.info("Starting test session - checking application initialization")
    logger.info("=" * 60)
    
    if not initialize_services(app_config):
        logger.error("Failed to initialize application - tests may fail")
        # On ne lève pas d'exception pour permettre aux tests individuels de décider
    
    yield
    
    logger.info("=" * 60)
    logger.info("Test session completed")
    logger.info("=" * 60)


# Hook pytest pour ajouter un délai entre les tests (éviter 503)
def pytest_runtest_teardown(item, nextitem):
    """Ajouter un petit délai entre les tests pour éviter de surcharger le backend"""
    if nextitem is not None:
        import time
        time.sleep(0.1)  # 100ms de pause entre chaque test