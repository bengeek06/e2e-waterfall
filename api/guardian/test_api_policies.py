import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('guardian')

class TestAPIPolicies:
    @pytest.fixture(scope="function")
    def setup_test_data(self, api_tester, session_auth_cookies):
        """Setup pour chaque test avec cleanup automatique"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        # Préparer les cookies pour les requêtes
        cookies_dict = {
            'access_token': session_auth_cookies['access_token'],
            'refresh_token': session_auth_cookies['refresh_token']
        }
        api_tester.cookies_dict = cookies_dict
        
        # Récupérer company_id depuis /api/auth/verify
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 200, f"Failed to verify auth: {verify_response.text}"
        company_id = verify_response.json()['company_id']
        
        # Structure de tracking des ressources créées
        created_resources = {
            'policies': [],
            'permissions': [],
            'policy_permissions': []  # (policy_id, permission_id)
        }
        
        yield company_id, cookies_dict, created_resources
        
        # Cleanup automatique à la fin du test
        logger.info("🧹 Cleaning up test resources...")
        
        # Supprimer les associations policy-permission en premier
        for policy_id, permission_id in created_resources['policy_permissions']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/guardian/policies/{policy_id}/permissions/{permission_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted policy-permission association: {policy_id}/{permission_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete policy-permission {policy_id}/{permission_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting policy-permission {policy_id}/{permission_id}: {e}")
        
        # Supprimer les policies
        for policy_id in created_resources['policies']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/guardian/policies/{policy_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted policy: {policy_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete policy {policy_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting policy {policy_id}: {e}")
        
        # Supprimer les permissions (si le test en a créées)
        for permission_id in created_resources['permissions']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/guardian/permissions/{permission_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted permission: {permission_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete permission {permission_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting permission {permission_id}: {e}")
        
        logger.info("✅ Cleanup completed")

    def test01_get_policies_list(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /policies - Liste toutes les policies"""
        company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/guardian/policies"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get policies response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of policies"
        
        logger.info(f"✅ Retrieved {len(result)} policies")

    def test02_create_policy(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester POST /policies - Créer une policy"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        policy_data = {
            "name": f"test_policy_create_{timestamp}",
            "description": "Test policy for creation",
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/guardian/policies"
        api_tester.log_request("POST", url, data=policy_data, cookies=cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=policy_data,
            cookies=cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Create policy response status: {response.status_code}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result, "Expected policy ID in response"
        assert result['name'] == policy_data['name']
        assert result['company_id'] == company_id
        
        resources['policies'].append(result['id'])
        
        logger.info(f"✅ Policy created successfully with ID: {result['id']}")

    def test03_get_policy_by_id(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /policies/{id} - Récupérer une policy par ID"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une policy de test
        policy_data = {
            "name": f"test_policy_get_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        created_policy = create_response.json()
        resources['policies'].append(created_policy['id'])
        
        # Tester la récupération par ID
        url = f"{api_tester.base_url}/api/guardian/policies/{created_policy['id']}"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get policy by ID response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == created_policy['id']
        assert result['name'] == policy_data['name']
        
        logger.info(f"✅ Policy retrieved: {result}")

    def test04_patch_policy(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester PATCH /policies/{id} - Mise à jour partielle d'une policy"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une policy de test
        policy_data = {
            "name": f"test_policy_patch_{timestamp}",
            "description": "Original description",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        policy = create_response.json()
        resources['policies'].append(policy['id'])
        
        # Tester PATCH pour modifier seulement le nom
        patch_data = {
            "name": f"patched_policy_{timestamp}"
        }
        
        url = f"{api_tester.base_url}/api/guardian/policies/{policy['id']}"
        api_tester.log_request("PATCH", url, data=patch_data, cookies=cookies_dict)
        
        response = api_tester.session.patch(
            url,
            json=patch_data,
            cookies=cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Patch policy response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == patch_data['name']
        assert result['description'] == policy_data['description']  # Description non modifiée
        
        logger.info(f"✅ Policy patched successfully")

    def test05_put_policy(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester PUT /policies/{id} - Remplacement complet d'une policy"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une policy de test
        policy_data = {
            "name": f"test_policy_put_{timestamp}",
            "description": "Original description",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        policy = create_response.json()
        resources['policies'].append(policy['id'])
        
        # Tester PUT pour remplacer complètement
        put_data = {
            "name": f"updated_policy_{timestamp}",
            "description": "Updated description",
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/guardian/policies/{policy['id']}"
        api_tester.log_request("PUT", url, data=put_data, cookies=cookies_dict)
        
        response = api_tester.session.put(
            url,
            json=put_data,
            cookies=cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Put policy response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == put_data['name']
        assert result['description'] == put_data['description']
        
        logger.info(f"✅ Policy updated successfully")

    def test06_add_permission_to_policy(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester POST /policies/{id}/permissions - Ajouter une permission à une policy"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une policy de test
        policy_data = {
            "name": f"test_policy_perm_{timestamp}",
            "company_id": company_id
        }
        
        policy_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=cookies_dict
        )
        assert policy_response.status_code == 201
        policy = policy_response.json()
        resources['policies'].append(policy['id'])
        
        # Récupérer une permission existante
        permissions_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/permissions",
            cookies=cookies_dict
        )
        assert permissions_response.status_code == 200
        permissions = permissions_response.json()
        assert len(permissions) > 0, "No permissions available for testing"
        
        permission_id = permissions[0]['id']
        
        # Ajouter la permission à la policy
        add_permission_data = {
            "permission_id": permission_id
        }
        
        url = f"{api_tester.base_url}/api/guardian/policies/{policy['id']}/permissions"
        api_tester.log_request("POST", url, data=add_permission_data, cookies=cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=add_permission_data,
            cookies=cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Add permission to policy response status: {response.status_code}")
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result or 'permission_id' in result
        
        # Tracker l'association pour cleanup
        resources['policy_permissions'].append((policy['id'], permission_id))
        
        logger.info(f"✅ Permission added to policy successfully")

    def test07_get_policy_permissions(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /policies/{id}/permissions - Récupérer les permissions d'une policy"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une policy avec une permission
        policy_data = {
            "name": f"test_policy_get_perms_{timestamp}",
            "company_id": company_id
        }
        
        policy_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=cookies_dict
        )
        assert policy_response.status_code == 201
        policy = policy_response.json()
        resources['policies'].append(policy['id'])
        
        # Récupérer et ajouter une permission
        permissions_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/permissions",
            cookies=cookies_dict
        )
        assert permissions_response.status_code == 200
        permissions = permissions_response.json()
        assert len(permissions) > 0
        
        permission_id = permissions[0]['id']
        
        add_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies/{policy['id']}/permissions",
            json={"permission_id": permission_id},
            cookies=cookies_dict
        )
        assert add_response.status_code in [200, 201]
        resources['policy_permissions'].append((policy['id'], permission_id))
        
        # Tester GET permissions de la policy
        url = f"{api_tester.base_url}/api/guardian/policies/{policy['id']}/permissions"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get policy permissions response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list)
        assert len(result) > 0, "Expected at least one permission"
        
        logger.info(f"✅ Retrieved {len(result)} permissions for policy")

    def test08_delete_permission_from_policy(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester DELETE /policies/{id}/permissions/{permission_id} - Supprimer une permission d'une policy"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une policy avec une permission
        policy_data = {
            "name": f"test_policy_delete_perm_{timestamp}",
            "company_id": company_id
        }
        
        policy_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=cookies_dict
        )
        assert policy_response.status_code == 201
        policy = policy_response.json()
        resources['policies'].append(policy['id'])
        
        # Récupérer et ajouter une permission
        permissions_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/permissions",
            cookies=cookies_dict
        )
        assert permissions_response.status_code == 200
        permissions = permissions_response.json()
        assert len(permissions) > 0
        
        permission_id = permissions[0]['id']
        
        add_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies/{policy['id']}/permissions",
            json={"permission_id": permission_id},
            cookies=cookies_dict
        )
        assert add_response.status_code in [200, 201]
        
        # Tester DELETE permission de la policy
        url = f"{api_tester.base_url}/api/guardian/policies/{policy['id']}/permissions/{permission_id}"
        api_tester.log_request("DELETE", url, cookies=cookies_dict)
        
        response = api_tester.session.delete(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Delete permission from policy response status: {response.status_code}")
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Permission deleted from policy successfully")
        
        # Ne pas ajouter à policy_permissions car déjà supprimé

    def test09_delete_policy(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester DELETE /policies/{id} - Supprimer une policy"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une policy de test
        policy_data = {
            "name": f"test_policy_delete_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        policy = create_response.json()
        policy_id = policy['id']
        logger.info(f"Created policy for deletion: {policy_id}")
        
        # Tester la suppression
        url = f"{api_tester.base_url}/api/guardian/policies/{policy_id}"
        api_tester.log_request("DELETE", url, cookies=cookies_dict)
        
        response = api_tester.session.delete(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Delete policy response status: {response.status_code}")
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Policy deleted successfully: {policy_id}")
        
        # Vérifier que la policy n'existe plus
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/policies/{policy_id}",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 404, "Policy should not exist after deletion"
        logger.info("✅ Verified policy no longer exists")
        
        # Ne pas ajouter à resources car déjà supprimé
