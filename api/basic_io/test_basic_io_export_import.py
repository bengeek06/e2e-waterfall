"""
Tests for Basic I/O API - Export/Import Integration
Test complet du cycle export → import avec résolution FK
"""
import requests
import time
import pytest
import sys
import io
import json
from pathlib import Path

# Désactiver les warnings SSL pour les tests

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('basic_io')

class TestBasicIOExportImport:
    """Tests d'intégration Export → Import avec résolution FK"""
    



    @pytest.mark.xfail(reason="Basic-IO API signature change - POST params need fixing on develop")
    def test01_export_import_cycle_with_fk_resolution(self, api_tester, session_auth_cookies, session_user_info):
        """
        Test complet: Export → Delete → Import avec résolution FK
        
        Scénario:
        1. Créer 3 positions (Software Engineer, Product Manager, Data Scientist)
        2. Créer 9 users (3 par position)
        3. Exporter les users
        4. Supprimer les users créés
        5. Importer le fichier d'export
        6. Vérifier que chaque user a retrouvé sa position d'origine
        """
        company_id = session_user_info["company_id"]
        assert session_auth_cookies, "Authentication failed"
        
        timestamp = int(time.time())
        created_positions = []
        created_users = []
        export_file_path = None
        
        try:
            # ====== STEP 1: Créer 3 positions ======
            logger.info("Step 1: Creating 3 positions...")
            
            org_units_response = api_tester.session.get(
                f"{api_tester.base_url}/api/identity/organization_units",
                cookies=session_auth_cookies
            )
            assert org_units_response.status_code == 200
            org_units = org_units_response.json()
            assert len(org_units) > 0, "No organization units found"
            org_unit_id = org_units[0]['id']
            
            position_titles = [
                f"Software_Engineer_{timestamp}",
                f"Product_Manager_{timestamp}",
                f"Data_Scientist_{timestamp}"
            ]
            
            for title in position_titles:
                response = api_tester.session.post(
                    f"{api_tester.base_url}/api/identity/positions",
                    json={
                        "title": title,
                        "organization_unit_id": org_unit_id,
                        "company_id": company_id,
                        "description": f"Test position for export/import cycle"
                    },
                    cookies=session_auth_cookies
                )
                assert response.status_code == 201, f"Failed to create position: {response.text}"
                
                position = response.json()
                created_positions.append(position)
                logger.info(f"Created position: {title} → {position['id']}")
            
            assert len(created_positions) == 3, "Expected 3 positions created"
            
            # ====== STEP 2: Créer 9 users (3 par position) ======
            logger.info("Step 2: Creating 9 users (3 per position)...")
            
            for i, position in enumerate(created_positions):
                for j in range(3):
                    user_num = i * 3 + j + 1
                    email = f"export_import_test_{user_num}_{timestamp}@example.com"
                    
                    response = api_tester.session.post(
                        f"{api_tester.base_url}/api/identity/users",
                        json={
                            "email": email,
                            "password": "TestPassword123!",
                            "first_name": f"User{user_num}",
                            "last_name": "Test",
                            "company_id": company_id,
                            "position_id": position['id']
                        },
                        cookies=session_auth_cookies
                    )
                    assert response.status_code == 201, f"Failed to create user: {response.text}"
                    
                    user = response.json()
                    created_users.append({
                        'id': user['id'],
                        'email': email,
                        'expected_position_id': position['id'],
                        'expected_position_title': position['title']
                    })
                    logger.info(f"Created user {user_num}: {email}")
            
            assert len(created_users) == 9, "Expected 9 users created"
            
            # ====== STEP 3: Exporter les users ======
            logger.info("Step 3: Exporting users...")
            
            export_response = api_tester.session.get(
                f"{api_tester.base_url}/api/basic-io/export",
                params={
                    "service": "identity",
                    "path": "/users",
                    "format": "json"
                },
                cookies=session_auth_cookies
            )
            assert export_response.status_code == 200, f"Export failed: {export_response.text}"
            
            export_data = export_response.json()
            logger.info(f"Exported {len(export_data)} users")
            
            # Vérifier que nos users sont dans l'export avec _references correctes
            exported_test_users = [
                u for u in export_data
                if u.get('email', '').startswith(f"export_import_test_") and str(timestamp) in u.get('email', '')
            ]
            assert len(exported_test_users) == 9, \
                f"Expected 9 test users in export, got {len(exported_test_users)}"
            
            # Vérifier les _references
            for user in exported_test_users:
                refs = user.get('_references', {})
                assert 'position_id' in refs, f"Missing position_id in _references for {user.get('email')}"
                
                pos_ref = refs['position_id']
                assert pos_ref.get('resource_type') == 'positions', "Wrong resource_type"
                assert pos_ref.get('lookup_field') == 'title', \
                    f"Wrong lookup_field: {pos_ref.get('lookup_field')} (expected 'title')"
                assert pos_ref.get('lookup_value') is not None, "lookup_value is null"
                
                logger.info(f"✅ {user.get('email')}: _references correct (title={pos_ref.get('lookup_value')})")
            
            # Sauvegarder l'export pour l'import
            log_dir = Path(__file__).parent.parent.parent / 'logs'
            log_dir.mkdir(exist_ok=True)
            export_file_path = log_dir / f"test_export_import_{timestamp}.json"
            
            with open(export_file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Saved export to: {export_file_path}")
            
            # ====== STEP 4: Supprimer les users créés ======
            logger.info("Step 4: Deleting created users...")
            
            deleted_count = 0
            for user in created_users:
                response = api_tester.session.delete(
                    f"{api_tester.base_url}/api/identity/users/{user['id']}",
                    cookies=session_auth_cookies
                )
                if response.status_code in [204, 200]:
                    deleted_count += 1
            
            assert deleted_count == 9, f"Expected to delete 9 users, deleted {deleted_count}"
            logger.info(f"Deleted {deleted_count} users")
            
            # Attendre un peu pour être sûr
            time.sleep(1)
            
            # ====== STEP 5: Importer le fichier d'export ======
            logger.info("Step 5: Importing users from export file...")
            
            # Ajouter password aux données (pas dans l'export pour sécurité)
            with open(export_file_path, 'r') as f:
                import_data = json.load(f)
            
            for user in import_data:
                if 'password' not in user:
                    user['password'] = 'TestPassword123!'
            
            # Créer fichier temporaire pour l'import
            import_file = export_file_path.parent / f"import_{export_file_path.name}"
            with open(import_file, 'w') as f:
                json.dump(import_data, f, indent=2)
            
            # Import
            with open(import_file, 'rb') as f:
                files = {'file': (import_file.name, f, 'application/json')}
                data = {
                    'service': 'identity',
                    'path': '/users',
                    'type': 'json'
                }
                
                import_response = api_tester.session.post(
                    f"{api_tester.base_url}/api/basic-io/import",
                    files=files,
                    data=data,
                    cookies=session_auth_cookies
                )
            
            assert import_response.status_code in [200, 201, 207], \
                f"Import failed: {import_response.status_code} - {import_response.text[:500]}"
            
            result = import_response.json()
            import_report = result.get('import_report', {})
            resolution_report = result.get('resolution_report', {})
            
            logger.info(f"Import report: total={import_report.get('total')}, "
                       f"success={import_report.get('success')}, "
                       f"failed={import_report.get('failed')}")
            logger.info(f"Resolution report: resolved={resolution_report.get('resolved')}, "
                       f"ambiguous={resolution_report.get('ambiguous')}, "
                       f"missing={resolution_report.get('missing')}")
            
            # Vérifier qu'au moins nos 9 users ont été importés avec succès
            assert import_report.get('success', 0) >= 9, \
                f"Expected at least 9 successful imports, got {import_report.get('success')}"
            
            # Vérifier la résolution FK
            assert resolution_report.get('ambiguous', 0) == 0, \
                "Unexpected ambiguous FK references"
            
            id_mapping = import_report.get('id_mapping', {})
            assert len(id_mapping) >= 9, \
                f"Expected at least 9 users in id_mapping, got {len(id_mapping)}"
            
            # ====== STEP 6: Vérifier que les users ont les bonnes positions ======
            logger.info("Step 6: Verifying imported users have correct positions...")
            
            correct_count = 0
            wrong_count = 0
            
            # Créer un mapping email → expected position pour recherche rapide
            email_to_expected = {u['email']: u for u in created_users}
            
            for original_id, new_id in id_mapping.items():
                # Récupérer le user importé
                response = api_tester.session.get(
                    f"{api_tester.base_url}/api/identity/users/{new_id}",
                    cookies=session_auth_cookies
                )
                
                if response.status_code != 200:
                    continue
                
                imported_user = response.json()
                email = imported_user.get('email')
                
                # Vérifier seulement nos users de test
                if not email or not email.startswith(f"export_import_test_"):
                    continue
                
                if email not in email_to_expected:
                    continue
                
                expected = email_to_expected[email]
                actual_position = imported_user.get('position_id')
                expected_position = expected['expected_position_id']
                
                if actual_position == expected_position:
                    correct_count += 1
                    logger.info(f"✅ {email}: position_id correct ({expected['expected_position_title']})")
                else:
                    wrong_count += 1
                    logger.error(f"❌ {email}: position_id mismatch - "
                               f"expected {expected_position}, got {actual_position}")
            
            total_verified = correct_count + wrong_count
            assert total_verified == 9, \
                f"Expected to verify 9 users, verified {total_verified}"
            
            assert correct_count == 9, \
                f"Expected all 9 users with correct position_id, got {correct_count} correct, {wrong_count} wrong"
            
            logger.info(f"✅ Export/Import cycle successful: {correct_count}/9 users with correct FK")
            
            # Cleanup des users importés
            for new_id in id_mapping.values():
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/users/{new_id}",
                        cookies=session_auth_cookies
                    )
                except Exception as e:
                    logger.warning(f"Failed to cleanup imported user {new_id}: {e}")
            
            # Cleanup du fichier temporaire
            if import_file.exists():
                import_file.unlink()
            
        finally:
            # Cleanup: supprimer les positions (les users sont déjà supprimés)
            for position in created_positions:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/positions/{position['id']}",
                        cookies=session_auth_cookies
                    )
                    logger.info(f"Cleaned up position: {position['title']}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup position {position['id']}: {e}")
            
            # Cleanup du fichier d'export
            if export_file_path and export_file_path.exists():
                export_file_path.unlink()
                logger.info(f"Cleaned up export file: {export_file_path}")
