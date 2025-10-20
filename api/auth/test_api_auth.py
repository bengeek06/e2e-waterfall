"""
This module contains tests for the authentication API endpoints.
"""

import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('auth')

class APITester:
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
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        return False
    
    def log_request(self, method: str, url: str, data: dict = None):
        """Log la requête envoyée"""
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            logger.debug(f">>> Request body: {data}")
    
    def log_response(self, response: requests.Response):
        """Log la réponse reçue"""
        logger.debug(f"<<< RESPONSE: {response.status_code}")
        logger.debug(f"<<< Response headers: {dict(response.headers)}")
        try:
            response_json = response.json()
            logger.debug(f"<<< Response body: {response_json}")
        except:
            logger.debug(f"<<< Response body (text): {response.text[:200]}")

class TestAPICommunication:
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
    
    def test01_api_health_check(self, api_tester):
        """Vérifier que l'API auth est accessible"""
        assert api_tester.wait_for_api("/api/auth/health"), "API Auth not reachable"

    def test02_api_version(self, api_tester):
        """Vérifier que l'API auth retourne une version"""
        url = f"{api_tester.base_url}/api/auth/version"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        assert response.status_code == 200, "Failed to get API version"
        version_info = response.json()
        assert "version" in version_info, "Version info missing in response"
        logger.info(f"API Auth Version: {version_info['version']}")

    def test03_api_login(self, api_tester, app_config):
        """Tester la connexion via l'API auth"""
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        url = f"{api_tester.base_url}/api/auth/login"
        api_tester.log_request('POST', url, {"email": app_config['login'], "password": "***"})
        
        response = api_tester.session.post(url, json=login_data)
        api_tester.log_response(response)
        
        logger.info(f"Login response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Login failed with status {response.status_code}: {response.text}")
            assert False, f"Login failed with status {response.status_code}: {response.text}"
        
        response_json = response.json()
        
        # Le token est dans les cookies, pas dans le JSON
        cookies = response.cookies
        token = cookies.get('access_token')
        
        logger.info(f"Available cookies: {list(cookies.keys())}")
        assert token is not None, f"No access token found in cookies. Available cookies: {list(cookies.keys())}"
        logger.info(f"Received access token from cookie: {token[:50]}...")

    def test04_api_verify_token(self, api_tester, auth_token):
        """Tester la vérification du token via l'API auth"""
        assert auth_token is not None, "No auth cookies available for verify test"
        
        # Ajouter le token d'accès aux cookies de la session
        access_token = auth_token.get('access_token')
        assert access_token is not None, "No access token available"
        
        api_tester.session.cookies.set('access_token', access_token)
        
        url = f"{api_tester.base_url}/api/auth/verify"
        api_tester.log_request('GET', url)
        logger.debug(f">>> Using access_token: {access_token[:50]}...")
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Verify response status: {response.status_code}")
        
        assert response.status_code == 200, f"Token verification failed with status {response.status_code}: {response.text}"
        
        response_json = response.json()
        
        # Vérifier que la réponse contient les informations utilisateur
        assert "valid" in response_json or "user" in response_json or "email" in response_json, \
            f"Expected user info in verify response. Got: {response_json}"
        logger.info("Token verified successfully")

    def test05_api_refresh_token(self, api_tester, auth_token):
        """Tester le rafraîchissement du token via l'API auth"""
        assert auth_token is not None, "No auth cookies available for refresh test"
        
        # Ajouter les tokens aux cookies de la session
        access_token = auth_token.get('access_token')
        refresh_token = auth_token.get('refresh_token')
        
        assert refresh_token is not None, "No refresh token available"
        
        api_tester.session.cookies.set('access_token', access_token)
        api_tester.session.cookies.set('refresh_token', refresh_token)
        
        logger.info(f"Original access token: {access_token[:50] if access_token else None}...")
        logger.info(f"Refresh token: {refresh_token[:50] if refresh_token else None}...")
        
        url = f"{api_tester.base_url}/api/auth/refresh"
        api_tester.log_request('POST', url)
        logger.debug(f">>> Using refresh_token: {refresh_token[:50]}...")
        
        response = api_tester.session.post(url)
        api_tester.log_response(response)
        
        logger.info(f"Refresh response status: {response.status_code}")
        
        assert response.status_code == 200, f"Token refresh failed with status {response.status_code}: {response.text}"
        
        # Vérifier si un nouveau token est fourni dans les cookies
        new_cookies = response.cookies
        new_access_token = new_cookies.get('access_token')
        
        if new_access_token:
            logger.info(f"New access token received: {new_access_token[:50]}...")
            logger.debug(f">>> New access_token full: {new_access_token}")
            assert new_access_token != access_token, "New access token should be different from the original"
        else:
            # Si pas de nouveau token dans les cookies, vérifier la réponse JSON
            response_json = response.json()
            assert "message" in response_json or "access_token" in response_json, \
                f"Expected success message or new token in response. Got: {response_json}"
        
        logger.info("Token refreshed successfully")

    def test06_api_verify_invalid_token(self, api_tester):
        """Tester la vérification avec un token invalide"""
        # Utiliser un token invalide
        invalid_token = "invalid.token.here"
        api_tester.session.cookies.set('access_token', invalid_token)
        
        url = f"{api_tester.base_url}/api/auth/verify"
        api_tester.log_request('GET', url)
        logger.debug(f">>> Using invalid access_token: {invalid_token}")
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Invalid token verify response status: {response.status_code}")
        
        # Un token invalide devrait retourner 401 ou 403
        assert response.status_code in [401, 403], \
            f"Expected 401 or 403 for invalid token, got {response.status_code}: {response.text}"
        logger.info("Invalid token correctly rejected")

    def test07_api_logout(self, api_tester, auth_token):
        """Tester la déconnexion via l'API auth"""
        assert auth_token is not None, "No auth cookies available for logout test"
        
        # Ajouter tous les cookies d'authentification à la session
        access_token = auth_token.get('access_token')
        refresh_token = auth_token.get('refresh_token')
        
        logger.info(f"Available auth cookies: {list(auth_token.keys())}")
        
        if access_token:
            api_tester.session.cookies.set('access_token', access_token)
        if refresh_token:
            api_tester.session.cookies.set('refresh_token', refresh_token)
        
        url = f"{api_tester.base_url}/api/auth/logout"
        api_tester.log_request('POST', url)
        logger.debug(f">>> Using access_token: {access_token[:50] if access_token else None}...")
        logger.debug(f">>> Using refresh_token: {refresh_token[:50] if refresh_token else None}...")
        
        response = api_tester.session.post(url)
        api_tester.log_response(response)
        
        logger.info(f"Logout response status: {response.status_code}")
        
        assert response.status_code == 200, f"Logout failed with status {response.status_code}: {response.text}"
        
        # Vérifier que les tokens ont été supprimés des cookies
        response_json = response.json()
        
        # Les cookies peuvent être supprimés côté serveur, vérifier la réponse
        assert "message" in response_json, "No message in logout response"
        logger.info("Logout successful")