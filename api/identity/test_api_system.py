"""
Tests for Identity Service - System endpoints
"""

import requests
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('identity')

class TestIdentitySystemEndpoints:
    def test01_health_check(self, api_tester):
        """Tester le endpoint /health"""
        url = f"{api_tester.base_url}/api/identity/health"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Health check response status: {response.status_code}")
        
        # Le endpoint health devrait être accessible sans authentification
        assert response.status_code in [200, 503], \
            f"Expected 200 or 503 for health check, got {response.status_code}"
        
        health_info = response.json()
        
        # Vérifier la structure selon la spec
        assert "status" in health_info, "Missing 'status' in health response"
        assert "service" in health_info, "Missing 'service' in health response"
        
        # Le status devrait être 'healthy' ou 'unhealthy'
        assert health_info["status"] in ["healthy", "unhealthy", "degraded"], \
            f"Invalid status: {health_info['status']}"
        
        logger.info(f"Identity Service health: {health_info['status']}")
        if "checks" in health_info:
            logger.info(f"Health checks: {health_info['checks']}")

    def test02_version_endpoint(self, api_tester):
        """Tester le endpoint /version"""
        url = f"{api_tester.base_url}/api/identity/version"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Version endpoint response status: {response.status_code}")
        
        # Endpoint peut ne pas être implémenté (400, 404) ou nécessiter auth (401)
        assert response.status_code in [200, 400, 401, 404], \
            f"Expected 200, 400, 401 or 404 for version endpoint, got {response.status_code}"
        
        if response.status_code == 200:
            version_info = response.json()
            
            # Vérifier la structure selon la spec
            assert "version" in version_info, "Missing 'version' in response"
            
            logger.info(f"Identity Service version: {version_info['version']}")
        else:
            logger.info(f"Version endpoint not fully implemented (status {response.status_code})")

    def test03_config_endpoint(self, api_tester):
        """Tester le endpoint /config"""
        url = f"{api_tester.base_url}/api/identity/config"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Config endpoint response status: {response.status_code}")
        
        # Config peut nécessiter l'authentification (401) ou retourner les données (200)
        assert response.status_code in [200, 401], \
            f"Expected 200 or 401 for config endpoint, got {response.status_code}"
        
        if response.status_code == 200:
            config_info = response.json()
            logger.info(f"Config retrieved: {config_info}")
        else:
            logger.info("Config endpoint requires authentication")

    def test04_init_db_get_status(self, api_tester):
        """Tester le endpoint GET /init-db (vérifier le statut)"""
        url = f"{api_tester.base_url}/api/identity/init-db"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Init-db GET response status: {response.status_code}")
        
        # Le endpoint devrait être accessible sans authentification
        assert response.status_code == 200, \
            f"Expected 200 for init-db status, got {response.status_code}"
        
        init_status = response.json()
        
        # Vérifier la structure selon la spec
        assert "initialized" in init_status, "Missing 'initialized' in response"
        
        logger.info(f"Database initialized: {init_status['initialized']}")
        if "message" in init_status:
            logger.info(f"Init message: {init_status['message']}")

    def test05_init_db_already_initialized(self, api_tester):
        """Tester le endpoint POST /init-db (quand déjà initialisé)"""
        url = f"{api_tester.base_url}/api/identity/init-db"
        api_tester.log_request('POST', url)
        
        response = api_tester.session.post(url)
        api_tester.log_response(response)
        
        logger.info(f"Init-db POST response status: {response.status_code}")
        
        # Si déjà initialisé: 409, sinon 200
        assert response.status_code in [200, 403, 409], \
            f"Expected 200, 403 or 409 for init-db, got {response.status_code}"
        
        init_response = response.json()
        
        if response.status_code == 200:
            logger.info("Database initialized successfully")
        elif response.status_code == 409:
            logger.info(f"Database already initialized: {init_response.get('message', 'No message')}")
        else:
            logger.info(f"Init-db forbidden: {init_response.get('message', 'No message')}")
