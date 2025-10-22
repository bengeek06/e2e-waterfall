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

class TestAPIPositions:
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
            'positions': [],
            'organization_units': []
        }
        
        yield company_id, cookies_dict, created_resources
        
        logger.info("🧹 Cleaning up test resources...")
        
        # Supprimer les positions
        for position_id in created_resources['positions']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/positions/{position_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted position: {position_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete position {position_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting position {position_id}: {e}")
        
        # Supprimer les organization units
        for unit_id in reversed(created_resources['organization_units']):
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/organization_units/{unit_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted organization unit: {unit_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete organization unit {unit_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting organization unit {unit_id}: {e}")
        
        logger.info("✅ Cleanup completed")

    def test01_get_positions_list(self, api_tester, auth_token, setup_test_data):
        """Tester GET /positions"""
        company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/identity/positions"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of positions"
        
        logger.info(f"✅ Retrieved {len(result)} positions")

    def test02_create_position(self, api_tester, auth_token, setup_test_data):
        """Tester POST /positions"""
        company_id, cookies_dict, resources = setup_test_data
        
        # Créer une organization unit pour la position
        timestamp = int(time.time() * 1000)
        unit_data = {
            "name": f"test_unit_pos_{timestamp}",
            "company_id": company_id
        }
        
        unit_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert unit_response.status_code == 201
        unit = unit_response.json()
        resources['organization_units'].append(unit['id'])
        
        position_data = {
            "title": f"test_position_{timestamp}",
            "company_id": company_id,
            "organization_unit_id": unit['id']
        }
        
        url = f"{api_tester.base_url}/api/identity/positions"
        api_tester.log_request("POST", url, data=position_data, cookies=cookies_dict)
        
        response = api_tester.session.post(url, json=position_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result
        assert result['title'] == position_data['title']
        
        resources['positions'].append(result['id'])
        
        logger.info(f"✅ Position created: {result['id']}")

    def test03_get_position_by_id(self, api_tester, auth_token, setup_test_data):
        """Tester GET /positions/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        # Créer organization unit
        unit_data = {
            "name": f"test_unit_{timestamp}",
            "company_id": company_id
        }
        unit_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert unit_response.status_code == 201
        unit = unit_response.json()
        resources['organization_units'].append(unit['id'])
        
        # Créer position
        position_data = {
            "title": f"test_position_get_{timestamp}",
            "company_id": company_id,
            "organization_unit_id": unit['id']
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/positions",
            json=position_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        position = create_response.json()
        resources['positions'].append(position['id'])
        
        url = f"{api_tester.base_url}/api/identity/positions/{position['id']}"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == position['id']
        assert result['title'] == position_data['title']
        
        logger.info(f"✅ Position retrieved: {result['title']}")

    def test04_patch_position(self, api_tester, auth_token, setup_test_data):
        """Tester PATCH /positions/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        # Créer organization unit
        unit_data = {
            "name": f"test_unit_{timestamp}",
            "company_id": company_id
        }
        unit_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert unit_response.status_code == 201
        unit = unit_response.json()
        resources['organization_units'].append(unit['id'])
        
        # Créer position
        position_data = {
            "title": f"test_position_patch_{timestamp}",
            "company_id": company_id,
            "organization_unit_id": unit['id']
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/positions",
            json=position_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        position = create_response.json()
        resources['positions'].append(position['id'])
        
        patch_data = {
            "title": f"updated_position_{timestamp}"
        }
        
        url = f"{api_tester.base_url}/api/identity/positions/{position['id']}"
        api_tester.log_request("PATCH", url, data=patch_data, cookies=cookies_dict)
        
        response = api_tester.session.patch(url, json=patch_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['title'] == patch_data['title']
        
        logger.info(f"✅ Position patched successfully")

    def test05_put_position(self, api_tester, auth_token, setup_test_data):
        """Tester PUT /positions/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        # Créer organization unit
        unit_data = {
            "name": f"test_unit_{timestamp}",
            "company_id": company_id
        }
        unit_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert unit_response.status_code == 201
        unit = unit_response.json()
        resources['organization_units'].append(unit['id'])
        
        # Créer position
        position_data = {
            "title": f"test_position_put_{timestamp}",
            "company_id": company_id,
            "organization_unit_id": unit['id']
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/positions",
            json=position_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        position = create_response.json()
        resources['positions'].append(position['id'])
        
        put_data = {
            "title": f"fully_updated_position_{timestamp}",
            "company_id": company_id,
            "organization_unit_id": unit['id']
        }
        
        url = f"{api_tester.base_url}/api/identity/positions/{position['id']}"
        api_tester.log_request("PUT", url, data=put_data, cookies=cookies_dict)
        
        response = api_tester.session.put(url, json=put_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['title'] == put_data['title']
        
        logger.info(f"✅ Position updated successfully")

    def test06_delete_position(self, api_tester, auth_token, setup_test_data):
        """Tester DELETE /positions/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        # Créer organization unit
        unit_data = {
            "name": f"test_unit_{timestamp}",
            "company_id": company_id
        }
        unit_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert unit_response.status_code == 201
        unit = unit_response.json()
        resources['organization_units'].append(unit['id'])
        
        # Créer position
        position_data = {
            "title": f"test_position_delete_{timestamp}",
            "company_id": company_id,
            "organization_unit_id": unit['id']
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/positions",
            json=position_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        position = create_response.json()
        position_id = position['id']
        
        url = f"{api_tester.base_url}/api/identity/positions/{position_id}"
        api_tester.log_request("DELETE", url, cookies=cookies_dict)
        
        response = api_tester.session.delete(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Position deleted: {position_id}")
        
        # Vérifier suppression
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/identity/positions/{position_id}",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 404
        logger.info("✅ Verified position no longer exists")
