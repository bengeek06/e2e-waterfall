import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('identity')

class TestAPICompanies:
    @pytest.fixture(scope="function")
    def setup_test_data(self, api_tester, session_auth_cookies, session_user_info):
        """Setup pour chaque test avec cleanup automatique"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        cookies_dict = session_auth_cookies
        api_tester.cookies_dict = cookies_dict
        
        # Récupérer company_id depuis session_user_info
        company_id = session_user_info['company_id']
        
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

    def test01_get_companies_list(self, api_tester, session_auth_cookies, setup_test_data):
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

    def test02_create_company(self, api_tester, session_auth_cookies, setup_test_data):
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

    def test03_get_company_by_id(self, api_tester, session_auth_cookies, setup_test_data):
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

    def test04_patch_company(self, api_tester, session_auth_cookies, setup_test_data):
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

    def test05_put_company(self, api_tester, session_auth_cookies, setup_test_data):
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

    def test06_delete_company(self, api_tester, session_auth_cookies, setup_test_data):
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
