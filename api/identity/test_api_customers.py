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
        self.session.verify = False
        self.auth_cookies = None
    
    @staticmethod
    def log_request(method, url, data=None, cookies=None):
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            safe_data = data.copy() if isinstance(data, dict) else data
            if isinstance(safe_data, dict) and 'password' in safe_data:
                safe_data['password'] = '***'
            logger.debug(f">>> Request body: {safe_data}")
    
    @staticmethod
    def log_response(response):
        logger.debug(f"<<< RESPONSE: {response.status_code}")
        try:
            if response.text:
                logger.debug(f"<<< Response body: {response.json()}")
        except:
            logger.debug(f"<<< Response body (raw): {response.text}")
        
    def wait_for_api(self, endpoint: str, timeout: int = 10) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(2)
        return False

class TestAPICustomers:
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return APITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
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
            return {
                'access_token': response.cookies.get('access_token'),
                'refresh_token': response.cookies.get('refresh_token')
            }
        return None

    @pytest.fixture(scope="function")
    def setup_test_data(self, api_tester, auth_token):
        assert auth_token is not None, "No auth cookies available"
        
        cookies_dict = {
            'access_token': auth_token['access_token'],
            'refresh_token': auth_token['refresh_token']
        }
        
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 200
        company_id = verify_response.json()['company_id']
        
        created_resources = {
            'customers': []
        }
        
        yield company_id, cookies_dict, created_resources
        
        logger.info("🧹 Cleaning up test resources...")
        
        # Supprimer les customers
        for customer_id in created_resources['customers']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/customers/{customer_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted customer: {customer_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete customer {customer_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting customer {customer_id}: {e}")
        
        logger.info("✅ Cleanup completed")

    def test01_get_customers_list(self, api_tester, auth_token, setup_test_data):
        """Tester GET /customers"""
        company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/identity/customers"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of customers"
        
        logger.info(f"✅ Retrieved {len(result)} customers")

    @pytest.mark.xfail(reason="API bug: company_id expects integer but should accept UUID")
    def test03_get_customer_by_id(self, api_tester, auth_token, setup_test_data):
        """Tester GET /customers/{id}"""

    @pytest.mark.xfail(reason="API bug: company_id expects integer but should accept UUID")
    def test02_create_customer(self, api_tester, auth_token, setup_test_data):
        """Tester POST /customers"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        customer_data = {
            "name": f"test_customer_{timestamp}",
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/identity/customers"
        api_tester.log_request("POST", url, data=customer_data, cookies=cookies_dict)
        
        response = api_tester.session.post(url, json=customer_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result
        assert result['name'] == customer_data['name']
        
        resources['customers'].append(result['id'])
        
        logger.info(f"✅ Customer created: {result['id']}")

    @pytest.mark.xfail(reason="API bug: company_id expects integer but should accept UUID")
    def test03_get_customer_by_id(self, api_tester, auth_token, setup_test_data):
        """Tester GET /customers/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        customer_data = {
            "name": f"test_customer_get_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/customers",
            json=customer_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        customer = create_response.json()
        resources['customers'].append(customer['id'])
        
        url = f"{api_tester.base_url}/api/identity/customers/{customer['id']}"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == customer['id']
        assert result['name'] == customer_data['name']
        
        logger.info(f"✅ Customer retrieved: {result['name']}")

    @pytest.mark.xfail(reason="API bug: company_id expects integer but should accept UUID")
    def test04_patch_customer(self, api_tester, auth_token, setup_test_data):
        """Tester PATCH /customers/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        customer_data = {
            "name": f"test_customer_patch_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/customers",
            json=customer_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        customer = create_response.json()
        resources['customers'].append(customer['id'])
        
        patch_data = {
            "name": f"updated_customer_{timestamp}"
        }
        
        url = f"{api_tester.base_url}/api/identity/customers/{customer['id']}"
        api_tester.log_request("PATCH", url, data=patch_data, cookies=cookies_dict)
        
        response = api_tester.session.patch(url, json=patch_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == patch_data['name']
        
        logger.info(f"✅ Customer patched successfully")

    @pytest.mark.xfail(reason="API bug: company_id expects integer but should accept UUID")
    def test05_put_customer(self, api_tester, auth_token, setup_test_data):
        """Tester PUT /customers/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        customer_data = {
            "name": f"test_customer_put_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/customers",
            json=customer_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        customer = create_response.json()
        resources['customers'].append(customer['id'])
        
        put_data = {
            "name": f"fully_updated_customer_{timestamp}",
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/identity/customers/{customer['id']}"
        api_tester.log_request("PUT", url, data=put_data, cookies=cookies_dict)
        
        response = api_tester.session.put(url, json=put_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == put_data['name']
        
        logger.info(f"✅ Customer updated successfully")

    @pytest.mark.xfail(reason="API bug: company_id expects integer but should accept UUID")
    def test06_delete_customer(self, api_tester, auth_token, setup_test_data):
        """Tester DELETE /customers/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        customer_data = {
            "name": f"test_customer_delete_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/customers",
            json=customer_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        customer = create_response.json()
        customer_id = customer['id']
        
        url = f"{api_tester.base_url}/api/identity/customers/{customer_id}"
        api_tester.log_request("DELETE", url, cookies=cookies_dict)
        
        response = api_tester.session.delete(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Customer deleted: {customer_id}")
        
        # Vérifier suppression
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/identity/customers/{customer_id}",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 404
        logger.info("✅ Verified customer no longer exists")
