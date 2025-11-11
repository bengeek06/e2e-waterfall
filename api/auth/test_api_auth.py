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

class TestAPICommunication:
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

    def test04_api_verify_token(self, api_tester, session_auth_cookies):
        """Tester la vérification du token via l'API auth"""
        assert session_auth_cookies is not None, "No auth cookies available for verify test"
        
        # Ajouter le token d'accès aux cookies de la session
        access_token = session_auth_cookies.get('access_token')
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

    def test05_api_refresh_token(self, api_tester, session_auth_cookies):
        """Tester le rafraîchissement du token via l'API auth"""
        assert session_auth_cookies is not None, "No auth cookies available for refresh test"
        
        # Ajouter les tokens aux cookies de la session
        access_token = session_auth_cookies.get('access_token')
        refresh_token = session_auth_cookies.get('refresh_token')
        
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
        # Nettoyer tous les cookies existants pour éviter l'interférence avec les tests précédents
        api_tester.session.cookies.clear()
        
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

    def test07_api_logout(self, api_tester, session_auth_cookies):
        """Tester la déconnexion via l'API auth"""
        assert session_auth_cookies is not None, "No auth cookies available for logout test"
        
        # Ajouter tous les cookies d'authentification à la session
        access_token = session_auth_cookies.get('access_token')
        refresh_token = session_auth_cookies.get('refresh_token')
        
        logger.info(f"Available auth cookies: {list(session_auth_cookies.keys())}")
        
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

    def test08_api_config(self, api_tester):
        """Tester l'endpoint de configuration"""
        url = f"{api_tester.base_url}/api/auth/config"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Config response status: {response.status_code}")
        
        assert response.status_code == 200, f"Failed to get config with status {response.status_code}: {response.text}"
        
        config = response.json()
        
        # Vérifier que la réponse contient les champs attendus selon la spec
        expected_fields = ['FLASK_ENV', 'DATABASE_URL', 'LOG_LEVEL', 'USER_SERVICE_URL']
        
        for field in expected_fields:
            # Certains champs peuvent être absents selon l'environnement
            if field in config:
                logger.info(f"Config field '{field}': {config[field]}")
        
        # Au minimum FLASK_ENV devrait être présent
        assert len(config) > 0, "Config response should not be empty"
        logger.info(f"Config retrieved successfully with {len(config)} fields")

    def test09_api_login_invalid_email(self, api_tester):
        """Tester la connexion avec un email invalide"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        url = f"{api_tester.base_url}/api/auth/login"
        api_tester.log_request('POST', url, {"email": "nonexistent@example.com", "password": "***"})
        
        response = api_tester.session.post(url, json=login_data)
        api_tester.log_response(response)
        
        logger.info(f"Invalid email login response status: {response.status_code}")
        
        assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"
        
        response_json = response.json()
        assert "message" in response_json, "Expected error message in response"
        logger.info(f"Invalid credentials correctly rejected: {response_json.get('message')}")

    def test10_api_login_invalid_password(self, api_tester, app_config):
        """Tester la connexion avec un mot de passe invalide"""
        login_data = {
            "email": app_config['login'],
            "password": "wrongpassword123"
        }
        
        url = f"{api_tester.base_url}/api/auth/login"
        api_tester.log_request('POST', url, {"email": app_config['login'], "password": "***"})
        
        response = api_tester.session.post(url, json=login_data)
        api_tester.log_response(response)
        
        logger.info(f"Invalid password login response status: {response.status_code}")
        
        assert response.status_code == 401, f"Expected 401 for invalid password, got {response.status_code}"
        
        response_json = response.json()
        assert "message" in response_json, "Expected error message in response"
        logger.info(f"Invalid password correctly rejected: {response_json.get('message')}")

    def test11_api_login_missing_fields(self, api_tester):
        """Tester la connexion avec des champs manquants"""
        login_data = {
            "email": "test@example.com"
            # password manquant
        }
        
        url = f"{api_tester.base_url}/api/auth/login"
        api_tester.log_request('POST', url, login_data)
        
        response = api_tester.session.post(url, json=login_data)
        api_tester.log_response(response)
        
        logger.info(f"Missing fields login response status: {response.status_code}")
        
        # L'API retourne 401 pour champs manquants (traité comme credentials invalides)
        assert response.status_code in [400, 401, 422], \
            f"Expected 400, 401 or 422 for missing fields, got {response.status_code}"
        logger.info("Missing password correctly rejected")

    def test12_api_login_wrong_content_type(self, api_tester, app_config):
        """Tester la connexion avec un Content-Type invalide"""
        login_data = f"email={app_config['login']}&password={app_config['password']}"
        
        url = f"{api_tester.base_url}/api/auth/login"
        api_tester.log_request('POST', url)
        logger.debug(f">>> Sending form data instead of JSON")
        
        # Envoyer en form-urlencoded au lieu de JSON
        response = api_tester.session.post(
            url, 
            data=login_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        api_tester.log_response(response)
        
        logger.info(f"Wrong content-type login response status: {response.status_code}")
        
        # Devrait retourner 415 selon la spec
        assert response.status_code == 415, \
            f"Expected 415 for unsupported media type, got {response.status_code}"
        
        response_json = response.json()
        assert "message" in response_json, "Expected error message in response"
        logger.info(f"Unsupported media type correctly rejected: {response_json.get('message')}")

    def test13_api_verify_missing_token(self, api_tester):
        """Tester la vérification sans token"""
        # Créer une nouvelle session sans cookies
        temp_session = requests.Session()
        temp_session.verify = False
        
        url = f"{api_tester.base_url}/api/auth/verify"
        api_tester.log_request('GET', url)
        logger.debug(f">>> No access_token provided")
        
        response = temp_session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Missing token verify response status: {response.status_code}")
        
        # Devrait retourner 401 pour token manquant
        assert response.status_code == 401, \
            f"Expected 401 for missing token, got {response.status_code}"
        
        response_json = response.json()
        assert "message" in response_json, "Expected error message in response"
        logger.info(f"Missing token correctly rejected: {response_json.get('message')}")

    def test14_api_refresh_missing_token(self, api_tester):
        """Tester le refresh sans refresh token"""
        # Créer une nouvelle session sans cookies
        temp_session = requests.Session()
        temp_session.verify = False
        
        url = f"{api_tester.base_url}/api/auth/refresh"
        api_tester.log_request('POST', url)
        logger.debug(f">>> No refresh_token provided")
        
        response = temp_session.post(url)
        api_tester.log_response(response)
        
        logger.info(f"Missing refresh token response status: {response.status_code}")
        
        # Devrait retourner 400 selon la spec
        assert response.status_code == 400, \
            f"Expected 400 for missing refresh token, got {response.status_code}"
        
        response_json = response.json()
        assert "message" in response_json, "Expected error message in response"
        logger.info(f"Missing refresh token correctly rejected: {response_json.get('message')}")

    def test15_api_refresh_invalid_token(self, api_tester):
        """Tester le refresh avec un refresh token invalide"""
        # Utiliser un token invalide
        invalid_refresh_token = "invalid_refresh_token_123456"
        api_tester.session.cookies.set('refresh_token', invalid_refresh_token)
        
        url = f"{api_tester.base_url}/api/auth/refresh"
        api_tester.log_request('POST', url)
        logger.debug(f">>> Using invalid refresh_token: {invalid_refresh_token}")
        
        response = api_tester.session.post(url)
        api_tester.log_response(response)
        
        logger.info(f"Invalid refresh token response status: {response.status_code}")
        
        # Devrait retourner 401 pour token invalide/expiré
        assert response.status_code == 401, \
            f"Expected 401 for invalid refresh token, got {response.status_code}"
        
        response_json = response.json()
        assert "message" in response_json, "Expected error message in response"
        logger.info(f"Invalid refresh token correctly rejected: {response_json.get('message')}")

    def test16_api_logout_missing_tokens(self, api_tester):
        """Tester le logout sans tokens"""
        # Créer une nouvelle session sans cookies
        temp_session = requests.Session()
        temp_session.verify = False
        
        url = f"{api_tester.base_url}/api/auth/logout"
        api_tester.log_request('POST', url)
        logger.debug(f">>> No tokens provided")
        
        response = temp_session.post(url)
        api_tester.log_response(response)
        
        logger.info(f"Missing tokens logout response status: {response.status_code}")
        
        # Devrait retourner 400 selon la spec
        assert response.status_code == 400, \
            f"Expected 400 for missing tokens, got {response.status_code}"
        
        response_json = response.json()
        assert "message" in response_json, "Expected error message in response"
        logger.info(f"Missing tokens correctly rejected: {response_json.get('message')}")