import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('guardian')

class TestAPIPermissions:
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
            'permissions': []
        }
        
        yield company_id, cookies_dict, created_resources
        
        # Cleanup automatique à la fin du test
        logger.info("🧹 Cleaning up test resources...")
        
        # Supprimer les permissions créées
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

    def test01_get_permissions_list(self, api_tester, session_auth_cookies, setup_test_data):
        """Tester GET /permissions - Liste toutes les permissions"""
        company_id, cookies_dict, resources = setup_test_data
        
        url = f"{api_tester.base_url}/api/guardian/permissions"
        api_tester.log_request("GET", url, cookies=cookies_dict)
        
        response = api_tester.session.get(url, cookies=cookies_dict)
        
        api_tester.log_response(response)
        logger.info(f"Get permissions response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert isinstance(result, list), "Expected a list of permissions"
        
        logger.info(f"✅ Retrieved {len(result)} permissions")

