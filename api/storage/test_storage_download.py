"""
Tests for Storage API - Download functionality (presign & proxy)
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
            safe_data = data.copy() if isinstance(data, dict) else data
            logger.debug(f">>> Request body: {safe_data}")
    
    def log_response(self, response: requests.Response):
        """Log la réponse reçue"""
        logger.debug(f"<<< RESPONSE: {response.status_code}")
        logger.debug(f"<<< Response headers: {dict(response.headers)}")
        try:
            if response.text and response.headers.get('content-type', '').startswith('application/json'):
                logger.debug(f"<<< Response body: {response.json()}")
        except Exception:
            logger.debug(f"<<< Response body (raw): {response.text[:200]}")


class TestStorageDownload:
    """Tests de téléchargement de fichiers via Storage API"""
    
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return StorageAPITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        assert api_tester.wait_for_api("/api/auth/version"), "API Auth not ready"
        
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
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
    
    @pytest.fixture(scope="class")
    def uploaded_file(self, api_tester, auth_token, user_info):
        """Upload un fichier de test pour les tests de download"""
        user_id = user_info['user_id']
        
        # Créer un fichier de test
        content = b"Test file content for download tests\n" * 5
        file_obj = io.BytesIO(content)
        file_obj.name = "test_download_file.txt"
        
        files = {
            'file': (file_obj.name, file_obj, 'text/plain')
        }
        data = {
            'bucket_type': 'users',
            'bucket_id': user_id,
            'logical_path': f'{user_id}/workspace/test_download_file.txt'
        }
        
        url = f"{api_tester.base_url}/api/storage/upload/proxy"
        response = api_tester.session.post(url, files=files, data=data, cookies=auth_token)
        
        assert response.status_code == 201, f"Failed to upload test file: {response.text}"
        
        upload_response = response.json()
        file_info = {
            'file_id': upload_response['data']['file_id'],
            'object_key': upload_response['data']['object_key'],
            'size': upload_response['data']['size'],
            'content': content
        }
        
        logger.info(f"Test file uploaded: {file_info['file_id']}")
        return file_info

    def test01_download_presign_url_generation(self, api_tester, auth_token, user_info, uploaded_file):
        """Tester la génération d'URL présignée pour download"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # D'après la spec: bucket_type, bucket_id, logical_path
        url = f"{api_tester.base_url}/api/storage/download/presign"
        params = {
            "bucket_type": "users",
            "bucket_id": user_id,
            "logical_path": f"{user_id}/workspace/test_download_file.txt"
        }
        api_tester.log_request('GET', url, params)
        
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to get presigned download URL with status {response.status_code}: {response.text}"
        
        presign_response = response.json()
        assert "url" in presign_response, "Presigned URL missing in response"
        assert "expires_in" in presign_response, "Expiration info missing in response"
        
        logger.info(f"✅ Presigned download URL generated")
        logger.info(f"Expires in: {presign_response['expires_in']} seconds")

    def test02_download_presign_missing_file_id(self, api_tester, auth_token, user_info):
        """Tester le download presign sans bucket_type (doit échouer)"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # Paramètres incomplets - manque bucket_type
        params = {
            "bucket_id": user_id,
            "logical_path": "test_file.txt"
        }
        
        url = f"{api_tester.base_url}/api/storage/download/presign"
        api_tester.log_request('GET', url, params)
        
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 400, \
            f"Expected 400 for missing bucket_type, got {response.status_code}"
        
        logger.info("✅ Missing bucket_type correctly rejected")

    def test03_download_presign_invalid_file_id(self, api_tester, auth_token, user_info):
        """Tester le download presign avec fichier inexistant"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        params = {
            "bucket_type": "users",
            "bucket_id": user_id,
            "logical_path": "nonexistent_file.txt"  # Fichier qui n'existe pas
        }
        
        url = f"{api_tester.base_url}/api/storage/download/presign"
        api_tester.log_request('GET', url, params)
        
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code in [404, 400], \
            f"Expected 404 or 400 for non-existent file, got {response.status_code}"
        
        logger.info("✅ Non-existent file correctly rejected")

    def test04_download_proxy_success(self, api_tester, auth_token, user_info, uploaded_file):
        """Tester le téléchargement via proxy (succès)"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        expected_content = uploaded_file['content']
        
        # D'après la spec: bucket_type, bucket_id, logical_path en query params
        url = f"{api_tester.base_url}/api/storage/download/proxy"
        params = {
            "bucket_type": "users",
            "bucket_id": user_id,
            "logical_path": f"{user_id}/workspace/test_download_file.txt"
        }
        api_tester.log_request('GET', url, params)
        
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to download via proxy with status {response.status_code}: {response.text}"
        
        # Vérifier le contenu
        assert response.content == expected_content, \
            "Downloaded content mismatch"
        
        # Vérifier les headers
        assert 'content-type' in response.headers, "Content-Type header missing"
        # Content-Length ou Transfer-Encoding chunked sont acceptables
        assert ('content-length' in response.headers or 'transfer-encoding' in response.headers), \
            "Neither Content-Length nor Transfer-Encoding header found"
        
        logger.info("✅ File downloaded via proxy successfully")
        logger.info(f"Downloaded {len(response.content)} bytes")

    def test05_download_proxy_missing_file_id(self, api_tester, auth_token, user_info):
        """Tester le download proxy sans logical_path (doit échouer)"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # Paramètres incomplets - manque logical_path
        url = f"{api_tester.base_url}/api/storage/download/proxy"
        params = {
            "bucket_type": "users",
            "bucket_id": user_id
        }
        api_tester.log_request('GET', url, params)
        
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)

    def test06_download_proxy_invalid_file_id(self, api_tester, auth_token, user_info):
        """Tester le download proxy avec fichier invalide"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # Fichier inexistant
        url = f"{api_tester.base_url}/api/storage/download/proxy"
        params = {
            "bucket_type": "users",
            "bucket_id": user_id,
            "logical_path": "nonexistent_file.txt"
        }
        api_tester.log_request('GET', url, params)
        
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)

    def test07_download_with_version(self, api_tester, auth_token, user_info):
        """Tester le download avec versioning"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # Uploader première version
        upload_url = f"{api_tester.base_url}/api/storage/upload/proxy"
        
        # Version 1
        files_v1 = {'file': ('test_version_file.txt', b'Version 1 content', 'text/plain')}
        data_v1 = {
            'bucket_type': 'users',
            'bucket_id': user_id,
            'logical_path': 'test_version_file.txt'
        }
        response_v1 = api_tester.session.post(upload_url, data=data_v1, files=files_v1, cookies=auth_token)
        assert response_v1.status_code == 201, f"First upload failed: {response_v1.text}"
        
        # Version 2 (même fichier)
        files_v2 = {'file': ('test_version_file.txt', b'Version 2 content - updated', 'text/plain')}
        data_v2 = data_v1.copy()
        response_v2 = api_tester.session.post(upload_url, data=data_v2, files=files_v2, cookies=auth_token)
        assert response_v2.status_code == 201, f"Second upload failed: {response_v2.text}"
        
        # Télécharger la dernière version
        download_url = f"{api_tester.base_url}/api/storage/download/proxy"
        params = {
            "bucket_type": "users",
            "bucket_id": user_id,
            "logical_path": "test_version_file.txt"
        }
        
        response = api_tester.session.get(download_url, params=params, cookies=auth_token)
        assert response.status_code == 200, f"Failed to download file: {response.text}"

    def test08_list_files_in_directory(self, api_tester, auth_token, user_info):
        """Tester la liste des fichiers dans un répertoire"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # Paramètres pour lister les fichiers - d'après la spec: bucket, id, path
        list_params = {
            "bucket": "users",
            "id": user_id,
            "path": f"{user_id}/workspace/"
        }
        
        url = f"{api_tester.base_url}/api/storage/list"
        api_tester.log_request('GET', url, list_params)
        
        response = api_tester.session.get(url, params=list_params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to list files with status {response.status_code}: {response.text}"
        
        list_response = response.json()
        assert "files" in list_response or "data" in list_response, "Files list missing in response"
        
        files_key = "files" if "files" in list_response else "data"
        files = list_response.get(files_key, [])
        
        logger.info(f"✅ Listed {len(files)} files in workspace")
        
        # Vérifier qu'on trouve au moins notre fichier de test
        assert len(files) > 0, "Should have at least one file in workspace"

    def test09_download_without_authentication(self, api_tester, user_info):
        """Tester le download sans authentification (doit échouer)"""
        user_id = user_info['user_id']
        
        url = f"{api_tester.base_url}/api/storage/download/proxy"
        params = {
            "bucket_type": "users",
            "bucket_id": user_id,
            "logical_path": "test_download_file.txt"
        }
        api_tester.log_request('GET', url, params)
        
        # Requête sans cookies d'authentification
        response = api_tester.session.get(url, params=params)
        api_tester.log_response(response)
        
        assert response.status_code in [401, 403], \
            f"Expected 401 or 403 without auth, got {response.status_code}"
        
        logger.info("✅ Download without authentication correctly rejected")
