"""
Tests pour les endpoints de métadonnées et listing de Storage API

Tests couverts:
- test01_list_files_users_bucket: Lister les fichiers du bucket users
- test02_list_files_with_pagination: Pagination de la liste
- test03_list_files_empty_directory: Répertoire vide
- test04_get_metadata_existing_file: Récupérer métadonnées d'un fichier
- test05_update_metadata_tags: Mettre à jour les tags
- test06_update_metadata_description: Mettre à jour la description
"""

import pytest
import requests
import logging
import io

logger = logging.getLogger(__name__)

class TestStorageMetadata:
    """Tests pour les métadonnées et listing de fichiers"""
    


    @pytest.fixture(scope="class")
    def user_info(self, api_tester, session_auth_cookies, session_user_info):
        """Get current user info from JWT"""
        url = f"{api_tester.base_url}/api/auth/verify"
        response = api_tester.session.get(url, cookies=session_auth_cookies)
        
        assert response.status_code == 200, f"Failed to verify token: {response.text}"
        
        user_data = response.json()
        user_info = {
            'user_id': user_data['user_id'],
            'company_id': user_data['company_id'],
            'email': user_data['email']
        }
        
        print(f"\nConnected user: {user_info['email']} (ID: {user_info['user_id']})")
        return user_info
    
    @pytest.fixture(scope="class")
    def test_files(self, api_tester, session_auth_cookies, user_info):
        """Upload plusieurs fichiers de test pour les tests de listing et métadonnées"""
        user_id = user_info['user_id']
        upload_url = f"{api_tester.base_url}/api/storage/upload/proxy"
        
        files_data = []
        
        # Créer 3 fichiers de test
        for i in range(1, 4):
            content = f"Test file {i} content\n".encode() * 10
            file_obj = io.BytesIO(content)
            filename = f"test_metadata_file_{i}.txt"
            
            files = {'file': (filename, file_obj, 'text/plain')}
            data = {
                'bucket_type': 'users',
                'bucket_id': user_id,
                'logical_path': f'{user_id}/metadata_test/{filename}'
            }
            
            response = api_tester.session.post(upload_url, files=files, data=data, cookies=session_auth_cookies)
            assert response.status_code == 201, f"Failed to upload {filename}: {response.text}"
            
            upload_response = response.json()
            files_data.append({
                'file_id': upload_response['data']['file_id'],
                'filename': filename,
                'logical_path': f'{user_id}/metadata_test/{filename}',
                'size': len(content)
            })
            
            logger.info(f"Uploaded test file: {filename} (ID: {upload_response['data']['file_id']})")
        
        return files_data

    def test01_list_files_users_bucket(self, api_tester, session_auth_cookies, user_info, test_files):
        """Tester le listing des fichiers dans le bucket users"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # Lister les fichiers du répertoire metadata_test
        url = f"{api_tester.base_url}/api/storage/list"
        params = {
            "bucket": "users",
            "id": user_id,
            "path": f"{user_id}/metadata_test/"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to list files with status {response.status_code}: {response.text}"
        
        list_response = response.json()
        # La réponse réelle utilise 'files' et 'pagination' au lieu de 'data'
        assert "files" in list_response, "Missing files in response"
        assert "pagination" in list_response, "Missing pagination in response"
        
        items = list_response['files']
        assert len(items) >= 3, f"Expected at least 3 files, got {len(items)}"
        
        # Vérifier que nos fichiers de test sont présents
        file_ids = [f['file_id'] for f in test_files]
        found_files = [item for item in items if item.get('id') in file_ids]
        assert len(found_files) == 3, f"Expected 3 test files in listing, found {len(found_files)}"
        
        # Vérifier la structure des items
        for item in found_files:
            assert 'id' in item, "Missing id in item"
            assert 'logical_path' in item, "Missing logical_path in item"
            assert 'size' in item, "Missing size in item"
            assert 'created_at' in item, "Missing created_at in item"
        
        logger.info(f"✅ Listed {len(items)} files in bucket users")
        logger.info(f"Found {len(found_files)} test files")

    def test02_list_files_with_pagination(self, api_tester, session_auth_cookies, user_info, test_files):
        """Tester la pagination du listing"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # Lister avec limite de 2 fichiers
        url = f"{api_tester.base_url}/api/storage/list"
        params = {
            "bucket": "users",
            "id": user_id,
            "path": f"{user_id}/metadata_test/",
            "limit": 2,
            "page": 1
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to list files with status {response.status_code}: {response.text}"
        
        list_response = response.json()
        
        # Vérifier la pagination
        assert 'files' in list_response, "Missing files"
        assert 'pagination' in list_response, "Missing pagination"
        
        pagination = list_response['pagination']
        assert 'total_items' in pagination, "Missing total_items"
        assert 'page' in pagination, "Missing page number"
        assert 'limit' in pagination, "Missing limit"
        
        assert len(list_response['files']) <= 2, f"Expected max 2 items, got {len(list_response['files'])}"
        assert pagination['page'] == 1, f"Expected page 1, got {pagination['page']}"
        assert pagination['limit'] == 2, f"Expected limit 2, got {pagination['limit']}"
        
        logger.info(f"✅ Pagination works: {len(list_response['files'])} items on page {pagination['page']}")
        logger.info(f"Total files: {pagination['total_items']}")

    def test03_list_files_empty_directory(self, api_tester, session_auth_cookies, user_info):
        """Tester le listing d'un répertoire vide"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        
        # Lister un répertoire qui n'existe pas / est vide
        url = f"{api_tester.base_url}/api/storage/list"
        params = {
            "bucket": "users",
            "id": user_id,
            "path": f"{user_id}/empty_directory_xyz/"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to list empty directory with status {response.status_code}: {response.text}"
        
        list_response = response.json()
        assert "files" in list_response, "Missing files in response"
        assert "pagination" in list_response, "Missing pagination in response"
        
        files = list_response['files']
        assert len(files) == 0, f"Expected empty directory, got {len(files)} items"
        
        logger.info("✅ Empty directory returns empty list")

    def test04_get_metadata_existing_file(self, api_tester, session_auth_cookies, user_info, test_files):
        """Tester la récupération des métadonnées d'un fichier"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        file_info = test_files[0]
        
        # Récupérer les métadonnées - l'API attend bucket, id, logical_path
        url = f"{api_tester.base_url}/api/storage/metadata"
        params = {
            "bucket": "users",
            "id": user_id,
            "logical_path": file_info['logical_path']
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to get metadata with status {response.status_code}: {response.text}"
        
        metadata_response = response.json()
        
        # Vérifier la structure: {file: {...}, current_version: {...}}
        assert 'file' in metadata_response, "Missing 'file' in response"
        assert 'current_version' in metadata_response, "Missing 'current_version' in response"
        
        file_data = metadata_response['file']
        version_data = metadata_response['current_version']
        
        # Vérifier les champs du fichier
        assert file_data['id'] == file_info['file_id'], "File ID mismatch"
        assert 'bucket_type' in file_data, "Missing bucket_type"
        assert 'logical_path' in file_data, "Missing logical_path"
        assert 'owner_id' in file_data, "Missing owner_id"
        assert 'created_at' in file_data, "Missing created_at"
        assert 'status' in file_data, "Missing status"
        
        # Vérifier les champs de version
        assert 'mime_type' in version_data, "Missing mime_type in version"
        assert 'size' in version_data, "Missing size in version"
        assert 'version_number' in version_data, "Missing version_number"
        
        logger.info(f"✅ Metadata retrieved for file {file_info['file_id']}")
        logger.info(f"Status: {file_data['status']}, Version: {version_data['version_number']}")

    def test05_update_metadata_tags(self, api_tester, session_auth_cookies, user_info, test_files):
        """Tester la mise à jour des tags"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        file_info = test_files[1]
        
        # Mettre à jour les tags via PATCH
        url = f"{api_tester.base_url}/api/storage/metadata"
        params = {
            "bucket": "users",
            "id": user_id,
            "logical_path": file_info['logical_path']
        }
        update_data = {
            "tags": {
                "category": "test",
                "priority": "high",
                "reviewed": True
            }
        }
        
        api_tester.log_request('PATCH', url, update_data)
        response = api_tester.session.patch(url, params=params, json=update_data, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to update tags with status {response.status_code}: {response.text}"
        
        update_response = response.json()
        assert update_response.get('success') is True, "Update failed"
        assert 'data' in update_response, "Missing data in response"
        assert 'updated_fields' in update_response['data'], "Missing updated_fields"
        
        # Vérifier que les tags ont été mis à jour
        get_url = f"{api_tester.base_url}/api/storage/metadata"
        params = {
            "bucket": "users",
            "id": user_id,
            "logical_path": file_info['logical_path']
        }
        
        response = api_tester.session.get(get_url, params=params, cookies=session_auth_cookies)
        assert response.status_code == 200, "Failed to verify tags update"
        
        metadata_response = response.json()
        file_data = metadata_response['file']
        
        assert 'tags' in file_data, "Missing tags in metadata"
        assert file_data['tags']['category'] == 'test', "Tag 'category' not updated"
        assert file_data['tags']['priority'] == 'high', "Tag 'priority' not updated"
        assert file_data['tags']['reviewed'] is True, "Tag 'reviewed' not updated"
        
        logger.info(f"✅ Tags updated successfully for file {file_info['file_id']}")
        logger.info(f"Tags: {file_data['tags']}")

    def test06_update_metadata_description(self, api_tester, session_auth_cookies, user_info, test_files):
        """Tester la mise à jour de la description via tags"""
        assert session_auth_cookies is not None, "No auth cookies available"
        
        user_id = user_info['user_id']
        file_info = test_files[2]
        
        # Mettre à jour la description via tags avec PATCH
        url = f"{api_tester.base_url}/api/storage/metadata"
        params = {
            "bucket": "users",
            "id": user_id,
            "logical_path": file_info['logical_path']
        }
        update_data = {
            "tags": {
                "description": "Test file for metadata validation",
                "author": "automated-test"
            }
        }
        
        api_tester.log_request('PATCH', url, update_data)
        response = api_tester.session.patch(url, params=params, json=update_data, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to update description with status {response.status_code}: {response.text}"
        
        update_response = response.json()
        assert update_response.get('success') is True, "Update failed"
        assert 'data' in update_response, "Missing data in response"
        assert 'updated_fields' in update_response['data'], "Missing updated_fields"
        
        # Vérifier la mise à jour
        get_url = f"{api_tester.base_url}/api/storage/metadata"
        params = {
            "bucket": "users",
            "id": user_id,
            "logical_path": file_info['logical_path']
        }
        
        response = api_tester.session.get(get_url, params=params, cookies=session_auth_cookies)
        assert response.status_code == 200, "Failed to verify description update"
        
        metadata_response = response.json()
        file_data = metadata_response['file']
        
        assert 'tags' in file_data, "Missing tags in metadata"
        assert file_data['tags']['description'] == "Test file for metadata validation", \
            "Description not updated"
        assert file_data['tags']['author'] == "automated-test", "Author not updated"
        
        logger.info(f"✅ Description updated successfully for file {file_info['file_id']}")
        logger.info(f"Description: {file_data['tags']['description']}")
