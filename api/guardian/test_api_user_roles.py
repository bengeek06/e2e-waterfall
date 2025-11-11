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

class TestAPIUserRoles:
    @pytest.fixture(scope="function")
    def setup_test_data(self, api_tester, session_auth_cookies):
        """Setup: Créer les données de test nécessaires pour chaque test"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        cookies_dict = {
            'access_token': session_auth_cookies.get('access_token'),
            'refresh_token': session_auth_cookies.get('refresh_token')
        }
        
        # Récupérer user_id et company_id
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 200
        user_id = verify_response.json()['user_id']
        company_id = verify_response.json()['company_id']
        
        # Sauvegarder les cookies
        api_tester.cookies_dict = cookies_dict
        api_tester.company_id = company_id
        
        # Liste pour tracker les ressources créées à nettoyer
        created_resources = {
            'roles': [],
            'user_roles': []
        }
        
        logger.info(f"Setup test data - User: {user_id}, Company: {company_id}")
        
        yield user_id, company_id, created_resources
        
        # Cleanup: Supprimer toutes les ressources créées pendant le test
        logger.info("Starting cleanup of test resources...")
        
        # Supprimer les user-roles créés
        for user_role_id in created_resources['user_roles']:
            try:
                response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/guardian/user-roles/{user_role_id}",
                    cookies=cookies_dict
                )
                if response.status_code == 204:
                    logger.info(f"✓ Cleaned up user-role: {user_role_id}")
                else:
                    logger.warning(f"Could not cleanup user-role {user_role_id}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error cleaning up user-role {user_role_id}: {e}")
        
        # Supprimer les rôles créés
        for role_id in created_resources['roles']:
            try:
                response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/guardian/roles/{role_id}",
                    cookies=cookies_dict
                )
                if response.status_code == 204:
                    logger.info(f"✓ Cleaned up role: {role_id}")
                else:
                    logger.warning(f"Could not cleanup role {role_id}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error cleaning up role {role_id}: {e}")
        
        logger.info("Cleanup completed")

    def test01_get_user_roles_list(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /user-roles - Liste toutes les affectations user-role"""
        user_id, company_id, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/guardian/user-roles"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get user-roles response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of user-roles"
        
        logger.info(f"✅ Retrieved {len(result)} user-role assignments")

    def test02_create_user_role(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester POST /user-roles - Créer une affectation user-role"""
        user_id, company_id, resources = setup_test_data
        
        # Créer un rôle de test
        import time
        timestamp = int(time.time() * 1000)
        role_data = {
            "name": f"test_role_for_create_{timestamp}",
            "description": "Test role for user-role creation",
            "company_id": company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert role_response.status_code == 201, f"Failed to create test role: {role_response.status_code}"
        test_role = role_response.json()
        resources['roles'].append(test_role['id'])
        logger.info(f"Created test role: {test_role['id']}")
        
        # Créer l'affectation user-role
        user_role_data = {
            "user_id": user_id,
            "role_id": test_role['id'],
            "company_id": company_id
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
        assert result['company_id'] == company_id
        
        resources['user_roles'].append(result['id'])
        
        logger.info(f"✅ User-role created successfully with ID: {result['id']}")

    def test03_get_user_role_by_id(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /user-roles/{id} - Récupérer une affectation user-role par ID"""
        user_id, company_id, resources = setup_test_data
        
        # Créer un rôle de test
        import time
        timestamp = int(time.time() * 1000)
        role_data = {
            "name": f"test_role_for_get_{timestamp}",
            "company_id": company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert role_response.status_code == 201
        test_role = role_response.json()
        resources['roles'].append(test_role['id'])
        
        # Créer un user-role de test
        user_role_data = {
            "user_id": user_id,
            "role_id": test_role['id'],
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/user-roles",
            json=user_role_data,
            cookies=api_tester.cookies_dict
        )
        assert create_response.status_code == 201
        created_user_role = create_response.json()
        resources['user_roles'].append(created_user_role['id'])
        
        # Tester la récupération par ID
        url = f"{api_tester.base_url}/api/guardian/user-roles/{created_user_role['id']}"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get user-role by ID response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == created_user_role['id']
        assert 'user_id' in result
        assert 'role_id' in result
        assert 'company_id' in result
        
        logger.info(f"✅ User-role retrieved: {result}")

    def test04_get_user_roles_filtered_by_user_id(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /user-roles?user_id={id} - Filtrer par user_id"""
        user_id, company_id, resources = setup_test_data
        
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

    def test05_patch_user_role(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester PATCH /user-roles/{id} - Mise à jour partielle"""
        user_id, company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer le premier rôle
        role1_data = {
            "name": f"test_role_patch_1_{timestamp}",
            "company_id": company_id
        }
        
        role1_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role1_data,
            cookies=api_tester.cookies_dict
        )
        assert role1_response.status_code == 201
        role1 = role1_response.json()
        resources['roles'].append(role1['id'])
        
        # Créer le deuxième rôle
        role2_data = {
            "name": f"test_role_patch_2_{timestamp}",
            "company_id": company_id
        }
        
        role2_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role2_data,
            cookies=api_tester.cookies_dict
        )
        assert role2_response.status_code == 201
        role2 = role2_response.json()
        resources['roles'].append(role2['id'])
        
        # Créer un user-role avec le premier rôle
        user_role_data = {
            "user_id": user_id,
            "role_id": role1['id'],
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/user-roles",
            json=user_role_data,
            cookies=api_tester.cookies_dict
        )
        assert create_response.status_code == 201
        user_role = create_response.json()
        resources['user_roles'].append(user_role['id'])
        
        # Tester PATCH pour changer le rôle
        patch_data = {
            "role_id": role2['id']
        }
        
        url = f"{api_tester.base_url}/api/guardian/user-roles/{user_role['id']}"
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
        assert result['role_id'] == role2['id']
        
        logger.info(f"✅ User-role updated successfully to new role: {role2['id']}")

    def test06_put_user_role(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester PUT /user-roles/{id} - Remplacement complet"""
        user_id, company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer deux rôles de test
        role1_data = {
            "name": f"test_role_put_1_{timestamp}",
            "company_id": company_id
        }
        
        role1_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role1_data,
            cookies=api_tester.cookies_dict
        )
        assert role1_response.status_code == 201
        role1 = role1_response.json()
        resources['roles'].append(role1['id'])
        
        role2_data = {
            "name": f"test_role_put_2_{timestamp}",
            "company_id": company_id
        }
        
        role2_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role2_data,
            cookies=api_tester.cookies_dict
        )
        assert role2_response.status_code == 201
        role2 = role2_response.json()
        resources['roles'].append(role2['id'])
        
        # Créer un user-role avec le premier rôle
        user_role_data = {
            "user_id": user_id,
            "role_id": role1['id'],
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/user-roles",
            json=user_role_data,
            cookies=api_tester.cookies_dict
        )
        assert create_response.status_code == 201
        user_role = create_response.json()
        resources['user_roles'].append(user_role['id'])
        
        # Tester PUT pour remplacer complètement
        put_data = {
            "user_id": user_id,
            "role_id": role2['id'],
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/guardian/user-roles/{user_role['id']}"
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
        assert result['role_id'] == role2['id']
        assert result['user_id'] == user_id
        
        logger.info(f"✅ User-role fully updated successfully")

    def test07_delete_user_role(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester DELETE /user-roles/{id} - Supprimer une affectation user-role"""
        user_id, company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle de test
        role_data = {
            "name": f"test_role_delete_{timestamp}",
            "company_id": company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert role_response.status_code == 201, f"Failed to create test role: {role_response.status_code}"
        test_role = role_response.json()
        resources['roles'].append(test_role['id'])
        logger.info(f"Created test role for deletion: {test_role['id']}")
        
        # Créer un user-role de test
        user_role_data = {
            "user_id": user_id,
            "role_id": test_role['id'],
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/user-roles",
            json=user_role_data,
            cookies=api_tester.cookies_dict
        )
        assert create_response.status_code == 201, f"Failed to create user-role: {create_response.status_code}"
        user_role = create_response.json()
        user_role_id = user_role['id']
        logger.info(f"Created user-role for deletion: {user_role_id}")
        
        # Tester la suppression
        url = f"{api_tester.base_url}/api/guardian/user-roles/{user_role_id}"
        api_tester.log_request("DELETE", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.delete(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Delete user-role response status: {response.status_code}")
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ User-role deleted successfully: {user_role_id}")
        
        # Vérifier que le user-role n'existe plus
        verify_url = f"{api_tester.base_url}/api/guardian/user-roles/{user_role_id}"
        verify_response = api_tester.session.get(verify_url, cookies=api_tester.cookies_dict)
        
        assert verify_response.status_code == 404, "User-role should not exist after deletion"
        logger.info("✅ Verified user-role no longer exists")
        
        # Ne pas ajouter à resources car déjà supprimé
