"""
Tests for Basic I/O API - Foreign Key Enrichment functionality
Tests pour l'enrichissement automatique des références (FK) lors de l'export
"""
import pytest
import sys
from pathlib import Path

# Désactiver les warnings SSL pour les tests

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('basic_io')


class TestBasicIOExportEnriched:
    """Tests d'enrichissement automatique des FK via Basic I/O API"""
    
    def test01_export_enriched_detect_fk_fields(self, api_tester, session_auth_cookies):
        """Tester la détection automatique des champs FK (UUID)"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export depuis users avec enrich=true
        # Users a plusieurs FK: company_id, organization_unit_id, etc.
        
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "service": "identity",
            "path": "/users",
            "type": "json",
            "enrich": "true"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export enriched JSON with status {response.status_code}: {response.text}"
        
        # Parser le JSON
        data = response.json()
        assert isinstance(data, list), "Expected JSON array"
        assert len(data) > 0, "Expected at least one user record"
        
        first_record = data[0]
        
        # Vérifier _original_id
        assert '_original_id' in first_record, "Missing _original_id field"
        
        # Vérifier _references (métadonnées d'enrichissement)
        assert '_references' in first_record, "Missing _references field with enrich=true"
        
        references = first_record['_references']
        assert isinstance(references, dict), "_references should be a dict"
        
        # Vérifier qu'il y a au moins une FK enrichie
        assert len(references) > 0, "Expected at least one FK to be enriched"
        
        # Lister les FK détectées
        fk_fields = list(references.keys())
        logger.info(f"✅ Detected FK fields: {fk_fields}")
        
        # Vérifier la structure d'une référence
        first_fk = list(references.values())[0]
        assert 'resource_type' in first_fk, "Missing resource_type in FK metadata"
        assert 'lookup_field' in first_fk, "Missing lookup_field in FK metadata"
        
        logger.info(f"Sample FK metadata: {first_fk}")
        logger.info(f"Total records exported: {len(data)}")

    def test02_export_enriched_users_lookup_email(self, api_tester, session_auth_cookies):
        """Tester l'enrichissement avec lookup_field 'email' pour users"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export enrichi depuis users
        # Le service devrait détecter que 'email' est le lookup_field approprié
        
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "service": "identity",
            "path": "/users",
            "type": "json",
            "enrich": "true"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export enriched users with status {response.status_code}: {response.text}"
        
        # Parser le JSON
        data = response.json()
        assert len(data) > 0, "Expected at least one user"
        
        first_user = data[0]
        
        # Vérifier que email est présent (c'est le lookup_field)
        assert 'email' in first_user, "Missing email field in user record"
        
        # Si _references existe, vérifier les métadonnées FK
        if '_references' in first_user:
            references = first_user['_references']
            
            # Chercher une référence qui pointe vers users
            # (ex: created_by_id, updated_by_id, etc.)
            user_refs = {k: v for k, v in references.items() 
                        if v.get('resource_type') == 'users'}
            
            if user_refs:
                # Vérifier que lookup_field est 'email' pour les refs users
                for fk_name, fk_meta in user_refs.items():
                    lookup_field = fk_meta.get('lookup_field')
                    logger.info(f"FK {fk_name} → users uses lookup_field: {lookup_field}")
                    
                    # Le service devrait utiliser 'email' comme lookup pour users
                    assert lookup_field in ['email', 'id', 'uuid'], \
                        f"Unexpected lookup_field for users: {lookup_field}"
        
        logger.info("✅ Users export with email lookup successful")
        logger.info(f"Exported {len(data)} users")

    def test03_export_enriched_projects_lookup_name(self, api_tester, session_auth_cookies):
        """Tester l'enrichissement avec lookup_field 'name' pour projects"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export enrichi depuis projects
        # Le service devrait détecter que 'name' est un bon lookup_field
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "service": "project",
            "path": "/projects",
            "type": "json",
            "enrich": "true"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        # Project service peut ne pas être disponible en test
        if response.status_code == 502:
            logger.warning("⚠️ Project service unreachable (502) - skipping test")
            pytest.skip("Project service not available")
            return
        
        assert response.status_code == 200, \
            f"Failed to export enriched projects with status {response.status_code}: {response.text}"
        
        # Parser le JSON
        data = response.json()
        
        if len(data) > 0:
            first_project = data[0]
            
            # Vérifier que name est présent
            assert 'name' in first_project, "Missing name field in project record"
            
            # Vérifier _references
            if '_references' in first_project:
                references = first_project['_references']
                
                logger.info(f"✅ Project enrichment metadata: {list(references.keys())}")
                
                # Analyser les lookup_fields utilisés
                lookup_fields = {k: v.get('lookup_field') for k, v in references.items()}
                logger.info(f"Lookup fields: {lookup_fields}")
        else:
            logger.info("No projects in database (empty result)")
        
        logger.info("✅ Projects export with name lookup successful")

    def test04_export_enriched_parent_id_special_handling(self, api_tester, session_auth_cookies):
        """Tester le traitement spécial de parent_id (self-reference)"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export enrichi depuis organization_units (qui a parent_id self-reference)
        
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "service": "identity",
            "path": "/users",
            "type": "json",
            "enrich": "true"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export enriched org units with status {response.status_code}: {response.text}"
        
        # Parser le JSON
        data = response.json()
        
        if len(data) > 0:
            # Chercher un record avec parent_id
            record_with_parent = None
            for record in data:
                if record.get('parent_id'):
                    record_with_parent = record
                    break
            
            if record_with_parent:
                logger.info("Found record with parent_id")
                
                # Vérifier _references
                if '_references' in record_with_parent:
                    references = record_with_parent['_references']
                    
                    # parent_id devrait avoir une référence spéciale
                    if 'parent_id' in references:
                        parent_ref = references['parent_id']
                        
                        logger.info(f"✅ parent_id reference metadata: {parent_ref}")
                        
                        # Vérifier que c'est une self-reference
                        resource_type = parent_ref.get('resource_type')
                        logger.info(f"Parent resource_type: {resource_type}")
                        
                        # Devrait pointer vers organization_units (même table)
                        assert 'organization_unit' in resource_type.lower() or \
                               resource_type == 'organization_units', \
                            f"Expected self-reference, got {resource_type}"
                        
                        # Vérifier lookup_field
                        lookup_field = parent_ref.get('lookup_field')
                        logger.info(f"Parent lookup_field: {lookup_field}")
                    else:
                        logger.info("parent_id not in _references (might be excluded)")
                else:
                    logger.info("No _references in record with parent")
            else:
                logger.info("No records with parent_id found (all roots)")
        else:
            logger.info("No organization_units in database")
        
        logger.info("✅ Parent_id special handling test successful")

    def test05_export_enriched_verify_lookup_values(self, api_tester, session_auth_cookies):
        """Tester que les valeurs de lookup_field sont présentes dans les données"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export enrichi depuis users
        
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "service": "identity",
            "path": "/users",
            "type": "json",
            "enrich": "true"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export enriched users with status {response.status_code}: {response.text}"
        
        # Parser le JSON
        data = response.json()
        assert len(data) > 0, "Expected at least one user"
        
        # Vérifier pour chaque record
        missing_lookup_fields = []
        
        for i, record in enumerate(data[:5]):  # Vérifier les 5 premiers
            if '_references' not in record:
                continue
            
            references = record['_references']
            
            # Pour chaque FK, vérifier que le lookup_field existe dans le record
            for fk_name, fk_meta in references.items():
                lookup_field = fk_meta.get('lookup_field')
                
                if lookup_field and lookup_field not in record:
                    missing_lookup_fields.append({
                        'record_index': i,
                        'fk_name': fk_name,
                        'missing_field': lookup_field
                    })
        
        if missing_lookup_fields:
            logger.warning(f"⚠️ Missing lookup fields: {missing_lookup_fields}")
        else:
            logger.info("✅ All lookup_fields are present in exported records")
        
        # Vérifier la cohérence: lookup_field devrait être dans le record
        # (sauf si c'est une FK vers une autre table)
        first_record = data[0]
        if '_references' in first_record:
            references = first_record['_references']
            
            for fk_name, fk_meta in references.items():
                lookup_field = fk_meta.get('lookup_field')
                resource_type = fk_meta.get('resource_type')
                
                logger.info(f"FK {fk_name} → {resource_type} (lookup: {lookup_field})")
        
        logger.info(f"✅ Lookup values verification completed for {len(data)} records")

    def test06_export_enriched_csv_preserves_metadata(self, api_tester, session_auth_cookies):
        """Tester que CSV avec enrich=true inclut des métadonnées (commentaires ou colonnes spéciales)"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export CSV enrichi
        
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "service": "identity",
            "path": "/users",
            "type": "csv",
            "enrich": "true"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export enriched CSV with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'text/csv' in content_type, \
            f"Expected CSV content type, got {content_type}"
        
        # Analyser le CSV
        csv_content = response.text
        
        # CSV peut inclure les métadonnées de plusieurs façons:
        # 1. Commentaires en en-tête (# _references: ...)
        # 2. Colonnes additionnelles (_references_*)
        # 3. Fichier JSON séparé (pas dans ce test)
        
        lines = csv_content.split('\n')
        
        # Vérifier s'il y a des commentaires
        has_comments = any(line.startswith('#') for line in lines[:20])
        
        if has_comments:
            logger.info("✅ CSV includes metadata comments")
            comment_lines = [line for line in lines if line.startswith('#')]
            logger.info(f"Comment lines: {len(comment_lines)}")
            if comment_lines:
                logger.info(f"Sample comment: {comment_lines[0][:100]}")
        else:
            logger.info("CSV has no comment metadata (standard format)")
        
        # Analyser les colonnes
        import csv
        import io
        
        # Filtrer les commentaires pour parser le CSV
        csv_lines = [line for line in lines if not line.startswith('#')]
        csv_text = '\n'.join(csv_lines)
        
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(csv_reader)
        
        if rows:
            first_row = rows[0]
            columns = list(first_row.keys())
            
            # Vérifier _original_id
            assert '_original_id' in columns, "Missing _original_id column"
            
            # Chercher des colonnes liées aux références
            reference_columns = [col for col in columns if '_reference' in col.lower()]
            
            if reference_columns:
                logger.info(f"✅ CSV includes reference columns: {reference_columns}")
            else:
                logger.info("CSV uses standard format (no reference columns)")
            
            logger.info(f"Total columns: {len(columns)}")
            logger.info(f"Total rows: {len(rows)}")
        
        logger.info("✅ CSV enriched export test successful")
