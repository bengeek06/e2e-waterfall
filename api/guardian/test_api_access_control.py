"""
This module contains tests for the Guardian Access Control API endpoint.
Tests the /check-access endpoint which is the core of the RBAC system.
"""

import requests
import time
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('guardian')

class APITester:
    def __init__(self, app_config):
        self.session = requests.Session()
        self.base_url = app_config['web_url']
        # Ignorer les certificats auto-signés pour les tests
        self.session.verify = False
        self.auth_cookies = None
    
    @staticmethod
    def log_request(method, url, data=None, cookies=None):
        """Log une requête HTTP avec détails"""
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            # Masquer les mots de passe dans les logs
            safe_data = data.copy() if isinstance(data, dict) else data
            if isinstance(safe_data, dict) and 'password' in safe_data:
                safe_data['password'] = '***'
            logger.debug(f">>> Request body: {safe_data}")
        if cookies:
            # Logger les cookies utilisés (tronqués pour sécurité)
            for key, value in cookies.items():
                display_value = f"{value[:50]}..." if len(value) > 50 else value
                logger.debug(f">>> Using {key}: {display_value}")
    
    @staticmethod
    def log_response(response):
        """Log une réponse HTTP avec détails"""
        logger.debug(f"<<< RESPONSE: {response.status_code}")
        logger.debug(f"<<< Response headers: {dict(response.headers)}")
        try:
            if response.text:
                logger.debug(f"<<< Response body: {response.json()}")
        except:
            logger.debug(f"<<< Response body (raw): {response.text}")
        
    def set_auth_cookies(self, cookies):
        """Définir les cookies d'authentification"""
        self.auth_cookies = cookies
        # Forcer l'ajout des cookies à la session
        for cookie in cookies:
            self.session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
        
    def wait_for_api(self, endpoint: str, timeout: int = 10) -> bool:
        """Attendre qu'une API soit disponible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                logger.debug(f"wait_for_api - Status: {response.status_code}, Response: {response.text[:100]}...")
                if response.status_code == 200:
                    return True
                elif response.status_code in [401, 403]:
                    logger.warning(f"Authentication issue detected: {response.status_code}")
                    return False  # Ne pas continuer si c'est un problème d'auth
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request exception: {e}")
                pass
            time.sleep(2)
        return False

class TestAPIAccessControl:
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return APITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        # Attendre que l'API auth soit prête
        assert api_tester.wait_for_api("/api/auth/version"), "API Auth not ready"
        
        # Créer un utilisateur de test et s'authentifier
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            # Retourner les cookies de réponse pour avoir accès aux deux tokens
            return response.cookies
        return None
    
    @pytest.fixture(scope="class")
    def setup_test_data(self, api_tester, auth_token):
        """Configurer les données de test (role, policy, permission)"""
        assert auth_token is not None, "No auth cookies available"
        
        cookies_dict = {
            'access_token': auth_token.get('access_token'),
            'refresh_token': auth_token.get('refresh_token')
        }
        
        # Récupérer le user_id et company_id depuis le token
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=cookies_dict
        )
        assert verify_response.status_code == 200
        token_data = verify_response.json()
        
        # Sauvegarder pour les autres tests
        api_tester.cookies_dict = cookies_dict
        api_tester.user_id = token_data['user_id']
        api_tester.company_id = token_data['company_id']
        
        logger.info(f"Test setup - User ID: {api_tester.user_id}, Company ID: {api_tester.company_id}")
        
        return {
            'user_id': api_tester.user_id,
            'company_id': api_tester.company_id,
            'cookies': cookies_dict
        }

    def test01_check_access_with_valid_permission(self, api_tester, auth_token, setup_test_data):
        """Tester le check-access avec une permission valide"""
        
        # Récupérer une permission existante
        url = f"{api_tester.base_url}/api/guardian/permissions"
        api_tester.log_request("GET", url, cookies=api_tester.cookies_dict)
        
        permissions_response = api_tester.session.get(url, cookies=api_tester.cookies_dict)
        api_tester.log_response(permissions_response)
        
        assert permissions_response.status_code == 200
        permissions = permissions_response.json()
        assert len(permissions) > 0, "No permissions available for testing"
        
        # Utiliser la première permission
        test_permission = permissions[0]
        logger.info(f"Using permission: {test_permission}")
        
        # Construire la requête check-access
        check_access_data = {
            "user_id": setup_test_data['user_id'],
            "company_id": setup_test_data['company_id'],
            "service": test_permission['service'],
            "resource_name": test_permission['resource_name'],
            "operation": test_permission['operations'][0] if test_permission['operations'] else "read"
        }
        
        url = f"{api_tester.base_url}/api/guardian/check-access"
        api_tester.log_request("POST", url, data=check_access_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=check_access_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Check access response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'access_granted' in result, "Missing access_granted field in response"
        assert 'reason' in result, "Missing reason field in response"
        assert result['user_id'] == setup_test_data['user_id']
        assert result['company_id'] == setup_test_data['company_id']
        assert result['service'] == check_access_data['service']
        assert result['resource_name'] == check_access_data['resource_name']
        assert result['operation'] == check_access_data['operation']
        
        logger.info(f"Access granted: {result['access_granted']}, Reason: {result['reason']}")

    def test02_check_access_denied(self, api_tester, auth_token, setup_test_data):
        """Tester le check-access pour une permission non attribuée (accès refusé)"""
        
        # Construire une requête pour une ressource inexistante ou non autorisée
        check_access_data = {
            "user_id": setup_test_data['user_id'],
            "company_id": setup_test_data['company_id'],
            "service": "test_service",
            "resource_name": "non_existent_resource",
            "operation": "delete"
        }
        
        url = f"{api_tester.base_url}/api/guardian/check-access"
        api_tester.log_request("POST", url, data=check_access_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=check_access_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Check access response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'access_granted' in result
        assert result['access_granted'] == False, "Expected access to be denied"
        assert 'reason' in result
        
        logger.info(f"✅ Access correctly denied: {result['reason']}")

    def test03_check_access_invalid_operation(self, api_tester, auth_token, setup_test_data):
        """Tester le check-access avec une opération invalide"""
        
        check_access_data = {
            "user_id": setup_test_data['user_id'],
            "company_id": setup_test_data['company_id'],
            "service": "guardian",
            "resource_name": "role",
            "operation": "invalid_operation"  # Opération non valide
        }
        
        url = f"{api_tester.base_url}/api/guardian/check-access"
        api_tester.log_request("POST", url, data=check_access_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=check_access_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Check access response status: {response.status_code}")
        
        # L'API peut retourner 400 (Bad Request) ou 200 avec access_granted=false
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        if response.status_code == 400:
            logger.info("✅ Invalid operation correctly rejected with 400")
        else:
            result = response.json()
            logger.info(f"Access granted: {result.get('access_granted')}, Reason: {result.get('reason')}")

    def test04_check_access_missing_fields(self, api_tester, auth_token, setup_test_data):
        """Tester le check-access avec des champs manquants"""
        
        # Requête sans user_id
        check_access_data = {
            "company_id": setup_test_data['company_id'],
            "service": "guardian",
            "resource_name": "role",
            "operation": "read"
        }
        
        url = f"{api_tester.base_url}/api/guardian/check-access"
        api_tester.log_request("POST", url, data=check_access_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=check_access_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Check access response status: {response.status_code}")
        
        # Devrait retourner 400 Bad Request pour champs manquants
        assert response.status_code == 400, f"Expected 400 for missing fields, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert 'message' in result or 'errors' in result
        logger.info(f"✅ Missing fields correctly rejected: {result}")

    def test05_check_access_different_company(self, api_tester, auth_token, setup_test_data):
        """Tester le check-access avec un company_id différent (isolation multi-tenant)"""
        
        fake_company_id = "00000000-0000-0000-0000-000000000000"
        
        check_access_data = {
            "user_id": setup_test_data['user_id'],
            "company_id": fake_company_id,  # Company ID différent
            "service": "guardian",
            "resource_name": "role",
            "operation": "read"
        }
        
        url = f"{api_tester.base_url}/api/guardian/check-access"
        api_tester.log_request("POST", url, data=check_access_data, cookies=api_tester.cookies_dict)
        
        response = api_tester.session.post(
            url,
            json=check_access_data,
            cookies=api_tester.cookies_dict
        )
        
        api_tester.log_response(response)
        logger.info(f"Check access response status: {response.status_code}")
        
        # L'accès devrait être refusé ou l'API devrait retourner une erreur
        assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            result = response.json()
            # L'accès devrait être refusé car le company_id ne correspond pas
            assert result['access_granted'] == False, "Access should be denied for different company"
            logger.info(f"✅ Access correctly denied for different company: {result['reason']}")
        else:
            logger.info("✅ Different company access correctly forbidden with 403")

    def test06_check_access_all_operations(self, api_tester, auth_token, setup_test_data):
        """Tester le check-access pour toutes les opérations standard"""
        
        operations = ['list', 'create', 'read', 'update', 'delete']
        
        for operation in operations:
            check_access_data = {
                "user_id": setup_test_data['user_id'],
                "company_id": setup_test_data['company_id'],
                "service": "guardian",
                "resource_name": "role",
                "operation": operation
            }
            
            url = f"{api_tester.base_url}/api/guardian/check-access"
            api_tester.log_request("POST", url, data=check_access_data, cookies=api_tester.cookies_dict)
            
            response = api_tester.session.post(
                url,
                json=check_access_data,
                cookies=api_tester.cookies_dict
            )
            
            api_tester.log_response(response)
            
            assert response.status_code == 200, f"Expected 200 for operation {operation}, got {response.status_code}: {response.text}"
            
            result = response.json()
            assert 'access_granted' in result
            assert result['operation'] == operation
            
            logger.info(f"Operation '{operation}': access_granted={result['access_granted']}, reason={result['reason']}")
        
        logger.info("✅ All operations tested successfully")
