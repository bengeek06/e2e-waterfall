import os
from dotenv import load_dotenv
from pytest import fixture
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.', '.env.test'))

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