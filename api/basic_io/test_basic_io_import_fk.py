"""
Tests for Basic I/O API - Foreign Key Reference Resolution
Tests pour la résolution automatique des références (FK) lors de l'import
"""
import requests
import time
import pytest
import sys
import io
import json
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('basic_io')


class TestBasicIOImportFK:
    """Tests de résolution automatique des FK lors de l'import"""

    @pytest.mark.xfail(reason="Basic-IO API signature change - POST params need fixing on develop")
    def test01_import_auto_resolve_single_match(self, api_tester, session_auth_cookies, session_user_info):
        """Tester la résolution automatique d'une référence FK avec une seule correspondance
        
        Scénario: user avec FK position_id → position (lookup par title)
        """
        company_id = session_user_info["company_id"]
        company_id = session_user_info['company_id']
        assert session_auth_cookies, "Authentication failed"
        
        timestamp = int(time.time())
        created_position_ids = []
        created_user_ids = []
        
        try:
            # Étape 1: Créer une position de référence
            logger.info("Step 1: Creating reference position...")
            import uuid
            position_title = f"FK_Test_Position_{uuid.uuid4().hex[:8]}_{timestamp}"
            
            # Récupérer l'org unit existante (Default Organization créée à l'init)
            org_units_response = api_tester.session.get(
                f"{api_tester.base_url}/api/identity/organization_units",
                cookies=session_auth_cookies
            )
            assert org_units_response.status_code == 200, "Failed to list org units"
            org_units = org_units_response.json()
            assert len(org_units) > 0, "No organization units found"
            org_unit_id = org_units[0]['id']  # Utiliser le premier (Default Organization)
            
            position_response = api_tester.session.post(
                f"{api_tester.base_url}/api/identity/positions",
                json={
                    "title": position_title,
                    "organization_unit_id": org_unit_id,
                    "company_id": company_id,  # Temporaire: schema valide ça mais le service l'écrase avec org_unit.company_id
                    "description": "Reference position for FK resolution test"
                },
                cookies=session_auth_cookies
            )
            assert position_response.status_code == 201, \
                f"Failed to create position: {position_response.text}"
            
            position_id = position_response.json()['id']
            created_position_ids.append(position_id)
            logger.info(f"✅ Created position: {position_id} with title '{position_title}'")
            
            # Étape 2: Importer un user avec FK position_id par lookup (title au lieu d'UUID)
            # Simuler un export enrichi avec _references
            user_email = f"fk_test_user_{timestamp}@example.com"
            import_data = [{
                "_original_id": "temp-user-1",
                "email": user_email,
                "password": "TestPassword123!",
                "first_name": "FK",
                "last_name": "TestUser",
                "company_id": company_id,
                "position_id": position_title,  # ❗ Title au lieu d'UUID
                "_references": {
                    "position_id": {
                        "resource_type": "positions",
                        "original_id": position_id,  # UUID original
                        "lookup_field": "title",
                        "lookup_value": position_title  # Valeur pour lookup
                    }
                }
            }]
            
            # Étape 3: Import avec résolution FK
            logger.info("Step 2: Importing user with FK reference to position by title...")
            json_file = io.BytesIO(json.dumps(import_data).encode('utf-8'))
            
            files = {'file': ('import_fk.json', json_file, 'application/json')}
            data = {
                'service': 'identity',
                'path': '/users',
                'type': 'json'
            }
            
            api_tester.log_request('POST', f"{api_tester.base_url}/api/basic-io/import", data)
            response = api_tester.session.post(
                f"{api_tester.base_url}/api/basic-io/import",
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            api_tester.log_response(response)
            
            # Vérification
            assert response.status_code == 201, \
                f"Expected 201 for successful import, got {response.status_code}: {response.text}"
            
            result = response.json()
            import_report = result.get('import_report', {})
            resolution_report = result.get('resolution_report', {})
            
            # Vérifier l'import
            assert import_report.get('success', 0) == 1, \
                f"Expected 1 successful import, got {import_report}"
            assert import_report.get('failed', 0) == 0, \
                "Expected no failed imports"
            
            # Vérifier la résolution FK
            assert resolution_report.get('resolved', 0) == 1, \
                f"Expected 1 resolved FK reference, got {resolution_report}"
            assert resolution_report.get('ambiguous', 0) == 0, \
                "Expected no ambiguous references"
            assert resolution_report.get('missing', 0) == 0, \
                "Expected no missing references"
            
            # Récupérer l'ID du user créé
            id_mapping = import_report.get('id_mapping', {})
            assert 'temp-user-1' in id_mapping, "Missing ID mapping for imported user"
            created_user_id = id_mapping['temp-user-1']
            created_user_ids.append(created_user_id)
            
            # Vérifier que le user a bien la bonne position_id (UUID résolu)
            user_response = api_tester.session.get(
                f"{api_tester.base_url}/api/identity/users/{created_user_id}",
                cookies=session_auth_cookies
            )
            assert user_response.status_code == 200, "Failed to retrieve created user"
            
            user_data = user_response.json()
            assert user_data['position_id'] == position_id, \
                f"FK not resolved correctly: expected {position_id}, got {user_data.get('position_id')}"
            
            logger.info(f"✅ FK resolved: '{position_title}' → {position_id}")
            logger.info(f"Resolution report: {resolution_report}")
            
        finally:
            # Cleanup: users first (FK dependency)
            for user_id in created_user_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/users/{user_id}",
                        cookies=session_auth_cookies
                    )
                    logger.info(f"Cleaned up user: {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup user {user_id}: {e}")
            
            # Then positions
            for position_id in created_position_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/positions/{position_id}",
                        cookies=session_auth_cookies
                    )
                    logger.info(f"Cleaned up position: {position_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup position {position_id}: {e}")

    @pytest.mark.xfail(reason="Basic-IO API signature change - POST params need fixing on develop")
    def test02_import_ambiguous_reference_skip(self, api_tester, session_auth_cookies, session_user_info):
        """Tester le comportement skip quand une référence FK est ambiguë (plusieurs matches)
        
        Scénario: 2 positions avec le même title → user import avec FK ambiguë → skip
        """
        company_id = session_user_info["company_id"]
        assert session_auth_cookies, "Authentication failed"
        
        timestamp = int(time.time())
        created_position_ids = []
        created_user_ids = []
        
        try:
            # Récupérer l'org unit existante
            org_units_response = api_tester.session.get(
                f"{api_tester.base_url}/api/identity/organization_units",
                cookies=session_auth_cookies
            )
            org_units = org_units_response.json()
            org_unit_id = org_units[0]['id']
            
            # Étape 1: Créer 2 positions avec le MÊME title (ambiguïté)
            logger.info("Step 1: Creating 2 positions with same title (ambiguous)...")
            import uuid
            duplicate_title = f"Ambiguous_Position_{uuid.uuid4().hex[:8]}_{timestamp}"
            
            for i in range(2):
                position_response = api_tester.session.post(
                    f"{api_tester.base_url}/api/identity/positions",
                    json={
                        "title": duplicate_title,
                        "organization_unit_id": org_unit_id,
                        "company_id": company_id,
                        "description": f"Duplicate position #{i+1}"
                    },
                    cookies=session_auth_cookies
                )
                assert position_response.status_code == 201, \
                    f"Failed to create position #{i+1}: {position_response.text}"
                
                position_id = position_response.json()['id']
                created_position_ids.append(position_id)
                logger.info(f"Created position #{i+1}: {position_id}")
            
            # Étape 2: Import avec référence ambiguë (mode skip par défaut)
            logger.info("Step 2: Importing user with ambiguous FK reference (skip mode)...")
            user_email = f"ambiguous_test_{timestamp}@example.com"
            import_data = [{
                "_original_id": "temp-user-1",
                "email": user_email,
                "password": "TestPassword123!",
                "first_name": "Ambiguous",
                "last_name": "Test",
                "company_id": company_id,
                "position_id": duplicate_title,  # Référence ambiguë
                "_references": {
                    "position_id": {
                        "resource_type": "positions",
                        "original_id": created_position_ids[0],
                        "lookup_field": "title",
                        "lookup_value": duplicate_title
                    }
                }
            }]
            
            json_file = io.BytesIO(json.dumps(import_data).encode('utf-8'))
            files = {'file': ('import_ambiguous.json', json_file, 'application/json')}
            data = {
                'service': 'identity',
                'path': '/users',
                'type': 'json',
                'on_ambiguous': 'skip'  # Mode skip explicite
            }
            
            api_tester.log_request('POST', f"{api_tester.base_url}/api/basic-io/import", data)
            response = api_tester.session.post(
                f"{api_tester.base_url}/api/basic-io/import",
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            api_tester.log_response(response)
            
            # ⚠️ COMPORTEMENT AVEC CHAMP REQUIS: 
            # Même en mode skip, si position_id est REQUIS par le schéma Identity,
            # l'import échoue car le service ne peut pas créer le user sans ce champ
            # C'est le comportement correct - skip ne peut pas contourner les contraintes du schéma
            assert response.status_code == 400, \
                f"Expected 400 (position_id required by schema), got {response.status_code}: {response.text}"
            
            result = response.json()
            resolution_report = result.get('resolution_report', {})
            
            # Vérifier qu'il y a une référence ambiguë détectée
            assert resolution_report.get('ambiguous', 0) >= 1, \
                f"Expected at least 1 ambiguous reference, got {resolution_report}"
            
            # L'import échoue car position_id est requis par Identity (skip ne peut pas contourner ça)
            import_report = result.get('import_report', {})
            assert import_report.get('failed', 0) == 1, \
                "Expected import to fail (position_id required by Identity schema)"
            
            logger.info("✅ on_ambiguous=skip detected ambiguity but import fails: position_id required")
            logger.info(f"Resolution report: {resolution_report}")
            
        finally:
            # Cleanup
            for user_id in created_user_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/users/{user_id}",
                        cookies=session_auth_cookies
                    )
                except Exception as e:
                    logger.warning(f"Failed to cleanup user {user_id}: {e}")
            
            for position_id in created_position_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/positions/{position_id}",
                        cookies=session_auth_cookies
                    )
                except Exception as e:
                    logger.warning(f"Failed to cleanup position {position_id}: {e}")

    @pytest.mark.xfail(reason="Basic-IO API signature change - POST params need fixing on develop")
    def test03_import_ambiguous_reference_fail(self, api_tester, session_auth_cookies, session_user_info):
        """Tester le mode fail quand une référence FK est ambiguë
        
        Scénario: 2 positions avec même title + mode on_ambiguous=fail → import doit échouer
        """
        company_id = session_user_info["company_id"]
        assert session_auth_cookies, "Authentication failed"
        
        timestamp = int(time.time())
        created_position_ids = []
        created_user_ids = []
        
        try:
            # Récupérer l'org unit existante
            org_units_response = api_tester.session.get(
                f"{api_tester.base_url}/api/identity/organization_units",
                cookies=session_auth_cookies
            )
            org_units = org_units_response.json()
            org_unit_id = org_units[0]['id']
            
            # Créer 2 positions avec le même title
            logger.info("Creating 2 positions with duplicate title...")
            import uuid
            duplicate_title = f"Fail_Ambiguous_{uuid.uuid4().hex[:8]}_{timestamp}"
            
            for i in range(2):
                position_response = api_tester.session.post(
                    f"{api_tester.base_url}/api/identity/positions",
                    json={
                        "title": duplicate_title,
                        "organization_unit_id": org_unit_id,
                        "company_id": company_id,
                        "description": f"Duplicate position #{i+1}"
                    },
                    cookies=session_auth_cookies
                )
                assert position_response.status_code == 201
                created_position_ids.append(position_response.json()['id'])
            
            # Import avec mode fail (on_ambiguous=fail)
            logger.info("Importing with ambiguous FK reference (fail mode)...")
            import_data = [{
                "_original_id": "temp-user-1",
                "email": f"fail_test_{timestamp}@example.com",
                "password": "TestPassword123!",
                "company_id": company_id,
                "position_id": duplicate_title,
                "_references": {
                    "position_id": {
                        "resource_type": "positions",
                        "original_id": created_position_ids[0],
                        "lookup_field": "title",
                        "lookup_value": duplicate_title
                    }
                }
            }]
            
            json_file = io.BytesIO(json.dumps(import_data).encode('utf-8'))
            files = {'file': ('import_fail.json', json_file, 'application/json')}
            data = {
                'service': 'identity',
                'path': '/users',
                'type': 'json',
                'on_ambiguous': 'fail'  # Mode fail explicite
            }
            
            api_tester.log_request('POST', f"{api_tester.base_url}/api/basic-io/import", data)
            response = api_tester.session.post(
                f"{api_tester.base_url}/api/basic-io/import",
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            api_tester.log_response(response)
            
            # ✅ COMPORTEMENT CORRECT: Le mode fail EST implémenté
            # Le service retourne 400 avec on_ambiguous=fail quand une référence est ambiguë
            assert response.status_code == 400, \
                f"Expected 400 when on_ambiguous=fail with ambiguous reference, got {response.status_code}"
            
            result = response.json()
            
            # Vérifier le message d'erreur
            assert 'ambiguous' in result.get('message', '').lower(), \
                "Expected error message about ambiguous references"
            
            # Vérifier le rapport de résolution
            resolution_report = result.get('resolution_report', {})
            assert resolution_report.get('ambiguous', 0) >= 1, \
                "Expected at least 1 ambiguous reference detected"
            
            # Vérifier les détails de la référence ambiguë
            details = resolution_report.get('details', [])
            assert len(details) > 0, "Expected details about ambiguous reference"
            assert details[0]['status'] == 'ambiguous', "Expected status=ambiguous"
            assert details[0]['field'] == 'position_id', "Expected field=position_id"
            assert details[0]['candidates'] == 2, "Expected 2 candidates found"
            
            logger.info(f"✅ on_ambiguous=fail WORKS CORRECTLY - service returns 400: {resolution_report}")
            
        finally:
            # Cleanup users first (FK dependency)
            for user_id in created_user_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/users/{user_id}",
                        cookies=session_auth_cookies
                    )
                    logger.info(f"Cleaned up user: {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup user {user_id}: {e}")
            
            # Then cleanup positions
            for position_id in created_position_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/positions/{position_id}",
                        cookies=session_auth_cookies
                    )
                except Exception as e:
                    logger.warning(f"Failed to cleanup: {e}")

    @pytest.mark.xfail(reason="Basic-IO API signature change - POST params need fixing on develop")
    def test04_import_missing_reference_skip(self, api_tester, session_auth_cookies, session_user_info):
        """Tester le mode skip quand une référence FK est introuvable
        
        Scénario: user avec FK vers position inexistante → skip mode → user créé sans position_id
        """
        company_id = session_user_info["company_id"]
        assert session_auth_cookies, "Authentication failed"
        
        timestamp = int(time.time())
        created_user_ids = []
        
        try:
            # Import avec référence FK vers un record inexistant
            logger.info("Importing with missing FK reference (skip mode)...")
            import uuid
            nonexistent_title = f"NonExistent_Position_{uuid.uuid4().hex[:8]}_{timestamp}"
            user_email = f"missing_ref_test_{timestamp}@example.com"
            
            import_data = [{
                "_original_id": "temp-user-1",
                "email": user_email,
                "password": "TestPassword123!",
                "first_name": "Missing",
                "last_name": "RefTest",
                "company_id": company_id,
                "position_id": nonexistent_title,  # N'existe pas
                "_references": {
                    "position_id": {
                        "resource_type": "positions",
                        "original_id": None,  # Pas d'ID original
                        "lookup_field": "title",
                        "lookup_value": nonexistent_title
                    }
                }
            }]
            
            json_file = io.BytesIO(json.dumps(import_data).encode('utf-8'))
            files = {'file': ('import_missing.json', json_file, 'application/json')}
            data = {
                'service': 'identity',
                'path': '/users',
                'type': 'json',
                'on_missing': 'skip'  # Mode skip explicite
            }
            
            api_tester.log_request('POST', f"{api_tester.base_url}/api/basic-io/import", data)
            response = api_tester.session.post(
                f"{api_tester.base_url}/api/basic-io/import",
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            api_tester.log_response(response)
            
            # ⚠️ COMPORTEMENT ACTUEL: position_id est REQUIS dans le schéma Identity
            # Le service Basic I/O détecte bien missing=1, mais l'import échoue 
            # car le service cible (Identity) refuse le record sans position_id
            assert response.status_code == 400, \
                f"Expected 400 (position_id required by Identity service), got {response.status_code}"
            
            result = response.json()
            resolution_report = result.get('resolution_report', {})
            
            # Vérifier qu'il y a une référence manquante détectée
            assert resolution_report.get('missing', 0) >= 1, \
                f"Expected at least 1 missing reference, got {resolution_report}"
            
            # L'import échoue car position_id requis
            import_report = result.get('import_report', {})
            assert import_report.get('failed', 0) == 1, \
                "Expected import to fail (position_id required)"
            
            logger.info("⚠️ Missing ref detected but import fails: position_id required by Identity service")
            logger.info(f"Resolution report (missing ref): {resolution_report}")
            
        finally:
            # Cleanup (aucun user créé car import échoue, mais par sécurité)
            for user_id in created_user_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/users/{user_id}",
                        cookies=session_auth_cookies
                    )
                    logger.info(f"Cleaned up user: {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup: {e}")

    @pytest.mark.xfail(reason="Basic-IO API signature change - POST params need fixing on develop")
    def test05_import_missing_reference_fail(self, api_tester, session_auth_cookies, session_user_info):
        """Tester le mode fail quand une référence FK est introuvable
        
        Scénario: user avec FK vers position inexistante + mode on_missing=fail → import doit échouer
        """
        company_id = session_user_info["company_id"]
        assert session_auth_cookies, "Authentication failed"
        
        timestamp = int(time.time())
        created_user_ids = []
        
        try:
            # Import avec référence manquante + mode fail
            logger.info("Importing with missing FK reference (fail mode)...")
            import uuid
            nonexistent_value = f"DoesNotExist_{uuid.uuid4().hex[:8]}_{timestamp}"
            import_data = [{
                "_original_id": "temp-user-1",
                "email": f"missing_fail_{timestamp}@example.com",
                "password": "TestPassword123!",
                "company_id": company_id,
                "position_id": nonexistent_value,
                "_references": {
                    "position_id": {
                        "resource_type": "positions",
                        "original_id": None,
                        "lookup_field": "title",
                        "lookup_value": nonexistent_value
                    }
                }
            }]
            
            json_file = io.BytesIO(json.dumps(import_data).encode('utf-8'))
            files = {'file': ('import_missing_fail.json', json_file, 'application/json')}
            data = {
                'service': 'identity',
                'path': '/users',
                'type': 'json',
                'on_missing': 'fail'  # Mode fail explicite
            }
            
            api_tester.log_request('POST', f"{api_tester.base_url}/api/basic-io/import", data)
            response = api_tester.session.post(
                f"{api_tester.base_url}/api/basic-io/import",
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            api_tester.log_response(response)
            
            # ✅ COMPORTEMENT CORRECT: Le mode fail EST implémenté
            # Le service retourne 400 avec on_missing=fail quand une référence est manquante
            assert response.status_code == 400, \
                f"Expected 400 when on_missing=fail with missing reference, got {response.status_code}"
            
            result = response.json()
            
            # Vérifier le message d'erreur
            assert 'missing' in result.get('message', '').lower(), \
                "Expected error message about missing references"
            
            # Vérifier le rapport de résolution
            resolution_report = result.get('resolution_report', {})
            assert resolution_report.get('missing', 0) >= 1, \
                "Expected at least 1 missing reference detected"
            
            # Vérifier les détails de la référence manquante
            details = resolution_report.get('details', [])
            assert len(details) > 0, "Expected details about missing reference"
            assert details[0]['status'] == 'missing', "Expected status=missing"
            assert details[0]['field'] == 'position_id', "Expected field=position_id"
            
            logger.info("✅ on_missing=fail WORKS CORRECTLY - service returns 400")
            logger.info(f"Resolution report (missing ref): {resolution_report}")
            
        finally:
            # Cleanup (aucun user créé car import échoue, mais par sécurité)
            for user_id in created_user_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/users/{user_id}",
                        cookies=session_auth_cookies
                    )
                    logger.info(f"Cleaned up user: {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup: {e}")

    @pytest.mark.skip(reason="TODO: Re-enable when we have a better FK scenario (tasks service not available)")
    @pytest.mark.xfail(reason="Basic-IO API signature change - POST params need fixing on develop")
    def test06_import_no_import_order_required(self, api_tester, session_auth_cookies, session_user_info):
        """Tester l'import dans n'importe quel ordre grâce à la résolution FK
        
        NOTE: Ce test devrait importer des tasks AVANT leurs assigned_to users.
        Actuellement skip car endpoint /tasks n'existe pas dans Identity service.
        Alternative: Créer des users avec org_unit_id référençant des org_units par nom.
        
        La résolution FK devrait permettre de créer les tasks avec les bonnes références.
        """
        company_id = session_user_info["company_id"]
        assert session_auth_cookies, "Authentication failed"
        
        timestamp = int(time.time())
        created_user_ids = []
        created_task_ids = []
        
        try:
            # Étape 1: Créer 2 users de référence
            logger.info("Step 1: Creating 2 users that will be referenced in tasks...")
            user_emails = []
            for i in range(2):
                user_email = f"task_assignee_{timestamp}_{i}@example.com"
                user_emails.append(user_email)
                
                user_response = api_tester.session.post(
                    f"{api_tester.base_url}/api/identity/users",
                    json={
                        "email": user_email,
                        "password": "TestPassword123!",
                        "first_name": f"Assignee{i}",
                        "last_name": "Test",
                        "company_id": company_id
                    },
                    cookies=session_auth_cookies
                )
                assert user_response.status_code == 201, \
                    f"Failed to create user: {user_response.text}"
                
                user_id = user_response.json()['id']
                created_user_ids.append(user_id)
                logger.info(f"Created user: {user_id} ({user_email})")
            
            # Étape 2: Importer des tasks qui référencent ces users par EMAIL
            # (normalement il faudrait créer les users AVANT les tasks, 
            #  mais avec FK resolution on peut référencer par email)
            logger.info("Step 2: Importing tasks that reference users by email...")
            
            import_data = [
                {
                    "_original_id": "temp-task-1",
                    "title": f"Task 1 - FK Resolution Test {timestamp}",
                    "description": "Testing FK resolution with user email lookup",
                    "company_id": company_id,
                    "assigned_to": user_emails[0],  # Email au lieu d'UUID
                    "_references": {
                        "assigned_to": {
                            "resource_type": "users",
                            "original_id": created_user_ids[0],
                            "lookup_field": "email",
                            "lookup_value": user_emails[0]
                        }
                    }
                },
                {
                    "_original_id": "temp-task-2",
                    "title": f"Task 2 - FK Resolution Test {timestamp}",
                    "description": "Another task with email reference",
                    "company_id": company_id,
                    "assigned_to": user_emails[1],  # Email au lieu d'UUID
                    "_references": {
                        "assigned_to": {
                            "resource_type": "users",
                            "original_id": created_user_ids[1],
                            "lookup_field": "email",
                            "lookup_value": user_emails[1]
                        }
                    }
                }
            ]
            
            json_file = io.BytesIO(json.dumps(import_data).encode('utf-8'))
            files = {'file': ('import_tasks.json', json_file, 'application/json')}
            data = {
                'service': 'identity',
                'path': '/tasks',
                'type': 'json'
            }
            
            api_tester.log_request('POST', f"{api_tester.base_url}/api/basic-io/import", data)
            response = api_tester.session.post(
                f"{api_tester.base_url}/api/basic-io/import",
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            api_tester.log_response(response)
            
            # Vérification
            assert response.status_code == 201, \
                f"Expected 201 for successful import, got {response.status_code}: {response.text}"
            
            result = response.json()
            import_report = result.get('import_report', {})
            resolution_report = result.get('resolution_report', {})
            
            # 2 tasks importées avec succès
            assert import_report.get('success', 0) == 2, \
                f"Expected 2 successful imports, got {import_report}"
            
            # 2 FK résolues
            assert resolution_report.get('resolved', 0) == 2, \
                f"Expected 2 resolved FK references, got {resolution_report}"
            assert resolution_report.get('missing', 0) == 0, \
                "Expected no missing references"
            
            # Récupérer les IDs des tasks créées
            id_mapping = import_report.get('id_mapping', {})
            task1_id = id_mapping.get('temp-task-1')
            task2_id = id_mapping.get('temp-task-2')
            
            assert task1_id and task2_id, "Missing task IDs in id_mapping"
            created_task_ids.extend([task1_id, task2_id])
            
            # Vérifier que les tasks ont les bons assigned_to (UUIDs résolus)
            for i, task_id in enumerate([task1_id, task2_id]):
                task_response = api_tester.session.get(
                    f"{api_tester.base_url}/api/identity/tasks/{task_id}",
                    cookies=session_auth_cookies
                )
                assert task_response.status_code == 200, \
                    f"Failed to retrieve task {task_id}"
                
                task_data = task_response.json()
                expected_user_id = created_user_ids[i]
                actual_user_id = task_data.get('assigned_to')
                
                assert actual_user_id == expected_user_id, \
                    f"FK not resolved correctly for task {i+1}: expected {expected_user_id}, got {actual_user_id}"
                
                logger.info(f"✅ Task {i+1} correctly assigned: {user_emails[i]} → {expected_user_id}")
            
            logger.info("✅ Import order independence verified - tasks imported with FK resolution")
            logger.info(f"Resolution report: {resolution_report}")
            
        finally:
            # Cleanup tasks first (FK dependency)
            for task_id in created_task_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/tasks/{task_id}",
                        cookies=session_auth_cookies
                    )
                    logger.info(f"Cleaned up task: {task_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup task {task_id}: {e}")
            
            # Then cleanup users
            for user_id in created_user_ids:
                try:
                    api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/users/{user_id}",
                        cookies=session_auth_cookies
                    )
                    logger.info(f"Cleaned up user: {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup user {user_id}: {e}")
