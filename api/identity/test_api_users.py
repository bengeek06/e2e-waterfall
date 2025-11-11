import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('identity')

class TestAPIUsers:
    @pytest.fixture(scope="function")
    def setup_test_data(self, api_tester, session_auth_cookies, session_user_info):
        """Setup pour chaque test avec cleanup automatique"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        # Préparer les cookies pour les requêtes
        cookies_dict = session_auth_cookies
        api_tester.cookies_dict = cookies_dict
        api_tester.cookies_dict = cookies_dict
        
        # Récupérer user_id et company_id depuis /api/auth/verify
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 200, f"Failed to verify auth: {verify_response.text}"
        user_id = verify_response.json()['user_id']
        company_id = verify_response.json()['company_id']
        
        # Structure de tracking des ressources créées
        created_resources = {
            'roles': [],
            'user_roles': [],
            'users': []
        }
        
        logger.info(f"Setup test data - User: {user_id}, Company: {company_id}")
        
        yield user_id, company_id, cookies_dict, created_resources
        
        # Cleanup automatique à la fin du test
        logger.info("🧹 Cleaning up test resources...")
        
        # Supprimer les user-roles en premier
        for user_role_id in created_resources['user_roles']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/users/{user_id}/roles/{user_role_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted user-role: {user_role_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete user-role {user_role_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting user-role {user_role_id}: {e}")
        
        # Supprimer les roles créés
        for role_id in created_resources['roles']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/guardian/roles/{role_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted role: {role_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete role {role_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting role {role_id}: {e}")
        
        # Supprimer les users créés (si applicable)
        for user_id_to_delete in created_resources['users']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/users/{user_id_to_delete}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted user: {user_id_to_delete}")
                else:
                    logger.warning(f"⚠️ Failed to delete user {user_id_to_delete}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting user {user_id_to_delete}: {e}")
        
        logger.info("✅ Cleanup completed")

    def test01_get_users_list(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /users - Liste tous les utilisateurs"""
        user_id, company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/identity/users"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get users response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of users"
        
        logger.info(f"✅ Retrieved {len(result)} users")

    def test02_get_user_by_id(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /users/{id} - Récupérer un utilisateur par ID"""
        user_id, company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/identity/users/{user_id}"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get user by ID response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == user_id
        assert 'email' in result
        assert result['company_id'] == company_id
        
        logger.info(f"✅ User retrieved: {result['email']}")

    def test03_get_user_roles(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /users/{id}/roles - Récupérer les rôles d'un utilisateur"""
        user_id, company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/identity/users/{user_id}/roles"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get user roles response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'roles' in result, "No 'roles' key found in response"
        assert isinstance(result['roles'], list), "Roles is not a list"
        
        logger.info(f"✅ Retrieved {len(result['roles'])} roles for user")

    def test04_add_role_to_user(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester POST /users/{id}/roles - Ajouter un rôle à un utilisateur"""
        user_id, company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle de test
        role_data = {
            "name": f"test_role_identity_{timestamp}",
            "company_id": company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=cookies_dict
        )
        assert role_response.status_code == 201, f"Failed to create role: {role_response.text}"
        role = role_response.json()
        resources['roles'].append(role['id'])
        
        logger.info(f"Created test role: {role['id']}")
        
        # Ajouter le rôle à l'utilisateur
        add_role_data = {
            "role_id": role['id']
        }
        
        url = f"{api_tester.base_url}/api/identity/users/{user_id}/roles"
        api_tester.log_request("POST", url, data=add_role_data, cookies=cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=add_role_data,
            cookies=cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Add role to user response status: {response.status_code}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result, "Expected user-role ID in response"
        
        resources['user_roles'].append(result['id'])
        
        logger.info(f"✅ Role added to user successfully: {result['id']}")

    def test05_remove_role_from_user(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester DELETE /users/{id}/roles/{role_id} - Supprimer un rôle d'un utilisateur"""
        user_id, company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle de test
        role_data = {
            "name": f"test_role_remove_{timestamp}",
            "company_id": company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=cookies_dict
        )
        assert role_response.status_code == 201
        role = role_response.json()
        resources['roles'].append(role['id'])
        
        # Ajouter le rôle à l'utilisateur
        add_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/users/{user_id}/roles",
            json={"role_id": role['id']},
            cookies=cookies_dict
        )
        assert add_response.status_code == 201
        user_role = add_response.json()
        user_role_id = user_role['id']
        
        logger.info(f"Created user-role for deletion: {user_role_id}")
        
        # Tester la suppression
        url = f"{api_tester.base_url}/api/identity/users/{user_id}/roles/{user_role_id}"
        api_tester.log_request("DELETE", url, cookies=cookies_dict)
        
        response = api_tester.session.delete(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Remove role from user response status: {response.status_code}")
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Role removed from user successfully: {user_role_id}")
        
        # Ne pas ajouter à resources car déjà supprimé

        