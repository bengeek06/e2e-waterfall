"""
This module contains tests for the Guardian User-Role Management API endpoints.
Tests the complete CRUD operations for user-role assignments.
"""

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
        self.session.verify = False
        self.auth_cookies = None
    
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
        
    def set_auth_cookies(self, cookies):
        """Définir les cookies d'authentification"""
        self.auth_cookies = cookies
        for cookie in cookies:
            self.session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
        
    def wait_for_api(self, endpoint: str, timeout: int = 10) -> bool:
        """Attendre qu'une API soit disponible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                logger.debug(f"wait_for_api - Status: {response.status_code}")
                if response.status_code == 200:
                    return True
                elif response.status_code in [401, 403]:
                    logger.warning(f"Authentication issue detected: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request exception: {e}")
                pass
            time.sleep(2)
        return False

class TestAPIUserRoles:
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return APITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        assert api_tester.wait_for_api("/api/auth/version"), "API Auth not ready"
        
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
    
    @pytest.fixture(scope="class")
    def test_role(self, api_tester, auth_token):
        """Créer un rôle de test pour les tests user-role"""
        assert auth_token is not None, "No auth cookies available"
        
        cookies_dict = {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        }
        
        # Récupérer company_id
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 200
        company_id = verify_response.json()['company_id']
        
        # Créer un rôle de test
        role_data = {
            "name": "test_user_role",
            "description": "Role for user-role testing",
            "company_id": company_id
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=cookies_dict
        )
        
        assert response.status_code == 201
        role = response.json()
        
        # Sauvegarder pour cleanup
        api_tester.test_role_id = role['id']
        api_tester.company_id = company_id
        api_tester.cookies_dict = cookies_dict
        
        logger.info(f"Created test role: {role['id']}")
        
        yield role
        
        # Cleanup: supprimer le rôle de test
        api_tester.session.delete(
            f"{api_tester.base_url}/api/guardian/roles/{role['id']}",
            cookies=cookies_dict
        )
        logger.info(f"Cleaned up test role: {role['id']}")

    def test01_get_user_roles_list(self, api_tester, auth_token, test_role):
        """Tester GET /user-roles - Liste toutes les affectations user-role"""
        
        url = f"{api_tester.base_url}/api/guardian/user-roles"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get user-roles response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of user-roles"
        
        logger.info(f"✅ Retrieved {len(result)} user-role assignments")

    def test02_create_user_role(self, api_tester, auth_token, test_role):
        """Tester POST /user-roles - Créer une affectation user-role"""
        
        # Récupérer le user_id depuis le token
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=api_tester.cookies_dict
        )
        assert verify_response.status_code == 200
        user_id = verify_response.json()['user_id']
        
        user_role_data = {
            "user_id": user_id,
            "role_id": test_role['id'],
            "company_id": api_tester.company_id
        }
        
        url = f"{api_tester.base_url}/api/guardian/user-roles"
        api_tester.log_request("POST", url, data=user_role_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=user_role_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Create user-role response status: {response.status_code}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result, "Expected user-role ID in response"
        assert result['user_id'] == user_id
        assert result['role_id'] == test_role['id']
        assert result['company_id'] == api_tester.company_id
        
        # Sauvegarder l'ID pour les tests suivants
        api_tester.created_user_role_id = result['id']
        
        logger.info(f"✅ User-role created successfully with ID: {result['id']}")

    def test03_get_user_role_by_id(self, api_tester, auth_token, test_role):
        """Tester GET /user-roles/{id} - Récupérer une affectation user-role par ID"""
        assert hasattr(api_tester, 'created_user_role_id'), "No user-role ID from previous test"
        
        url = f"{api_tester.base_url}/api/guardian/user-roles/{api_tester.created_user_role_id}"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get user-role by ID response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == api_tester.created_user_role_id
        assert 'user_id' in result
        assert 'role_id' in result
        assert 'company_id' in result
        
        logger.info(f"✅ User-role retrieved: {result}")

    def test04_get_user_roles_filtered_by_user_id(self, api_tester, auth_token, test_role):
        """Tester GET /user-roles?user_id={id} - Filtrer par user_id"""
        
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=api_tester.cookies_dict
        )
        user_id = verify_response.json()['user_id']
        
        url = f"{api_tester.base_url}/api/guardian/user-roles?user_id={user_id}"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get user-roles filtered response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list)
        
        # Vérifier que tous les résultats correspondent au user_id
        for user_role in result:
            assert user_role['user_id'] == user_id
        
        logger.info(f"✅ Retrieved {len(result)} user-roles for user {user_id}")

    def test05_patch_user_role(self, api_tester, auth_token, test_role):
        """Tester PATCH /user-roles/{id} - Mise à jour partielle"""
        assert hasattr(api_tester, 'created_user_role_id'), "No user-role ID from previous test"
        
        # Créer un deuxième rôle pour le test
        role_data = {
            "name": "test_user_role_2",
            "company_id": api_tester.company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert role_response.status_code == 201
        new_role = role_response.json()
        api_tester.second_test_role_id = new_role['id']
        
        # Mettre à jour le user-role avec le nouveau role_id
        patch_data = {
            "role_id": new_role['id']
        }
        
        url = f"{api_tester.base_url}/api/guardian/user-roles/{api_tester.created_user_role_id}"
        api_tester.log_request("PATCH", url, data=patch_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.patch(
            url,
            json=patch_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Patch user-role response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['role_id'] == new_role['id']
        
        logger.info(f"✅ User-role updated successfully to new role: {new_role['id']}")

    def test06_put_user_role(self, api_tester, auth_token, test_role):
        """Tester PUT /user-roles/{id} - Remplacement complet"""
        assert hasattr(api_tester, 'created_user_role_id'), "No user-role ID from previous test"
        
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=api_tester.cookies_dict
        )
        user_id = verify_response.json()['user_id']
        
        put_data = {
            "user_id": user_id,
            "role_id": test_role['id'],  # Revenir au rôle original
            "company_id": api_tester.company_id
        }
        
        url = f"{api_tester.base_url}/api/guardian/user-roles/{api_tester.created_user_role_id}"
        api_tester.log_request("PUT", url, data=put_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.put(
            url,
            json=put_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Put user-role response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['role_id'] == test_role['id']
        assert result['user_id'] == user_id
        
        logger.info(f"✅ User-role fully updated successfully")

    def test07_delete_user_role(self, api_tester, auth_token, test_role):
        """Tester DELETE /user-roles/{id} - Supprimer une affectation user-role"""
        assert hasattr(api_tester, 'created_user_role_id'), "No user-role ID from previous test"
        
        url = f"{api_tester.base_url}/api/guardian/user-roles/{api_tester.created_user_role_id}"
        api_tester.log_request("DELETE", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.delete(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Delete user-role response status: {response.status_code}")
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ User-role deleted successfully: {api_tester.created_user_role_id}")
        
        # Cleanup du deuxième rôle de test
        if hasattr(api_tester, 'second_test_role_id'):
            api_tester.session.delete(
                f"{api_tester.base_url}/api/guardian/roles/{api_tester.second_test_role_id}",
                cookies=api_tester.cookies_dict
            )
            logger.info(f"Cleaned up second test role: {api_tester.second_test_role_id}")
        
        # Vérifier que le user-role n'existe plus
        verify_url = f"{api_tester.base_url}/api/guardian/user-roles/{api_tester.created_user_role_id}"
        verify_response = api_tester.session.get(verify_url, cookies=api_tester.cookies_dict)
        
        assert verify_response.status_code == 404, "User-role should not exist after deletion"
        logger.info("✅ Verified user-role no longer exists")
