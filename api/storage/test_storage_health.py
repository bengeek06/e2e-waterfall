"""
Tests for Storage API - Health, Version, Config endpoints
"""
import requests
import time
import pytest
import sys
from pathlib import Path

# Désactiver les warnings SSL pour les tests (certificats auto-signés)

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('storage')

class TestStorageHealth:
    """Tests de santé de l'API Storage"""
    


    def test01_health_check(self, api_tester):
        """Vérifier que l'API Storage est accessible via /health"""
        assert api_tester.wait_for_api("/api/storage/health"), "Storage API not reachable"
        
        url = f"{api_tester.base_url}/api/storage/health"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        assert response.status_code == 200, f"Health check failed with status {response.status_code}"
        
        health_info = response.json()
        assert "status" in health_info, "Status field missing in health response"
        assert health_info["status"] in ["healthy", "unhealthy"], "Invalid status value"
        
        logger.info(f"✅ Storage API Health: {health_info['status']}")
        
        # Vérifier les champs optionnels
        if "service" in health_info:
            logger.info(f"Service: {health_info['service']}")
        if "version" in health_info:
            logger.info(f"Version: {health_info['version']}")
        if "checks" in health_info:
            logger.info(f"Checks: {health_info['checks']}")

    def test02_version(self, api_tester, session_auth_cookies):
        """Vérifier que l'API Storage retourne une version"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        url = f"{api_tester.base_url}/api/storage/version"
        api_tester.log_request('GET', url)
        
        # Passer les cookies directement dans la requête
        response = api_tester.session.get(url, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to get API version with status {response.status_code}: {response.text}"
        
        version_info = response.json()
        assert "version" in version_info, "Version info missing in response"
        logger.info(f"✅ Storage API Version: {version_info['version']}")

    def test03_config(self, api_tester, session_auth_cookies):
        """Vérifier l'endpoint de configuration"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        url = f"{api_tester.base_url}/api/storage/config"
        api_tester.log_request('GET', url)
        
        # Passer les cookies directement dans la requête
        response = api_tester.session.get(url, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to get config with status {response.status_code}: {response.text}"
        
        config = response.json()
        logger.info(f"✅ Storage API Config retrieved with {len(config)} fields")
        
        # Vérifier quelques champs attendus (selon la spec)
        if "env" in config:
            logger.info(f"Environment: {config['env']}")
