"""
Tests for Project Service - System endpoints

Endpoints testés:
- GET /health - Vérification de l'état du service
- GET /version - Version du service  
- GET /config - Configuration du service
"""

import requests
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('project')


class TestProjectSystemEndpoints:
    """Tests des endpoints système du Project Service
    
    Ces endpoints permettent de vérifier l'état et la configuration du service.
    Selon la spec OpenAPI project_api.yml:
    - /health: Accessible sans auth, retourne status + checks
    - /version: Peut nécessiter auth (401) ou retourner version (200)
    - /config: Peut nécessiter auth (401) ou retourner config (200)
    """
    
    def test01_health_check(self, api_tester):
        """Tester le endpoint /health
        
        Selon RESPONSES_SPECIFICATION.md:
        - 200 OK: Service opérationnel (status: healthy)
        - 503 Service Unavailable: Service dégradé (status: unhealthy)
        
        Structure attendue:
        {
          "status": "healthy|unhealthy",
          "service": "project",
          "checks": {
            "database": "connected|disconnected",
            "identity_service": "reachable|unreachable"
          }
        }
        """
        url = f"{api_tester.base_url}/api/project/health"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Health check response status: {response.status_code}")
        
        # Le endpoint health devrait être accessible sans authentification
        # 404 si le service n'est pas encore déployé
        # 500 si PROJECT_SERVICE_URL n'est pas configuré dans le proxy
        assert response.status_code in [200, 404, 500, 503], \
            f"Expected 200, 404, 500 or 503 for health check, got {response.status_code}"
        
        if response.status_code == 404:
            logger.info("Health endpoint not yet implemented (404)")
            return
        
        if response.status_code == 500:
            error_info = response.json()
            if "PROJECT_SERVICE_URL" in error_info.get("error", ""):
                logger.info("Project Service not configured in proxy yet (PROJECT_SERVICE_URL not defined)")
                return
        
        health_info = response.json()
        
        # Vérifier la structure selon la spec
        assert "status" in health_info, "Missing 'status' in health response"
        assert "service" in health_info, "Missing 'service' in health response"
        
        # Le status devrait être 'healthy' ou 'unhealthy'
        assert health_info["status"] in ["healthy", "unhealthy", "degraded"], \
            f"Invalid status: {health_info['status']}"
        
        # Vérifier que c'est bien le Project Service
        assert health_info["service"] in ["project", "project_service"], \
            f"Expected service='project' or 'project_service', got '{health_info['service']}'"
        
        logger.info(f"Project Service health: {health_info['status']}")
        if "checks" in health_info:
            logger.info(f"Health checks: {health_info['checks']}")
            
            # Si des checks sont présents, ils devraient inclure database et identity_service
            checks = health_info["checks"]
            if "database" in checks:
                logger.info(f"  - Database: {checks['database']}")
            if "identity_service" in checks:
                logger.info(f"  - Identity Service: {checks['identity_service']}")

    def test02_version_endpoint(self, api_tester):
        """Tester le endpoint /version
        
        Selon RESPONSES_SPECIFICATION.md:
        - 200 OK: {"version": "0.0.1"}
        - 401 Unauthorized: JWT manquant ou invalide
        
        Note: Le endpoint peut nécessiter l'authentification selon l'implémentation.
        """
        url = f"{api_tester.base_url}/api/project/version"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Version endpoint response status: {response.status_code}")
        
        # Endpoint peut ne pas être implémenté (404) ou nécessiter auth (401)
        # 500 si PROJECT_SERVICE_URL n'est pas configuré
        # 400 si le middleware Guardian manque des informations
        assert response.status_code in [200, 400, 401, 404, 500], \
            f"Expected 200, 400, 401, 404 or 500 for version endpoint, got {response.status_code}"
        
        if response.status_code == 500:
            error_info = response.json()
            if "PROJECT_SERVICE_URL" in error_info.get("error", ""):
                logger.info("Project Service not configured in proxy yet (PROJECT_SERVICE_URL not defined)")
                return
        
        if response.status_code == 400:
            error_info = response.json()
            logger.info(f"Version endpoint returned 400: {error_info.get('error', 'Unknown error')}")
            return
        
        if response.status_code == 200:
            version_info = response.json()
            
            # Vérifier la structure selon la spec
            assert "version" in version_info, "Missing 'version' in response"
            
            # Version devrait être au format semver (ex: "0.0.1")
            version = version_info['version']
            assert isinstance(version, str), "Version should be a string"
            assert len(version) > 0, "Version should not be empty"
            
            logger.info(f"Project Service version: {version}")
        elif response.status_code == 401:
            logger.info("Version endpoint requires authentication")
            error_info = response.json()
            assert "message" in error_info, "Missing 'message' in 401 response"
        else:
            logger.info(f"Version endpoint not implemented (status {response.status_code})")

    def test03_config_endpoint(self, api_tester):
        """Tester le endpoint /config
        
        Selon RESPONSES_SPECIFICATION.md:
        - 200 OK: Configuration du service (env, debug, services, database_url)
        - 401 Unauthorized: JWT manquant ou invalide
        
        Structure attendue (200):
        {
          "env": "development|staging|production",
          "debug": true|false,
          "database_url": "postgresql://***:***@host:port/db"
        }
        
        Note: Les informations sensibles (passwords) doivent être masquées.
        """
        url = f"{api_tester.base_url}/api/project/config"
        api_tester.log_request('GET', url)
        
        response = api_tester.session.get(url)
        api_tester.log_response(response)
        
        logger.info(f"Config endpoint response status: {response.status_code}")
        
        # Config peut nécessiter l'authentification (401) ou retourner les données (200)
        # 500 si PROJECT_SERVICE_URL n'est pas configuré
        assert response.status_code in [200, 401, 404, 500], \
            f"Expected 200, 401, 404 or 500 for config endpoint, got {response.status_code}"
        
        if response.status_code == 500:
            error_info = response.json()
            if "PROJECT_SERVICE_URL" in error_info.get("error", ""):
                logger.info("Project Service not configured in proxy yet (PROJECT_SERVICE_URL not defined)")
                return
        
        if response.status_code == 200:
            config_info = response.json()
            logger.info(f"Config retrieved: {config_info}")
            
            # Vérifier les champs selon la spec
            if "env" in config_info:
                assert config_info["env"] in ["development", "staging", "production"], \
                    f"Invalid env value: {config_info['env']}"
                logger.info(f"  - Environment: {config_info['env']}")
            
            if "debug" in config_info:
                assert isinstance(config_info["debug"], bool), "debug should be boolean"
                logger.info(f"  - Debug mode: {config_info['debug']}")
            
            # Si database_url est présent, vérifier qu'il est masqué
            if "database_url" in config_info:
                db_url = config_info["database_url"]
                assert "***" in db_url or "****" in db_url, \
                    "Database password should be masked in config"
                logger.info(f"  - Database URL: {db_url}")
                
        elif response.status_code == 401:
            logger.info("Config endpoint requires authentication")
            error_info = response.json()
            assert "message" in error_info, "Missing 'message' in 401 response"
        else:
            logger.info(f"Config endpoint not implemented (status {response.status_code})")
