import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('identity')

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
                    return False
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request exception: {e}")
                pass
            time.sleep(2)
        return False

class TestAPICompanies:
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
            access_token = response.cookies.get('access_token')
            refresh_token = response.cookies.get('refresh_token')
            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        return None

    @pytest.fixture(scope="function")
    def setup_test_data(self, api_tester, auth_token):
        """Setup pour chaque test avec cleanup automatique"""
        assert auth_token is not None, "No auth cookies available"
        
        cookies_dict = {
            'access_token': auth_token['access_token'],
            'refresh_token': auth_token['refresh_token']
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
            'companies': []
        }
        
        logger.info(f"Setup test data - Company: {company_id}")
        
        yield company_id, cookies_dict, created_resources
        
        # Cleanup automatique à la fin du test
        logger.info("🧹 Cleaning up test resources...")
        
        # Supprimer les companies créées
        for company_id_to_delete in created_resources['companies']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/companies/{company_id_to_delete}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted company: {company_id_to_delete}")
                else:
                    logger.warning(f"⚠️ Failed to delete company {company_id_to_delete}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting company {company_id_to_delete}: {e}")
        
        logger.info("✅ Cleanup completed")

    def test01_get_companies_list(self, api_tester, auth_token, setup_test_data):
        """Tester GET /companies - Liste toutes les companies"""
        company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/identity/companies"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get companies response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of companies"
        
        logger.info(f"✅ Retrieved {len(result)} companies")

    def test02_create_company(self, api_tester, auth_token, setup_test_data):
        """Tester POST /companies - Créer une company"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        company_data = {
            "name": f"test_company_{timestamp}",
            "description": "Test company for creation",
            "email": f"test_{timestamp}@example.com",
            "city": "Paris"
        }
        
        url = f"{api_tester.base_url}/api/identity/companies"
        api_tester.log_request("POST", url, data=company_data, cookies=cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=company_data,
            cookies=cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Create company response status: {response.status_code}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result, "Expected company ID in response"
        assert result['name'] == company_data['name']
        
        resources['companies'].append(result['id'])
        
        logger.info(f"✅ Company created successfully with ID: {result['id']}")

    def test03_get_company_by_id(self, api_tester, auth_token, setup_test_data):
        """Tester GET /companies/{id} - Récupérer une company par ID"""
        company_id, cookies_dict, resources = setup_test_data
        
        # Utiliser la company courante
        url = f"{api_tester.base_url}/api/identity/companies/{company_id}"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get company by ID response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == company_id
        assert 'name' in result
        
        logger.info(f"✅ Company retrieved: {result['name']}")

    def test04_patch_company(self, api_tester, auth_token, setup_test_data):
        """Tester PATCH /companies/{id} - Mise à jour partielle d'une company"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une company de test
        company_data = {
            "name": f"test_company_patch_{timestamp}",
            "description": "Original description"
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/companies",
            json=company_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        company = create_response.json()
        resources['companies'].append(company['id'])
        
        # Tester PATCH pour modifier seulement la description
        patch_data = {
            "description": f"Updated description {timestamp}"
        }
        
        url = f"{api_tester.base_url}/api/identity/companies/{company['id']}"
        api_tester.log_request("PATCH", url, data=patch_data, cookies=cookies_dict)
        
        response = api_tester.session.patch(
            url,
            json=patch_data,
            cookies=cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Patch company response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['description'] == patch_data['description']
        assert result['name'] == company_data['name']  # Name non modifié
        
        logger.info(f"✅ Company patched successfully")

    def test05_put_company(self, api_tester, auth_token, setup_test_data):
        """Tester PUT /companies/{id} - Remplacement complet d'une company"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une company de test
        company_data = {
            "name": f"test_company_put_{timestamp}",
            "description": "Original description"
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/companies",
            json=company_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        company = create_response.json()
        resources['companies'].append(company['id'])
        
        # Tester PUT pour remplacer complètement
        put_data = {
            "name": f"updated_company_{timestamp}",
            "description": "Updated description",
            "city": "Lyon"
        }
        
        url = f"{api_tester.base_url}/api/identity/companies/{company['id']}"
        api_tester.log_request("PUT", url, data=put_data, cookies=cookies_dict)
        
        response = api_tester.session.put(
            url,
            json=put_data,
            cookies=cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Put company response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == put_data['name']
        assert result['description'] == put_data['description']
        
        logger.info(f"✅ Company updated successfully")

    def test06_delete_company(self, api_tester, auth_token, setup_test_data):
        """Tester DELETE /companies/{id} - Supprimer une company"""
        company_id, cookies_dict, resources = setup_test_data
        
        import time
        timestamp = int(time.time() * 1000)
        
        # Créer une company de test
        company_data = {
            "name": f"test_company_delete_{timestamp}"
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/companies",
            json=company_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        company = create_response.json()
        company_test_id = company['id']
        logger.info(f"Created company for deletion: {company_test_id}")
        
        # Tester la suppression
        url = f"{api_tester.base_url}/api/identity/companies/{company_test_id}"
        api_tester.log_request("DELETE", url, cookies=cookies_dict)
        
        response = api_tester.session.delete(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Delete company response status: {response.status_code}")
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Company deleted successfully: {company_test_id}")
        
        # Vérifier que la company n'existe plus
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/identity/companies/{company_test_id}",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 404, "Company should not exist after deletion"
        logger.info("✅ Verified company no longer exists")
        
        # Ne pas ajouter à resources car déjà supprimé
