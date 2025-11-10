"""
Tests for Basic I/O API - Health, Version, Config endpoints
"""
import requests
import time
import pytest
import sys
from pathlib import Path
import urllib3

# Désactiver les warnings SSL pour les tests (certificats auto-signés)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('basic_io')


class BasicIOAPITester:
    def __init__(self, app_config):
        self.session = requests.Session()
        self.base_url = app_config['web_url']
        # Ignorer les certificats auto-signés pour les tests
        self.session.verify = False
        
    def wait_for_api(self, endpoint: str, timeout: int = 120) -> bool:
        """Attendre qu'une API soit disponible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                logger.debug(f"wait_for_api - Status: {response.status_code}")
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request exception: {e}")
                pass
            time.sleep(2)
        return False
    
    def log_request(self, method: str, url: str, data: dict = None):
        """Log la requête envoyée"""
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            # Masquer les données sensibles
            safe_data = data.copy() if isinstance(data, dict) else data
            logger.debug(f">>> Request body: {safe_data}")
    
    def log_response(self, response: requests.Response):
        """Log la réponse reçue"""
        logger.debug(f"<<< RESPONSE: {response.status_code}")
        logger.debug(f"<<< Response headers: {dict(response.headers)}")
        try:
            if response.text:
                logger.debug(f"<<< Response body: {response.json()}")
        except:
            logger.debug(f"<<< Response body (raw): {response.text[:200]}")


class TestBasicIOHealth:
    """Tests de santé de l'API Basic I/O"""
    
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return BasicIOAPITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        # Attendre que l'API auth soit prête
        assert api_tester.wait_for_api("/api/auth/version"), "API Auth not ready"
        
        # Se connecter pour obtenir les tokens
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            # Retourner un dict avec les valeurs des cookies (pas l'objet cookies)
            access_token = response.cookies.get('access_token')
            refresh_token = response.cookies.get('refresh_token')
            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        return None
    
    def test01_health_check(self, api_tester):
        """Vérifier que l'API Basic I/O est accessible via /health"""
        assert api_tester.wait_for_api("/api/basic-io/health"), "Basic I/O API not reachable"
        
        url = f"{api_tester.base_url}/api/basic-io/health"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Health check failed with status {response.status_code}"
        
        health_info = response.json()
        assert "status" in health_info, "Status field missing in health response"
        assert health_info["status"] in ["healthy", "unhealthy"], "Invalid status value"
        
        logger.info(f"✅ Basic I/O API Health: {health_info['status']}")
        
        # Vérifier les champs optionnels
        if "service" in health_info:
            logger.info(f"Service: {health_info['service']}")
        if "version" in health_info:
            logger.info(f"Version: {health_info['version']}")
        if "checks" in health_info:
            logger.info(f"Checks: {health_info['checks']}")

    def test02_version(self, api_tester, auth_token):
        """Vérifier que l'API Basic I/O retourne une version avec authentification"""
        assert auth_token is not None, "Authentication token not available"
        
        url = f"{api_tester.base_url}/api/basic-io/version"
        api_tester.log_request('GET', url)
        
        # Passer les cookies directement dans la requête
        response = api_tester.session.get(url, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        version_info = response.json()
        assert "version" in version_info, "Version info missing in response"
        logger.info(f"✅ Basic I/O API Version: {version_info['version']}")


    def test03_config(self, api_tester, auth_token):
        """Vérifier l'endpoint de configuration avec authentification"""
        assert auth_token is not None, "Authentication token not available"
        
        url = f"{api_tester.base_url}/api/basic-io/config"
        api_tester.log_request('GET', url)
        
        # Passer les cookies directement dans la requête
        response = api_tester.session.get(url, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        config = response.json()
        logger.info(f"✅ Basic I/O API Config retrieved with {len(config)} fields")
        
        # Vérifier quelques champs attendus (selon la spec)
        if "env" in config:
            logger.info(f"Environment: {config['env']}")

