"""
Tests for Basic I/O API - CSV Export functionality
"""
import requests
import time
import pytest
import sys
from pathlib import Path
import urllib3
import csv
import io

# Désactiver les warnings SSL pour les tests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    
    def log_request(self, method: str, url: str, data: dict = None):
        """Log la requête envoyée"""
        logger.debug(f">>> REQUEST: {method} {url}")
        if data:
            logger.debug(f">>> Request params: {data}")
    
    def log_response(self, response: requests.Response):
        """Log la réponse reçue"""
        logger.debug(f"<<< RESPONSE: {response.status_code}")
        logger.debug(f"<<< Response headers: {dict(response.headers)}")
        # Ne pas logger le contenu CSV (peut être très long)
        logger.debug(f"<<< Response size: {len(response.content)} bytes")


class TestBasicIOExportCSV:
    """Tests d'export CSV via Basic I/O API"""
    
    @pytest.fixture(scope="class")
    def api_tester(self, app_config):
        return BasicIOAPITester(app_config)
    
    @pytest.fixture(scope="class")
    def auth_token(self, api_tester, app_config):
        """Obtenir un token d'authentification"""
        login_data = {
            "email": app_config['login'],
            "password": app_config['password']
        }
        
        response = api_tester.session.post(
            f"{api_tester.base_url}/api/auth/login",
            json=login_data
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        # Récupérer les cookies
        access_token = response.cookies.get('access_token')
        refresh_token = response.cookies.get('refresh_token')
        
        cookies = {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        
        assert cookies['access_token'] or cookies['refresh_token'], \
            "No auth cookies received"
        
        return cookies

    def test01_export_csv_simple(self, api_tester, auth_token):
        """Tester l'export CSV basique depuis users endpoint"""
        assert auth_token, "Authentication failed"
        
        # Export CSV depuis l'endpoint users
        target_url = "http://identity_service:5000/users"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "csv"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export CSV with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'text/csv' in content_type, \
            f"Expected CSV content type, got {content_type}"
        
        # Vérifier le Content-Disposition (download)
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disposition, \
            f"Expected attachment disposition, got {content_disposition}"
        assert '.csv' in content_disposition, \
            "Expected .csv extension in filename"
        
        # Parser le CSV
        csv_content = response.text
        assert len(csv_content) > 0, "CSV content is empty"
        
        # Vérifier la structure CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        assert len(rows) > 0, "CSV has no data rows"
        
        # Vérifier qu'il y a des colonnes
        first_row = rows[0]
        assert len(first_row.keys()) > 0, "CSV has no columns"
        
        # Vérifier que _original_id est présent (ajouté par basic-io)
        assert '_original_id' in first_row, "Missing _original_id field in CSV"
        
        # Vérifier des champs typiques d'un user
        assert 'email' in first_row or 'id' in first_row, \
            "Missing expected user fields in CSV"
        
        logger.info(f"✅ CSV export successful: {len(rows)} rows, {len(first_row.keys())} columns")
        logger.info(f"Columns: {', '.join(first_row.keys())}")

    def test02_export_csv_with_special_chars(self, api_tester, auth_token):
        """Tester l'export CSV avec caractères spéciaux"""
        assert auth_token, "Authentication failed"
        
        # Export depuis roles (peut contenir des descriptions avec caractères spéciaux)
        target_url = "http://guardian_service:5000/roles"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "csv"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export CSV with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'text/csv' in content_type, \
            f"Expected CSV content type, got {content_type}"
        
        # Parser le CSV
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        assert len(rows) > 0, "CSV has no data rows"
        
        # Vérifier que le parsing CSV fonctionne correctement
        # (pas d'exception levée signifie que les caractères spéciaux sont bien échappés)
        first_row = rows[0]
        
        # Vérifier que les champs sont présents
        assert '_original_id' in first_row, "Missing _original_id field"
        assert 'name' in first_row or 'id' in first_row, \
            "Missing expected role fields"
        
        # Si un champ contient des virgules ou guillemets, vérifier qu'ils sont bien échappés
        for row in rows:
            for key, value in row.items():
                # Les valeurs ne doivent pas casser la structure CSV
                # csv.DictReader les aura déjà décodées correctement
                assert value is not None, f"Field {key} has None value"
        
        logger.info(f"✅ CSV export with special chars successful: {len(rows)} rows")
        logger.info(f"Sample row: {rows[0]}")

    def test03_export_csv_large_dataset(self, api_tester, auth_token):
        """Tester l'export CSV d'un grand dataset (100+ users)"""
        assert auth_token, "Authentication failed"
        
        # Récupérer company_id depuis le token
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=auth_token
        )
        assert verify_response.status_code == 200, "Failed to verify token"
        company_id = verify_response.json()['company_id']
        
        created_user_ids = []
        
        try:
            # Créer 100 users pour avoir un dataset significatif
            logger.info("Creating 100 test users for large dataset export...")
            for i in range(100):
                user_data = {
                    "email": f"test_large_export_{i}@example.com",
                    "password": "TestPassword123!",
                    "first_name": f"TestUser{i}",
                    "last_name": "LargeExport",
                    "company_id": company_id
                }
                
                response = api_tester.session.post(
                    f"{api_tester.base_url}/api/identity/users",
                    json=user_data,
                    cookies=auth_token
                )
                
                if response.status_code == 201:
                    user_id = response.json()['id']
                    created_user_ids.append(user_id)
                    if (i + 1) % 20 == 0:
                        logger.info(f"  Created {i + 1}/100 users...")
                else:
                    logger.warning(f"Failed to create user {i}: {response.status_code}")
            
            logger.info(f"✅ Created {len(created_user_ids)} test users")
            
            # Export depuis users
            target_url = "http://identity_service:5000/users"
            
            url = f"{api_tester.base_url}/api/basic-io/export"
            params = {
                "url": target_url,
                "type": "csv"
            }
            
            api_tester.log_request('GET', url, params)
            
            # Mesurer le temps d'export
            start_time = time.time()
            response = api_tester.session.get(url, params=params, cookies=auth_token)
            duration = time.time() - start_time
            
            api_tester.log_response(response)
            
            assert response.status_code == 200, \
                f"Failed to export CSV with status {response.status_code}: {response.text}"
            
            # Vérifier le Content-Type
            content_type = response.headers.get('Content-Type', '')
            assert 'text/csv' in content_type, \
                f"Expected CSV content type, got {content_type}"
            
            # Parser le CSV
            csv_content = response.text
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)
            
            # Vérifier qu'on a au moins 100 lignes (nos users créés)
            assert len(rows) >= 100, \
                f"Expected at least 100 rows, got {len(rows)}"
            
            # Vérifier la taille du contenu
            content_size = len(csv_content)
            
            # Vérifier que toutes les lignes sont bien formées
            for i, row in enumerate(rows[:10]):  # Vérifier juste les 10 premières
                assert '_original_id' in row, f"Row {i} missing _original_id"
                # Vérifier qu'il y a des données dans la ligne
                non_empty_fields = [v for v in row.values() if v and v.strip()]
                assert len(non_empty_fields) > 0, f"Row {i} has no data"
            
            # Log des statistiques
            logger.info("✅ Large CSV export successful:")
            logger.info(f"  - Rows: {len(rows)}")
            logger.info(f"  - Columns: {len(rows[0].keys())}")
            logger.info(f"  - Size: {content_size} bytes ({content_size / 1024:.2f} KB)")
            logger.info(f"  - Duration: {duration:.2f}s")
            logger.info(f"  - Throughput: {len(rows) / duration:.1f} rows/s")
            
            # Vérifier que le temps d'export est raisonnable
            # (pas de timeout, pas de performance dégradée)
            assert duration < 30, \
                f"Export took too long: {duration:.2f}s (expected < 30s)"
        
        finally:
            # Cleanup: Supprimer tous les users créés
            logger.info(f"🧹 Cleaning up {len(created_user_ids)} test users...")
            deleted_count = 0
            for user_id in created_user_ids:
                try:
                    delete_response = api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/users/{user_id}",
                        cookies=auth_token
                    )
                    if delete_response.status_code == 204:
                        deleted_count += 1
                    else:
                        logger.warning(f"Failed to delete user {user_id}: {delete_response.status_code}")
                except Exception as e:
                    logger.error(f"Error deleting user {user_id}: {e}")
            
            logger.info(f"✅ Cleanup completed: {deleted_count}/{len(created_user_ids)} users deleted")

    def test04_export_csv_empty_result(self, api_tester, auth_token):
        """Tester l'export CSV quand l'endpoint retourne un tableau vide"""
        assert auth_token, "Authentication failed"
        
        # Utiliser un endpoint qui pourrait retourner un résultat vide
        # Note: Ceci peut varier selon l'état de la base de données
        # On teste la gestion d'un résultat vide, pas la recherche d'un endpoint vide
        target_url = "http://identity_service:5000/users?email=nonexistent@test.invalid"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "csv"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=auth_token)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export CSV with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'text/csv' in content_type, \
            f"Expected CSV content type, got {content_type}"
        
        # Parser le CSV
        csv_content = response.text
        
        # Un CSV vide peut avoir juste l'en-tête ou être complètement vide
        # Vérifier qu'on ne crash pas
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Le résultat peut être vide (0 lignes) ou avoir quelques lignes
        # L'important est qu'il n'y a pas d'erreur
        logger.info(f"✅ Empty CSV export handled: {len(rows)} rows")
        
        if len(rows) > 0:
            # Si des lignes sont présentes, vérifier la structure
            assert '_original_id' in rows[0], "Missing _original_id in CSV header"

    def test05_export_csv_without_auth(self, api_tester):
        """Tester l'export CSV sans authentification (doit échouer)"""
        
        target_url = "http://identity_service:5000/users"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "csv"
        }
        
        api_tester.log_request('GET', url, params)
        # Créer une nouvelle session sans cookies
        temp_session = requests.Session()
        response = temp_session.get(url, params=params)
        api_tester.log_response(response)
        
        # Devrait retourner 401 (unauthorized)
        assert response.status_code == 401, \
            f"Expected 401 for missing auth, got {response.status_code}"
        
        logger.info("✅ Missing authentication correctly rejected with 401")
