"""
Tests for Storage API - Upload functionality (presign & proxy)
"""
import requests
import time
import pytest
import sys
from pathlib import Path
import urllib3
import io

# Désactiver les warnings SSL pour les tests (certificats auto-signés)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('storage')


class StorageAPITester:
    def __init__(self, app_config):
        self.session = requests.Session()
        self.base_url = app_config['web_url']
        # Ignorer les certificats auto-signés pour les tests
        self.session.verify = False
        
    def wait_for_api(self, endpoint: str, timeout: int = 120) -> bool:
        """Attendre qu'une API soit disponible"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                logger.debug(f"wait_for_api - Status: {response.status_code}")
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException as e:
                logger.debug(f"Request exception: {e}")
                pass
            time.sleep(2)
        return False
    
    def log_request(self, method: str, url: str, data: dict = None):
        """Log la requête envoyée"""
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            # Masquer les données sensibles
            safe_data = data.copy() if isinstance(data, dict) else data
            logger.debug(f">>> Request body: {safe_data}")
    
    def log_response(self, response: requests.Response):
        """Log la réponse reçue"""
        logger.debug(f"<<< RESPONSE: {response.status_code}")
        logger.debug(f"<<< Response headers: {dict(response.headers)}")
        try:
            if response.text:
                logger.debug(f"<<< Response body: {response.json()}")
        except:
            logger.debug(f"<<< Response body (raw): {response.text[:200]}")


class TestStorageUpload:
    """Tests d'upload de fichiers via Storage API"""
    
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return StorageAPITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        # Attendre que l'API auth soit prête
        assert api_tester.wait_for_api("/api/auth/version"), "API Auth not ready"
        
        # Se connecter pour obtenir les tokens
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            # Retourner un dict avec les valeurs des cookies (pas l'objet cookies)
            access_token = response.cookies.get('access_token')
            refresh_token = response.cookies.get('refresh_token')
            return {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        return None
    
    @pytest.fixture(scope="class")
    def user_info(self, api_tester, auth_token):
        """Récupérer les informations de l'utilisateur connecté"""
        assert auth_token is not None, "No auth cookies available"
        
        # Vérifier le token pour obtenir user_id
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
    
    @pytest.fixture(scope="function")
    def test_file(self):
        """Créer un fichier de test temporaire"""
        content = b"Test file content for Storage API upload tests\n" * 10
        file_obj = io.BytesIO(content)
        file_obj.name = "test_upload_file.txt"
        return file_obj, len(content)

    def test01_upload_presign_url_generation(self, api_tester, auth_token, user_info):
        """Tester la génération d'URL présignée pour upload"""
        assert auth_token is not None, "No auth cookies available"
        assert user_info is not None, "No user info available"
        
        user_id = user_info['user_id']
        
        # Préparer les données pour la requête d'URL présignée
        # Le répertoire /users/<user_id>/workspace est créé automatiquement par identity
        # logical_path ne doit PAS commencer par '/'
        presign_data = {
            "bucket_type": "users",
            "bucket_id": user_id,  # UUID de l'utilisateur
            "logical_path": f"{user_id}/workspace/test_presign_upload.txt"
        }
        
        url = f"{api_tester.base_url}/api/storage/upload/presign"
        api_tester.log_request('POST', url, presign_data)
        
        response = api_tester.session.post(url, json=presign_data, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to get presigned URL with status {response.status_code}: {response.text}"
        
        presign_response = response.json()
        assert "url" in presign_response, "Presigned URL missing in response"
        assert "object_key" in presign_response, "Object key missing in response"
        assert "expires_in" in presign_response, "Expiration info missing in response"
        
        logger.info(f"✅ Presigned URL generated for object_key: {presign_response['object_key']}")
        logger.info(f"Expires in: {presign_response['expires_in']} seconds")

    def test02_upload_presign_missing_bucket(self, api_tester, auth_token):
        """Tester l'upload presign sans bucket_type (doit échouer)"""
        assert auth_token is not None, "No auth cookies available"
        
        presign_data = {
            "bucket_id": "1",
            "logical_path": "/test_file.txt",
            "content_type": "text/plain"
            # bucket_type manquant
        }
        
        url = f"{api_tester.base_url}/api/storage/upload/presign"
        api_tester.log_request('POST', url, presign_data)
        
        response = api_tester.session.post(url, json=presign_data, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 400, \
            f"Expected 400 for missing bucket, got {response.status_code}"
        
        logger.info("✅ Missing bucket correctly rejected")

    def test03_upload_presign_invalid_bucket(self, api_tester, auth_token):
        """Tester l'upload presign avec bucket_type invalide"""
        assert auth_token is not None, "No auth cookies available"
        
        presign_data = {
            "bucket_type": "invalid_bucket",
            "bucket_id": "1",
            "logical_path": "/test_file.txt",
            "content_type": "text/plain"
        }
        
        url = f"{api_tester.base_url}/api/storage/upload/presign"
        api_tester.log_request('POST', url, presign_data)
        
        response = api_tester.session.post(url, json=presign_data, cookies=auth_token)
        api_tester.log_response(response)
        
        # Devrait retourner 400 (bad request) ou 403 (forbidden)
        assert response.status_code in [400, 403], \
            f"Expected 400 or 403 for invalid bucket, got {response.status_code}"
        
        logger.info("✅ Invalid bucket correctly rejected")

    def test04_upload_proxy_success(self, api_tester, auth_token, user_info, test_file):
        """Tester l'upload via proxy (succès)"""
        assert auth_token is not None, "No auth cookies available"
        assert user_info is not None, "No user info available"
        
        user_id = user_info['user_id']
        file_obj, file_size = test_file
        
        # Préparer le multipart form data
        files = {
            'file': (file_obj.name, file_obj, 'text/plain')
        }
        data = {
            'bucket_type': 'users',
            'bucket_id': user_id,
            'logical_path': f'{user_id}/workspace/test_proxy_upload.txt'
        }
        
        url = f"{api_tester.base_url}/api/storage/upload/proxy"
        api_tester.log_request('POST', url, data)
        
        response = api_tester.session.post(url, files=files, data=data, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 201, \
            f"Failed to upload via proxy with status {response.status_code}: {response.text}"
        
        upload_response = response.json()
        assert "data" in upload_response, "Data field missing in response"
        assert "file_id" in upload_response["data"], "File ID missing in response data"
        assert "size" in upload_response["data"], "File size missing in response data"
        assert upload_response["data"]["size"] == file_size, \
            f"File size mismatch: expected {file_size}, got {upload_response['data']['size']}"
        
        logger.info(f"✅ File uploaded via proxy: {upload_response['data']['file_id']}")
        logger.info(f"Size: {upload_response['data']['size']} bytes")
        logger.info(f"Version: {upload_response['data'].get('version_number', 'N/A')}")

    def test05_upload_proxy_missing_file(self, api_tester, auth_token):
        """Tester l'upload proxy sans fichier (doit échouer)"""
        assert auth_token is not None, "No auth cookies available"
        
        data = {
            'bucket_type': 'users',
            'bucket_id': '1',
            'logical_path': '/test_file.txt'
        }
        
        url = f"{api_tester.base_url}/api/storage/upload/proxy"
        api_tester.log_request('POST', url, data)
        
        response = api_tester.session.post(url, data=data, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 400, \
            f"Expected 400 for missing file, got {response.status_code}"
        
        logger.info("✅ Missing file correctly rejected")

    def test06_upload_proxy_large_file(self, api_tester, auth_token, user_info):
        """Tester l'upload d'un fichier plus volumineux via proxy"""
        assert auth_token is not None, "No auth cookies available"
        assert user_info is not None, "No user info available"
        
        user_id = user_info['user_id']
        
        # Créer un fichier de ~1MB
        content = b"X" * (1024 * 1024)  # 1MB
        file_obj = io.BytesIO(content)
        file_obj.name = "large_test_file.bin"
        
        files = {
            'file': (file_obj.name, file_obj, 'application/octet-stream')
        }
        data = {
            'bucket_type': 'users',
            'bucket_id': user_id,
            'logical_path': f'{user_id}/workspace/large_test_file.bin'
        }
        
        url = f"{api_tester.base_url}/api/storage/upload/proxy"
        api_tester.log_request('POST', url, data)
        
        response = api_tester.session.post(url, files=files, data=data, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 201, \
            f"Failed to upload large file with status {response.status_code}: {response.text}"
        
        upload_response = response.json()
        assert "data" in upload_response, "Data field missing in response"
        assert "file_id" in upload_response["data"], "File ID missing in response data"
        assert upload_response["data"]["size"] == len(content), \
            f"File size mismatch: expected {len(content)}, got {upload_response['data']['size']}"
        
        logger.info(f"✅ Large file (1MB) uploaded successfully: {upload_response['data']['file_id']}")

    def test07_upload_with_metadata(self, api_tester, auth_token, user_info, test_file):
        """Tester l'upload avec métadonnées personnalisées"""
        assert auth_token is not None, "No auth cookies available"
        assert user_info is not None, "No user info available"
        
        user_id = user_info['user_id']
        file_obj, _ = test_file
        
        files = {
            'file': (file_obj.name, file_obj, 'text/plain')
        }
        data = {
            'bucket_type': 'users',
            'bucket_id': user_id,
            'logical_path': f'{user_id}/workspace/test_with_metadata.txt',
            'metadata': '{"description": "Test file with custom metadata", "project": "waterfall_tests"}'
        }
        
        url = f"{api_tester.base_url}/api/storage/upload/proxy"
        api_tester.log_request('POST', url, data)
        
        response = api_tester.session.post(url, files=files, data=data, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 201, \
            f"Failed to upload with metadata, status {response.status_code}: {response.text}"
        
        upload_response = response.json()
        assert "data" in upload_response, "Data field missing in response"
        assert "file_id" in upload_response["data"], "File ID missing in response data"
        
        logger.info(f"✅ File with metadata uploaded: {upload_response['data']['file_id']}")
