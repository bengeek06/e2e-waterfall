"""
Tests pour l'export JSON via Basic I/O API
Endpoints testés:
- GET /api/basic-io/export?type=json - Export simple
- GET /api/basic-io/export?type=json&enrich=true - Export enrichi
- GET /api/basic-io/export?type=json&tree=true - Export arborescent
"""

import pytest
import logging
import sys
import json
from pathlib import Path
import requests
import time

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('basic_io')


class BasicIOAPITester:
    def __init__(self, app_config):
        self.session = requests.Session()
        self.base_url = app_config['web_url']
        self.session.verify = False
        
    def wait_for_api(self, endpoint: str, timeout: int = 120) -> bool:
        """Attendre qu'une API soit disponible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        return False
    
    def log_request(self, method: str, url: str, params: dict = None):
        """Log la requête envoyée"""
        print(f"\n>>> REQUEST: {method} {url}")
        if params:
            print(f">>> Params: {params}")
    
    def log_response(self, response: requests.Response):
        """Log la réponse reçue"""
        print(f"<<< RESPONSE: {response.status_code}")
        print(f"<<< Response headers: {dict(response.headers)}")


@pytest.mark.order(500)
class TestBasicIOExportJSON:
    """Tests d'export JSON"""
    
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return BasicIOAPITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        # L'API Auth est déjà initialisée par conftest.py
        
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        # Logger TOUS les cookies reçus
        logger.info(f"All response cookies: {dict(response.cookies)}")
        logger.info(f"All session cookies: {dict(api_tester.session.cookies)}")
        
        # Récupérer les cookies
        access_token = response.cookies.get('access_token')
        refresh_token = response.cookies.get('refresh_token')
        
        logger.info(f"Access token from response: {access_token}")
        logger.info(f"Refresh token from response: {refresh_token}")
        
        # FIX: Re-set cookies with correct domain (localhost instead of localhost.local)
        # This fixes domain mismatch that prevents requests.Session from auto-sending cookies
        api_tester.session.cookies.clear()
        if access_token:
            api_tester.session.cookies.set(
                'access_token', access_token,
                domain='localhost', path='/', secure=False
            )
        if refresh_token:
            api_tester.session.cookies.set(
                'refresh_token', refresh_token,
                domain='localhost', path='/', secure=False
            )
        
        logger.info("Cookies re-set with correct domain for auto-sending")
        
        # Retourner un dict avec les cookies (pour compatibilité, mais non utilisé)
        cookies = {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        
        assert cookies['access_token'] or cookies['refresh_token'], \
            "No auth cookies received"
        
        return cookies
    
    @pytest.fixture(scope="class")
    def user_info(self, api_tester, auth_token):
        """Récupérer les informations de l'utilisateur connecté"""
        assert auth_token is not None, "No auth cookies available"
        
        response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=auth_token
        )
        
        assert response.status_code == 200, f"Failed to verify token: {response.text}"
        
        user_data = response.json()
        logger.info(f"Connected user: {user_data.get('email')} (ID: {user_data.get('user_id')})")
        
        return {
            'user_id': user_data.get('user_id'),
            'company_id': user_data.get('company_id'),
            'email': user_data.get('email')
        }

    def test01_export_json_simple_without_enrich(self, api_tester, auth_token):
        """Tester l'export JSON simple sans enrichissement"""
        assert auth_token, "Authentication failed"
        
        # Export simple depuis l'endpoint users
        # URL interne Docker pour le service identity
        target_url = "http://identity_service:5000/users"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json",
            "enrich": "false"
        }
        
        api_tester.log_request('GET', url, params)
        # FIX: Pass cookies explicitly like Storage tests do
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export JSON with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'application/json' in content_type, \
            f"Expected JSON content type, got {content_type}"
        
        # Vérifier le Content-Disposition (download)
        # BUG: Header manquant actuellement - voir BUG_REPORT_BASIC_IO_EXPORT.md
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disposition, \
            "Expected attachment disposition (BUG: header missing - see BUG_REPORT_BASIC_IO_EXPORT.md)"
        
        # Parser le JSON
        data = response.json()
        assert isinstance(data, list), "Expected JSON array"
        
        if len(data) > 0:
            # Vérifier qu'il y a un champ _original_id
            first_record = data[0]
            assert '_original_id' in first_record, "Missing _original_id field"
            
            # Vérifier qu'il N'y a PAS de champ _references (pas d'enrichissement)
            assert '_references' not in first_record, \
                "Should not have _references field when enrich=false"
            
            logger.info(f"✅ Exported {len(data)} records without enrichment")
        else:
            logger.info("✅ Export successful but no data returned (empty dataset)")

    def test02_export_json_enriched(self, api_tester, auth_token):
        """Tester l'export JSON avec enrichissement (_references)"""
        assert auth_token, "Authentication failed"
        
        # Export enrichi depuis l'endpoint roles
        target_url = "http://guardian_service:5000/roles"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json",
            "enrich": "true"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)

    def test03_export_json_with_invalid_url(self, api_tester, auth_token):
        """Tester l'export avec une URL invalide"""
        assert auth_token is not None, "No auth cookies available"
        
        # URL inexistante
        target_url = "http://identity_service:5000/nonexistent_endpoint"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        # Devrait retourner 502 (bad gateway) ou 404
        assert response.status_code in [502, 404, 500], \
            f"Expected error status for invalid URL, got {response.status_code}"
        
        logger.info(f"✅ Invalid URL correctly rejected with {response.status_code}")

    def test04_export_json_missing_url_param(self, api_tester, auth_token):
        """Tester l'export JSON sans paramètre url (doit retourner 400)"""
        assert auth_token, "Authentication failed"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "type": "json"
            # url manquant intentionnellement
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        # Devrait retourner 400 (missing required parameter)
        assert response.status_code == 400, \
            f"Expected 400 for missing url parameter, got {response.status_code}: {response.text}"
        
        logger.info("✅ Missing url parameter correctly rejected with 400")

    def test05_export_json_invalid_type(self, api_tester, auth_token):
        """Tester l'export avec type invalide (doit retourner 400)"""
        assert auth_token, "Authentication failed"
        
        target_url = "http://identity_service:5000/users"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "invalid_type"  # Type invalide (ni json, ni csv, ni mermaid)
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        # Devrait retourner 400 (invalid type parameter)
        assert response.status_code == 400, \
            f"Expected 400 for invalid type, got {response.status_code}: {response.text}"
        
        logger.info("✅ Invalid type parameter correctly rejected with 400")

    def test06_export_json_without_auth(self, api_tester):
        """Tester l'export sans authentification"""
        
        target_url = "http://identity_service:5000/users"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json"
        }
        
        api_tester.log_request('GET', url, params)
        # Sans cookies d'auth - créer une nouvelle session sans cookies
        temp_session = requests.Session()
        response = temp_session.get(url, params=params)
        api_tester.log_response(response)
        
        # Devrait retourner 401 (unauthorized)
        assert response.status_code == 401, \
            f"Expected 401 for missing auth, got {response.status_code}"
        
        logger.info("✅ Missing authentication correctly rejected with 401")

    def test07_export_json_verify_original_id_format(self, api_tester, auth_token):
        """Vérifier le format du champ _original_id dans les exports JSON"""
        assert auth_token, "Authentication failed"
        
        target_url = "http://identity_service:5000/users"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json",
            "enrich": "false"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        assert response.status_code == 200
        
        data = response.json()
        
        if len(data) > 0:
            first_record = data[0]
            original_id = first_record.get('_original_id')
            
            assert original_id is not None, "Missing _original_id"
            assert isinstance(original_id, str), "_original_id should be a string"
            
            # Vérifier le format UUID (36 caractères avec tirets)
            assert len(original_id) == 36, f"UUID should be 36 chars, got {len(original_id)}"
            assert original_id.count('-') == 4, "UUID should have 4 dashes"
            
            logger.info(f"✅ _original_id has valid UUID format: {original_id}")
        else:
            logger.info("⚠️ No data to verify UUID format (empty dataset)")
