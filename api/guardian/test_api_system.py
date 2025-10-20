"""
This module contains tests for the Guardian System API endpoints.
Tests health, version, config, and init-db endpoints.
"""

import requests
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
    
    @staticmethod
    def log_request(method, url, data=None, cookies=None):
        """Log une requête HTTP avec détails"""
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            safe_data = data.copy() if isinstance(data, dict) else data
            if isinstance(safe_data, dict) and 'password' in safe_data:
                safe_data['password'] = '***'
            logger.debug(f">>> Request body: {safe_data}")
        if cookies:
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

class TestAPISystem:
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return APITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification pour les endpoints protégés"""
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            return response.cookies
        return None

    def test01_health_check(self, api_tester):
        """Tester l'endpoint /health (sans authentification)"""
        
        url = f"{api_tester.base_url}/api/guardian/health"
        api_tester.log_request("GET", url)
        
        response = api_tester.session.get(url)
        
        api_tester.log_response(response)
        logger.info(f"Health check response status: {response.status_code}")
        
        # L'endpoint health devrait toujours retourner 200 ou 503
        assert response.status_code in [200, 503], f"Expected 200 or 503, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'status' in result, "Missing status field"
        assert 'service' in result, "Missing service field"
        assert 'timestamp' in result, "Missing timestamp field"
        assert 'version' in result, "Missing version field"
        assert 'environment' in result, "Missing environment field"
        
        # Vérifier le statut
        assert result['status'] in ['healthy', 'unhealthy']
        assert result['service'] == 'guardian_service'
        
        # Vérifier les checks de santé
        if 'checks' in result:
            assert 'database' in result['checks']
            db_check = result['checks']['database']
            assert 'healthy' in db_check
            logger.info(f"Database health: {db_check}")
        
        logger.info(f"✅ Guardian service status: {result['status']}, environment: {result['environment']}")

    def test02_version_endpoint(self, api_tester, auth_token):
        """Tester l'endpoint /version"""
        assert auth_token is not None, "No auth cookies available"
        
        cookies_dict = {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        }
        
        url = f"{api_tester.base_url}/api/guardian/version"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Version response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'version' in result, "Missing version field"
        
        logger.info(f"✅ Guardian API version: {result['version']}")

    def test03_config_endpoint(self, api_tester, auth_token):
        """Tester l'endpoint /config"""
        assert auth_token is not None, "No auth cookies available"
        
        cookies_dict = {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        }
        
        url = f"{api_tester.base_url}/api/guardian/config"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Config response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        # L'API retourne FLASK_ENV au lieu de env
        assert 'FLASK_ENV' in result or 'env' in result, "Missing environment field"
        
        env_value = result.get('FLASK_ENV') or result.get('env')
        logger.info(f"✅ Config - Environment: {env_value}")
        logger.info(f"Config details: {result}")

    def test04_init_db_get_status(self, api_tester):
        """Tester GET /init-db pour vérifier le statut d'initialisation"""
        
        url = f"{api_tester.base_url}/api/guardian/init-db"
        api_tester.log_request("GET", url)
        
        response = api_tester.session.get(url)
        
        api_tester.log_response(response)
        logger.info(f"Init-db status response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'initialized' in result, "Missing initialized field"
        assert isinstance(result['initialized'], bool)
        
        logger.info(f"✅ Database initialized: {result['initialized']}")

    def test05_init_db_already_initialized(self, api_tester):
        """Tester POST /init-db quand la DB est déjà initialisée"""
        
        url = f"{api_tester.base_url}/api/guardian/init-db"
        api_tester.log_request("POST", url)
        
        response = api_tester.session.post(url)
        
        api_tester.log_response(response)
        logger.info(f"Init-db POST response status: {response.status_code}")
        
        # Si déjà initialisé, peut retourner 200, 403 ou 409
        assert response.status_code in [200, 403, 409], f"Expected 200, 403 or 409, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'message' in result or 'initialized' in result
        
        if response.status_code in [403, 409]:
            assert 'already initialized' in result['message'].lower()
            logger.info(f"✅ Database already initialized (expected): {result['message']}")
        else:  # 200
            logger.info(f"✅ Database initialization confirmed: {result}")
