"""
Tests for Basic I/O API - Health, Version, Config endpoints
"""
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('basic_io')


class TestBasicIOHealth:
    """Tests de santé de l'API Basic I/O"""
    
    def test01_health_check(self, api_tester):
        """Vérifier que l'API Basic I/O est accessible via /health"""
        assert api_tester.wait_for_api("/api/basic-io/health"), "Basic I/O API not reachable"
        
        url = f"{api_tester.base_url}/api/basic-io/health"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Health check failed with status {response.status_code}"
        
        health_info = response.json()
        assert "status" in health_info, "Status field missing in health response"
        assert health_info["status"] in ["healthy", "unhealthy"], "Invalid status value"
        
        logger.info(f"✅ Basic I/O API Health: {health_info['status']}")
        
        # Vérifier les champs optionnels
        if "service" in health_info:
            logger.info(f"Service: {health_info['service']}")
        if "version" in health_info:
            logger.info(f"Version: {health_info['version']}")
        if "checks" in health_info:
            logger.info(f"Checks: {health_info['checks']}")

    def test02_version(self, api_tester, session_auth_cookies):
        """Vérifier que l'API Basic I/O retourne une version avec authentification"""
        assert session_auth_cookies is not None, "Authentication token not available"
        
        url = f"{api_tester.base_url}/api/basic-io/version"
        api_tester.log_request('GET', url)
        
        # Passer les cookies directement dans la requête
        response = api_tester.session.get(url, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        version_info = response.json()
        assert "version" in version_info, "Version info missing in response"
        logger.info(f"✅ Basic I/O API Version: {version_info['version']}")


    def test03_config(self, api_tester, session_auth_cookies):
        """Vérifier l'endpoint de configuration avec authentification"""
        assert session_auth_cookies is not None, "Authentication token not available"
        
        url = f"{api_tester.base_url}/api/basic-io/config"
        api_tester.log_request('GET', url)
        
        # Passer les cookies directement dans la requête
        response = api_tester.session.get(url, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        config = response.json()
        logger.info(f"✅ Basic I/O API Config retrieved with {len(config)} fields")
        
        # Vérifier quelques champs attendus (selon la spec)
        if "env" in config:
            logger.info(f"Environment: {config['env']}")
