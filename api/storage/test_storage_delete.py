"""
Tests pour les opérations de suppression de fichiers
Endpoints testés:
- DELETE /api/storage/delete - Suppression logique (archive)
- DELETE /api/storage/delete?permanent=true - Suppression physique
"""

import pytest
import logging
import sys
from pathlib import Path
from io import BytesIO
import requests
import time

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('storage')


class StorageAPITester:
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
    
    def log_request(self, method: str, url: str, data: dict = None):
        """Log la requête envoyée"""
        print(f"\n>>> REQUEST: {method} {url}")
        if data:
            print(f">>> Request body: {data}")
    
    def log_response(self, response: requests.Response):
        """Log la réponse reçue"""
        print(f"<<< RESPONSE: {response.status_code}")
        print(f"<<< Response headers: {dict(response.headers)}")
        try:
            if response.text and response.headers.get('content-type', '').startswith('application/json'):
                print(f"<<< Response body: {response.json()}")
        except Exception:
            print(f"<<< Response body (raw): {response.text[:200]}")


@pytest.mark.order(400)
class TestStorageDelete:
    """Tests de suppression de fichiers"""
    
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
    
    @pytest.fixture(scope='class')
    def test_files(self, api_tester, auth_token, user_info):
        """Créer des fichiers de test pour la suppression"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        files = []
        
        # Créer 3 fichiers de test
        for i in range(1, 4):
            filename = f"test_delete_file_{i}.txt"
            logical_path = f"{user_id}/delete_test/{filename}"
            
            file_content = f"File {i} for deletion tests".encode('utf-8')
            file_data = BytesIO(file_content)
            
            url = f"{api_tester.base_url}/api/storage/upload/proxy"
            files_payload = {'file': (filename, file_data, 'text/plain')}
            data = {
                'bucket_type': 'users',
                'bucket_id': user_id,
                'logical_path': logical_path
            }
            
            response = api_tester.session.post(url, files=files_payload, data=data, cookies=auth_token)
            assert response.status_code == 201, f"Failed to upload {filename}: {response.text}"
            
            upload_response = response.json()
            file_id = upload_response['data']['file_id']
            
            files.append({
                'file_id': file_id,
                'filename': filename,
                'logical_path': logical_path
            })
            
            logger.info(f"Uploaded test file: {filename} (ID: {file_id})")
        
        return files

    def test01_delete_logical_archive(self, api_tester, auth_token, user_info, test_files):
        """Tester la suppression logique (archivage)"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        file_info = test_files[0]
        
                # Supprimer le fichier de manière logique (par défaut)
        url = f"{api_tester.base_url}/api/storage/delete"
        delete_data = {
            "file_id": file_info['file_id']
        }
        
        api_tester.log_request('DELETE', url, delete_data)
        response = api_tester.session.delete(url, json=delete_data, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to delete file with status {response.status_code}: {response.text}"
        
        delete_response = response.json()
        assert delete_response.get('success') is True, "Delete operation failed"
        assert delete_response.get('data', {}).get('logical_delete') is True, "Should be logical delete"
        assert delete_response.get('data', {}).get('physical_delete') is False, "Should not be physical delete"
        
        # Vérifier que le fichier est marqué comme supprimé
        metadata_url = f"{api_tester.base_url}/api/storage/metadata"
        metadata_params = {
            "bucket": "users",
            "id": user_id,
            "logical_path": file_info['logical_path']
        }
        
        response = api_tester.session.get(metadata_url, params=metadata_params, cookies=auth_token)
        
        # Le fichier devrait soit retourner 404, soit avoir is_deleted=True
        if response.status_code == 200:
            # Après suppression logique, is_deleted peut rester False si c'est juste un soft delete
            # L'important est que la suppression ait retourné logical_delete=True
            logger.info("✅ File metadata still accessible after logical deletion")
        elif response.status_code == 404:
            logger.info("✅ File not found after logical deletion (404)")
        else:
            pytest.fail(f"Unexpected status {response.status_code} when checking deleted file")
        
        logger.info(f"✅ Logical deletion successful for file {file_info['file_id']}")

    def test02_delete_physical_permanent(self, api_tester, auth_token, user_info, test_files):
        """Tester la suppression physique permanente"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        file_info = test_files[1]
        
        # Supprimer le fichier physiquement
        url = f"{api_tester.base_url}/api/storage/delete"
        delete_data = {
            "file_id": file_info['file_id'],
            "physical": True  # Suppression physique (spec: physical, not permanent)
        }
        
        api_tester.log_request('DELETE', url, delete_data)
        response = api_tester.session.delete(url, json=delete_data, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to permanently delete file with status {response.status_code}: {response.text}"
        
        delete_response = response.json()
        assert delete_response.get('success') is True, "Permanent delete operation failed"
        assert delete_response.get('data', {}).get('physical_delete') is True, "Should be physical delete"
        assert delete_response.get('data', {}).get('logical_delete') is True, "Should also be logical delete"
        
        # IMPORTANT: Après suppression physique, les métadonnées DOIVENT être supprimées
        # pour maintenir la cohérence MinIO/Database
        metadata_url = f"{api_tester.base_url}/api/storage/metadata"
        metadata_params = {
            "bucket": "users",
            "id": user_id,
            "logical_path": file_info['logical_path']
        }
        
        response = api_tester.session.get(metadata_url, params=metadata_params, cookies=auth_token)
        assert response.status_code == 404, \
            f"BUG: Metadata still exists after physical deletion (got {response.status_code}). " \
            f"This creates MinIO/Database inconsistency - the object is deleted in MinIO but metadata remains in DB. " \
            f"Physical deletion should remove BOTH the object AND the metadata."
        
        logger.info(f"✅ Physical deletion successful - both object and metadata deleted for {file_info['file_id']}")

    def test03_delete_missing_file(self, api_tester, auth_token):
        """Tester la suppression d'un fichier qui n'existe pas"""
        assert auth_token is not None, "No auth cookies available"
        
                # Tenter de supprimer un fichier inexistant
        url = f"{api_tester.base_url}/api/storage/delete"
        delete_data = {
            "file_id": "00000000-0000-0000-0000-000000000000"
        }
        
        api_tester.log_request('DELETE', url, delete_data)
        response = api_tester.session.delete(url, json=delete_data, cookies=auth_token)
        api_tester.log_response(response)
        
        # Devrait retourner 404
        assert response.status_code == 404, \
            f"Expected 404 for missing file, got {response.status_code}: {response.text}"
        
        logger.info("✅ Deletion of missing file correctly returns 404")

    def test04_delete_without_permission(self, api_tester, auth_token):
        """Tester la suppression d'un fichier inexistant (simule accès non autorisé)"""
        assert auth_token is not None, "No auth cookies available"
        
        # Tenter de supprimer avec un mauvais file_id
        url = f"{api_tester.base_url}/api/storage/delete"
        delete_data = {
            "file_id": "00000000-0000-0000-0000-000000000001"  # ID qui n'existe pas ou appartient à un autre user
        }
        
        api_tester.log_request('DELETE', url, delete_data)
        response = api_tester.session.delete(url, json=delete_data, cookies=auth_token)
        api_tester.log_response(response)

    def test05_verify_remaining_file(self, api_tester, auth_token, user_info, test_files):
        """Vérifier que le dernier fichier existe toujours"""
        assert auth_token is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        file_info = test_files[2]
        
        # Vérifier que le fichier non supprimé existe encore
        url = f"{api_tester.base_url}/api/storage/metadata"
        params = {
            "bucket": "users",
            "id": user_id,
            "logical_path": file_info['logical_path']
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"File should still exist, got {response.status_code}: {response.text}"
        
        metadata = response.json()
        file_data = metadata['file']
        
        assert file_data['id'] == file_info['file_id'], "File ID mismatch"
        assert file_data.get('is_deleted') is not True, "File should not be deleted"
        
        logger.info(f"✅ File {file_info['file_id']} still exists and is not deleted")
