"""
This module contains tests for the authentication API endpoints.
"""

import requests
import time
import pytest

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
        response = api_tester.session.get(f"{api_tester.base_url}/api/auth/version")
        assert response.status_code == 200, "Failed to get API version"
        version_info = response.json()
        assert "version" in version_info, "Version info missing in response"
        print(f"API Auth Version: {version_info['version']}")

    def test03_api_login(self, api_tester, app_config):
        """Tester la connexion via l'API auth"""
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        print(f"Login response status: {response.status_code}")
        print(f"Login response headers: {dict(response.headers)}")
        print(f"Login response content: {response.text}")
        
        if response.status_code != 200:
            print(f"Login failed with status {response.status_code}: {response.text}")
            assert False, f"Login failed with status {response.status_code}: {response.text}"
        
        response_json = response.json()
        print(f"Login response JSON: {response_json}")
        
        # Le token est dans les cookies, pas dans le JSON
        cookies = response.cookies
        token = cookies.get('access_token')
        
        print(f"Available cookies: {list(cookies.keys())}")
        assert token is not None, f"No access token found in cookies. Available cookies: {list(cookies.keys())}"
        print(f"Received access token from cookie: {token}")

    def test04_api_verify_token(self, api_tester, auth_token):
        """Tester la vérification du token via l'API auth"""
        assert auth_token is not None, "No auth cookies available for verify test"
        
        # Ajouter le token d'accès aux cookies de la session
        access_token = auth_token.get('access_token')
        assert access_token is not None, "No access token available"
        
        api_tester.session.cookies.set('access_token', access_token)
        
        response = api_tester.session.get(f"{api_tester.base_url}/api/auth/verify")
        
        print(f"Verify response status: {response.status_code}")
        print(f"Verify response headers: {dict(response.headers)}")
        print(f"Verify response content: {response.text}")
        
        assert response.status_code == 200, f"Token verification failed with status {response.status_code}: {response.text}"
        
        response_json = response.json()
        print(f"Verify response JSON: {response_json}")
        
        # Vérifier que la réponse contient les informations utilisateur
        assert "valid" in response_json or "user" in response_json or "email" in response_json, \
            f"Expected user info in verify response. Got: {response_json}"

    def test05_api_refresh_token(self, api_tester, auth_token):
        """Tester le rafraîchissement du token via l'API auth"""
        assert auth_token is not None, "No auth cookies available for refresh test"
        
        # Ajouter les tokens aux cookies de la session
        access_token = auth_token.get('access_token')
        refresh_token = auth_token.get('refresh_token')
        
        assert refresh_token is not None, "No refresh token available"
        
        api_tester.session.cookies.set('access_token', access_token)
        api_tester.session.cookies.set('refresh_token', refresh_token)
        
        print(f"Original access token: {access_token[:50] if access_token else None}...")
        print(f"Refresh token: {refresh_token[:50] if refresh_token else None}...")
        
        response = api_tester.session.post(f"{api_tester.base_url}/api/auth/refresh")
        
        print(f"Refresh response status: {response.status_code}")
        print(f"Refresh response headers: {dict(response.headers)}")
        print(f"Refresh response content: {response.text}")
        
        assert response.status_code == 200, f"Token refresh failed with status {response.status_code}: {response.text}"
        
        # Vérifier si un nouveau token est fourni dans les cookies
        new_cookies = response.cookies
        new_access_token = new_cookies.get('access_token')
        
        if new_access_token:
            print(f"New access token received: {new_access_token[:50]}...")
            assert new_access_token != access_token, "New access token should be different from the original"
        else:
            # Si pas de nouveau token dans les cookies, vérifier la réponse JSON
            response_json = response.json()
            print(f"Refresh response JSON: {response_json}")
            assert "message" in response_json or "access_token" in response_json, \
                f"Expected success message or new token in response. Got: {response_json}"

    def test06_api_verify_invalid_token(self, api_tester):
        """Tester la vérification avec un token invalide"""
        # Utiliser un token invalide
        invalid_token = "invalid.token.here"
        api_tester.session.cookies.set('access_token', invalid_token)
        
        response = api_tester.session.get(f"{api_tester.base_url}/api/auth/verify")
        
        print(f"Invalid token verify response status: {response.status_code}")
        print(f"Invalid token verify response content: {response.text}")
        
        # Un token invalide devrait retourner 401 ou 403
        assert response.status_code in [401, 403], \
            f"Expected 401 or 403 for invalid token, got {response.status_code}: {response.text}"

    def test07_api_logout(self, api_tester, auth_token):
        """Tester la déconnexion via l'API auth"""
        assert auth_token is not None, "No auth cookies available for logout test"
        
        # Ajouter tous les cookies d'authentification à la session
        access_token = auth_token.get('access_token')
        refresh_token = auth_token.get('refresh_token')
        
        print(f"Available auth cookies: {list(auth_token.keys())}")
        print(f"Access token: {access_token[:50] if access_token else None}...")
        print(f"Refresh token: {refresh_token[:50] if refresh_token else None}...")
        
        if access_token:
            api_tester.session.cookies.set('access_token', access_token)
        if refresh_token:
            api_tester.session.cookies.set('refresh_token', refresh_token)
        
        # Vérifier les cookies avant la requête
        print(f"Session cookies before logout: {list(api_tester.session.cookies.keys())}")
        
        response = api_tester.session.post(f"{api_tester.base_url}/api/auth/logout")
        
        print(f"Logout response status: {response.status_code}")
        print(f"Logout response headers: {dict(response.headers)}")
        print(f"Logout response content: {response.text}")
        
        assert response.status_code == 200, f"Logout failed with status {response.status_code}: {response.text}"
        
        # Vérifier que les tokens ont été supprimés des cookies
        response_json = response.json()
        print(f"Logout response JSON: {response_json}")
        
        # Les cookies peuvent être supprimés côté serveur, vérifier la réponse
        assert "message" in response_json, "No message in logout response"