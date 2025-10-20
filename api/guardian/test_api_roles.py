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
        # Ignorer les certificats auto-signés pour les tests
        self.session.verify = False
        self.auth_cookies = None
    
    @staticmethod
    def log_request(method, url, data=None, cookies=None):
        """Log une requête HTTP avec détails"""
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            # Masquer les mots de passe dans les logs
            safe_data = data.copy() if isinstance(data, dict) else data
            if isinstance(safe_data, dict) and 'password' in safe_data:
                safe_data['password'] = '***'
            logger.debug(f">>> Request body: {safe_data}")
        if cookies:
            # Logger les cookies utilisés (tronqués pour sécurité)
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
        # Forcer l'ajout des cookies à la session
        for cookie in cookies:
            self.session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
        
    def wait_for_api(self, endpoint: str, timeout: int = 10) -> bool:
        """Attendre qu'une API soit disponible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                logger.debug(f"wait_for_api - Status: {response.status_code}, Response: {response.text[:100]}...")
                if response.status_code == 200:
                    return True
                elif response.status_code in [401, 403]:
                    logger.warning(f"Authentication issue detected: {response.status_code}")
                    return False  # Ne pas continuer si c'est un problème d'auth
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request exception: {e}")
                pass
            time.sleep(2)
        return False

class TestAPIRoles:
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
    
    @pytest.fixture(scope="function")
    def setup_test_data(self, api_tester, auth_token):
        """Setup: Créer les données de test nécessaires pour chaque test"""
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
        
        # Sauvegarder les cookies
        api_tester.cookies_dict = cookies_dict
        api_tester.company_id = company_id
        
        # Liste pour tracker les ressources créées à nettoyer
        created_resources = {
            'roles': [],
            'policies': [],
            'role_policies': []  # Pour les associations role-policy
        }
        
        logger.info(f"Setup test data - Company: {company_id}")
        
        yield company_id, created_resources
        
        # Cleanup: Supprimer toutes les ressources créées pendant le test
        logger.info("Starting cleanup of test resources...")
        
        # Supprimer les associations role-policy
        for role_id, policy_id in created_resources['role_policies']:
            try:
                response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/guardian/roles/{role_id}/policies/{policy_id}",
                    cookies=cookies_dict
                )
                if response.status_code == 204:
                    logger.info(f"✓ Cleaned up role-policy: {role_id}/{policy_id}")
                else:
                    logger.warning(f"Could not cleanup role-policy {role_id}/{policy_id}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error cleaning up role-policy {role_id}/{policy_id}: {e}")
        
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
        
        # Supprimer les policies créées
        for policy_id in created_resources['policies']:
            try:
                response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/guardian/policies/{policy_id}",
                    cookies=cookies_dict
                )
                if response.status_code == 204:
                    logger.info(f"✓ Cleaned up policy: {policy_id}")
                else:
                    logger.warning(f"Could not cleanup policy {policy_id}: {response.status_code}")
            except Exception as e:
                logger.error(f"Error cleaning up policy {policy_id}: {e}")
        
        logger.info("Cleanup completed")

    def test01_get_roles_list(self, api_tester, auth_token, setup_test_data):
        """Tester GET /roles - Liste tous les rôles"""
        company_id, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/guardian/roles"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get roles response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of roles"
        
        logger.info(f"✅ Retrieved {len(result)} roles")

    def test02_create_role(self, api_tester, auth_token, setup_test_data):
        """Tester POST /roles - Créer un rôle"""
        company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        role_data = {
            "name": f"test_role_create_{timestamp}",
            "description": "Test role for creation",
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/guardian/roles"
        api_tester.log_request("POST", url, data=role_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Create role response status: {response.status_code}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result, "Expected role ID in response"
        assert result['name'] == role_data['name']
        assert result['company_id'] == company_id
        
        resources['roles'].append(result['id'])
        
        logger.info(f"✅ Role created successfully with ID: {result['id']}")

    def test03_get_role_by_id(self, api_tester, auth_token, setup_test_data):
        """Tester GET /roles/{id} - Récupérer un rôle par ID"""
        company_id, resources = setup_test_data
        
        # Créer un rôle de test
        import time
        timestamp = int(time.time() * 1000)
        role_data = {
            "name": f"test_role_get_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert create_response.status_code == 201
        created_role = create_response.json()
        resources['roles'].append(created_role['id'])
        
        # Tester la récupération par ID
        url = f"{api_tester.base_url}/api/guardian/roles/{created_role['id']}"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get role by ID response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == created_role['id']
        assert result['name'] == role_data['name']
        
        logger.info(f"✅ Role retrieved: {result}")

    def test04_patch_role(self, api_tester, auth_token, setup_test_data):
        """Tester PATCH /roles/{id} - Mise à jour partielle d'un rôle"""
        company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle de test
        role_data = {
            "name": f"test_role_patch_{timestamp}",
            "description": "Original description",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert create_response.status_code == 201
        role = create_response.json()
        resources['roles'].append(role['id'])
        
        # Tester PATCH pour modifier seulement le nom
        patch_data = {
            "name": f"patched_role_{timestamp}"
        }
        
        url = f"{api_tester.base_url}/api/guardian/roles/{role['id']}"
        api_tester.log_request("PATCH", url, data=patch_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.patch(
            url,
            json=patch_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Patch role response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == patch_data['name']
        assert result['description'] == role_data['description']  # Description non modifiée
        
        logger.info(f"✅ Role patched successfully")

    def test05_put_role(self, api_tester, auth_token, setup_test_data):
        """Tester PUT /roles/{id} - Remplacement complet d'un rôle"""
        company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle de test
        role_data = {
            "name": f"test_role_put_{timestamp}",
            "description": "Original description",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert create_response.status_code == 201
        role = create_response.json()
        resources['roles'].append(role['id'])
        
        # Tester PUT pour remplacer complètement
        put_data = {
            "name": f"updated_role_{timestamp}",
            "description": "Updated description",
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/guardian/roles/{role['id']}"
        api_tester.log_request("PUT", url, data=put_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.put(
            url,
            json=put_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Put role response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == put_data['name']
        assert result['description'] == put_data['description']
        
        logger.info(f"✅ Role updated successfully")

    def test06_add_policy_to_role(self, api_tester, auth_token, setup_test_data):
        """Tester POST /roles/{id}/policies - Ajouter une policy à un rôle"""
        company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle de test
        role_data = {
            "name": f"test_role_policy_{timestamp}",
            "company_id": company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert role_response.status_code == 201
        role = role_response.json()
        resources['roles'].append(role['id'])
        
        # Créer une policy de test
        policy_data = {
            "name": f"test_policy_{timestamp}",
            "company_id": company_id
        }
        
        policy_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=api_tester.cookies_dict
        )
        assert policy_response.status_code == 201
        policy = policy_response.json()
        resources['policies'].append(policy['id'])
        
        # Ajouter la policy au rôle
        add_policy_data = {
            "policy_id": policy['id']
        }
        
        url = f"{api_tester.base_url}/api/guardian/roles/{role['id']}/policies"
        api_tester.log_request("POST", url, data=add_policy_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=add_policy_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Add policy to role response status: {response.status_code}")
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result or 'policy_id' in result
        
        # Tracker l'association pour cleanup
        resources['role_policies'].append((role['id'], policy['id']))
        
        logger.info(f"✅ Policy added to role successfully")

    def test07_get_role_policies(self, api_tester, auth_token, setup_test_data):
        """Tester GET /roles/{id}/policies - Récupérer les policies d'un rôle"""
        company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle avec une policy
        role_data = {
            "name": f"test_role_get_policies_{timestamp}",
            "company_id": company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert role_response.status_code == 201
        role = role_response.json()
        resources['roles'].append(role['id'])
        
        # Créer et ajouter une policy
        policy_data = {
            "name": f"test_policy_{timestamp}",
            "company_id": company_id
        }
        
        policy_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=api_tester.cookies_dict
        )
        assert policy_response.status_code == 201
        policy = policy_response.json()
        resources['policies'].append(policy['id'])
        
        add_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles/{role['id']}/policies",
            json={"policy_id": policy['id']},
            cookies=api_tester.cookies_dict
        )
        assert add_response.status_code in [200, 201]
        resources['role_policies'].append((role['id'], policy['id']))
        
        # Tester GET policies du rôle
        url = f"{api_tester.base_url}/api/guardian/roles/{role['id']}/policies"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get role policies response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list)
        assert len(result) > 0, "Expected at least one policy"
        
        logger.info(f"✅ Retrieved {len(result)} policies for role")

    def test08_delete_policy_from_role(self, api_tester, auth_token, setup_test_data):
        """Tester DELETE /roles/{id}/policies/{policy_id} - Supprimer une policy d'un rôle"""
        company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle avec une policy
        role_data = {
            "name": f"test_role_delete_policy_{timestamp}",
            "company_id": company_id
        }
        
        role_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert role_response.status_code == 201
        role = role_response.json()
        resources['roles'].append(role['id'])
        
        policy_data = {
            "name": f"test_policy_{timestamp}",
            "company_id": company_id
        }
        
        policy_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/policies",
            json=policy_data,
            cookies=api_tester.cookies_dict
        )
        assert policy_response.status_code == 201
        policy = policy_response.json()
        resources['policies'].append(policy['id'])
        
        add_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles/{role['id']}/policies",
            json={"policy_id": policy['id']},
            cookies=api_tester.cookies_dict
        )
        assert add_response.status_code in [200, 201]
        
        # Tester DELETE policy du rôle
        url = f"{api_tester.base_url}/api/guardian/roles/{role['id']}/policies/{policy['id']}"
        api_tester.log_request("DELETE", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.delete(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Delete policy from role response status: {response.status_code}")
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Policy deleted from role successfully")
        
        # Ne pas ajouter à role_policies car déjà supprimé

    def test09_delete_role(self, api_tester, auth_token, setup_test_data):
        """Tester DELETE /roles/{id} - Supprimer un rôle"""
        company_id, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer un rôle de test
        role_data = {
            "name": f"test_role_delete_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/guardian/roles",
            json=role_data,
            cookies=api_tester.cookies_dict
        )
        assert create_response.status_code == 201
        role = create_response.json()
        role_id = role['id']
        logger.info(f"Created role for deletion: {role_id}")
        
        # Tester la suppression
        url = f"{api_tester.base_url}/api/guardian/roles/{role_id}"
        api_tester.log_request("DELETE", url, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.delete(url, cookies=api_tester.cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Delete role response status: {response.status_code}")
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Role deleted successfully: {role_id}")
        
        # Vérifier que le rôle n'existe plus
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/guardian/roles/{role_id}",
            cookies=api_tester.cookies_dict
        )
        assert verify_response.status_code == 404, "Role should not exist after deletion"
        logger.info("✅ Verified role no longer exists")
        
        # Ne pas ajouter à resources car déjà supprimé