import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('identity')

class TestAPIOrganizationUnits:
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
            'organization_units': []
        }
        
        yield company_id, cookies_dict, created_resources
        
        logger.info("🧹 Cleaning up test resources...")
        
        # Supprimer les organization units (en ordre inverse pour gérer la hiérarchie)
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

    def test01_get_organization_units_list(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /organization_units"""
        company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/identity/organization_units"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of organization units"
        
        logger.info(f"✅ Retrieved {len(result)} organization units")

    def test02_create_organization_unit(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester POST /organization_units"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        unit_data = {
            "name": f"test_unit_{timestamp}",
            "company_id": company_id,
            "description": "Test organization unit"
        }
        
        url = f"{api_tester.base_url}/api/identity/organization_units"
        api_tester.log_request("POST", url, data=unit_data, cookies=cookies_dict)
        
        response = api_tester.session.post(url, json=unit_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'id' in result
        assert result['name'] == unit_data['name']
        
        resources['organization_units'].append(result['id'])
        
        logger.info(f"✅ Organization unit created: {result['id']}")

    def test03_get_organization_unit_by_id(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /organization_units/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        unit_data = {
            "name": f"test_unit_get_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        unit = create_response.json()
        resources['organization_units'].append(unit['id'])
        
        url = f"{api_tester.base_url}/api/identity/organization_units/{unit['id']}"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['id'] == unit['id']
        assert result['name'] == unit_data['name']
        
        logger.info(f"✅ Organization unit retrieved: {result['name']}")

    def test04_create_child_unit(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester création d'une unité enfant avec parent_id"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        # Créer parent
        parent_data = {
            "name": f"parent_unit_{timestamp}",
            "company_id": company_id
        }
        
        parent_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=parent_data,
            cookies=cookies_dict
        )
        assert parent_response.status_code == 201
        parent = parent_response.json()
        resources['organization_units'].append(parent['id'])
        
        # Créer enfant
        child_data = {
            "name": f"child_unit_{timestamp}",
            "company_id": company_id,
            "parent_id": parent['id']
        }
        
        url = f"{api_tester.base_url}/api/identity/organization_units"
        api_tester.log_request("POST", url, data=child_data, cookies=cookies_dict)
        
        response = api_tester.session.post(url, json=child_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['parent_id'] == parent['id']
        
        resources['organization_units'].append(result['id'])
        
        logger.info(f"✅ Child organization unit created: {result['id']}")

    def test05_get_children_units(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /organization_units/{id}/children"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        # Créer parent
        parent_data = {
            "name": f"parent_children_{timestamp}",
            "company_id": company_id
        }
        
        parent_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=parent_data,
            cookies=cookies_dict
        )
        assert parent_response.status_code == 201
        parent = parent_response.json()
        resources['organization_units'].append(parent['id'])
        
        # Créer 2 enfants
        for i in range(2):
            child_data = {
                "name": f"child_{i}_{timestamp}",
                "company_id": company_id,
                "parent_id": parent['id']
            }
            
            child_response = api_tester.session.post(
                f"{api_tester.base_url}/api/identity/organization_units",
                json=child_data,
                cookies=cookies_dict
            )
            assert child_response.status_code == 201
            resources['organization_units'].append(child_response.json()['id'])
        
        # Récupérer les enfants
        url = f"{api_tester.base_url}/api/identity/organization_units/{parent['id']}/children"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list)
        assert len(result) == 2, f"Expected 2 children, got {len(result)}"
        
        logger.info(f"✅ Retrieved {len(result)} children units")

    def test06_patch_organization_unit(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester PATCH /organization_units/{id}"""

        """Tester PATCH /organization_units/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        unit_data = {
            "name": f"test_unit_patch_{timestamp}",
            "company_id": company_id,
            "description": "Original description"
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        unit = create_response.json()
        resources['organization_units'].append(unit['id'])
        
        patch_data = {
            "description": f"Updated description {timestamp}"
        }
        
        url = f"{api_tester.base_url}/api/identity/organization_units/{unit['id']}"
        api_tester.log_request("PATCH", url, data=patch_data, cookies=cookies_dict)
        
        response = api_tester.session.patch(url, json=patch_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['description'] == patch_data['description']
        assert result['name'] == unit_data['name']
        
        logger.info(f"✅ Organization unit patched successfully")

    def test06_put_organization_unit(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester PUT /organization_units/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        unit_data = {
            "name": f"test_unit_put_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        unit = create_response.json()
        resources['organization_units'].append(unit['id'])
        
        put_data = {
            "name": f"updated_unit_{timestamp}",
            "company_id": company_id,
            "description": "New description"
        }
        
        url = f"{api_tester.base_url}/api/identity/organization_units/{unit['id']}"
        api_tester.log_request("PUT", url, data=put_data, cookies=cookies_dict)
        
        response = api_tester.session.put(url, json=put_data, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result['name'] == put_data['name']
        assert result['description'] == put_data['description']
        
        logger.info(f"✅ Organization unit updated successfully")

    def test07_delete_organization_unit(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester DELETE /organization_units/{id}"""
        company_id, cookies_dict, resources = setup_test_data
        
        timestamp = int(time.time() * 1000)
        
        unit_data = {
            "name": f"test_unit_delete_{timestamp}",
            "company_id": company_id
        }
        
        create_response = api_tester.session.post(
            f"{api_tester.base_url}/api/identity/organization_units",
            json=unit_data,
            cookies=cookies_dict
        )
        assert create_response.status_code == 201
        unit = create_response.json()
        unit_id = unit['id']
        
        url = f"{api_tester.base_url}/api/identity/organization_units/{unit_id}"
        api_tester.log_request("DELETE", url, cookies=cookies_dict)
        
        response = api_tester.session.delete(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"
        
        logger.info(f"✅ Organization unit deleted: {unit_id}")
        
        # Vérifier suppression
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/identity/organization_units/{unit_id}",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 404
        logger.info("✅ Verified organization unit no longer exists")
