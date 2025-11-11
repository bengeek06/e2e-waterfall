import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('identity')

class TestAPISubcontractors:
    @pytest.fixture(scope="function")
    def setup_test_data(self, api_tester, session_auth_cookies, session_user_info):
        assert session_auth_cookies is not None, "No auth cookies available"
        
        cookies_dict = session_auth_cookies
        api_tester.cookies_dict = cookies_dict
        
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 200
        company_id = verify_response.json()['company_id']
        
        created_resources = {
            'subcontractors': []
        }
        
        yield company_id, cookies_dict, created_resources
        
        logger.info("🧹 Cleaning up test resources...")
        
        # Supprimer les subcontractors
        for subcontractor_id in created_resources['subcontractors']:
            try:
                delete_response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/subcontractors/{subcontractor_id}",
                    cookies=cookies_dict
                )
                if delete_response.status_code == 204:
                    logger.info(f"✅ Deleted subcontractor: {subcontractor_id}")
                else:
                    logger.warning(f"⚠️ Failed to delete subcontractor {subcontractor_id}: {delete_response.status_code}")
            except Exception as e:
                logger.error(f"❌ Error deleting subcontractor {subcontractor_id}: {e}")
        
        logger.info("✅ Cleanup completed")

    def test01_get_subcontractors_list(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /subcontractors"""
        company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/identity/subcontractors"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of subcontractors"
        
        logger.info(f"✅ Retrieved {len(result)} subcontractors")

    def test02_create_subcontractor(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester POST /subcontractors"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        subcontractor_data = {
            "name": f"test_subcontractor_{timestamp}",
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/identity/subcontractors"
        api_tester.log_request("POST", url, data=subcontractor_data, cookies=cookies_dict)
        
        response = api_tester.session.post(url, json=subcontractor_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result
        assert result['name'] == subcontractor_data['name']
        
        resources['subcontractors'].append(result['id'])
        
        logger.info(f"✅ Subcontractor created: {result['id']}")

    def test03_get_subcontractor_by_id(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /subcontractors/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        subcontractor_data = {
            "name": f"test_subcontractor_get_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/subcontractors",
            json=subcontractor_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        subcontractor = create_response.json()
        resources['subcontractors'].append(subcontractor['id'])
        
        url = f"{api_tester.base_url}/api/identity/subcontractors/{subcontractor['id']}"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == subcontractor['id']
        assert result['name'] == subcontractor_data['name']
        
        logger.info(f"✅ Subcontractor retrieved: {result['name']}")

    def test04_patch_subcontractor(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester PATCH /subcontractors/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        subcontractor_data = {
            "name": f"test_subcontractor_patch_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/subcontractors",
            json=subcontractor_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        subcontractor = create_response.json()
        resources['subcontractors'].append(subcontractor['id'])
        
        patch_data = {
            "name": f"updated_subcontractor_{timestamp}"
        }
        
        url = f"{api_tester.base_url}/api/identity/subcontractors/{subcontractor['id']}"
        api_tester.log_request("PATCH", url, data=patch_data, cookies=cookies_dict)
        
        response = api_tester.session.patch(url, json=patch_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == patch_data['name']
        
        logger.info(f"✅ Subcontractor patched successfully")

    def test05_put_subcontractor(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester PUT /subcontractors/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        subcontractor_data = {
            "name": f"test_subcontractor_put_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/subcontractors",
            json=subcontractor_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        subcontractor = create_response.json()
        resources['subcontractors'].append(subcontractor['id'])
        
        put_data = {
            "name": f"fully_updated_subcontractor_{timestamp}",
            "company_id": company_id
        }
        
        url = f"{api_tester.base_url}/api/identity/subcontractors/{subcontractor['id']}"
        api_tester.log_request("PUT", url, data=put_data, cookies=cookies_dict)
        
        response = api_tester.session.put(url, json=put_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == put_data['name']
        
        logger.info(f"✅ Subcontractor updated successfully")

    def test06_delete_subcontractor(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester DELETE /subcontractors/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        subcontractor_data = {
            "name": f"test_subcontractor_delete_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/subcontractors",
            json=subcontractor_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        subcontractor = create_response.json()
        subcontractor_id = subcontractor['id']
        
        url = f"{api_tester.base_url}/api/identity/subcontractors/{subcontractor_id}"
        api_tester.log_request("DELETE", url, cookies=cookies_dict)
        
        response = api_tester.session.delete(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Subcontractor deleted: {subcontractor_id}")
        
        # Vérifier suppression
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/identity/subcontractors/{subcontractor_id}",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 404
        logger.info("✅ Verified subcontractor no longer exists")
