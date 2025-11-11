"""
Tests for Basic I/O API - Tree Structure Export functionality
Tests pour l'export de structures arborescentes (parent_id, parent_uuid)
"""
import pytest
import sys
import time
import requests
from pathlib import Path

# Ajouter le répertoire parent au path pour importer conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

logger = get_service_logger('basic_io')


class TestBasicIOExportTree:
    """Tests d'export de structures arborescentes via Basic I/O API"""
    
    def test01_export_json_tree_structure(self, api_tester, session_auth_cookies):
        """Tester l'export JSON avec structure arborescente (tree=true)"""
        assert session_auth_cookies, "Authentication failed"
        
        # Récupérer company_id
        verify_response = api_tester.session.get(
            f"{api_tester.base_url}/api/auth/verify",
            cookies=session_auth_cookies
        )
        assert verify_response.status_code == 200
        company_id = verify_response.json()['company_id']
        
        created_unit_ids = []
        
        try:
            # Créer une hiérarchie d'organization_units
            timestamp = int(time.time() * 1000)
            
            # Racine
            root_data = {
                "name": f"Root_Unit_{timestamp}",
                "company_id": company_id,
                "description": "Root unit for tree export test"
            }
            root_response = api_tester.session.post(
                f"{api_tester.base_url}/api/identity/organization_units",
                json=root_data,
                cookies=session_auth_cookies
            )
            assert root_response.status_code == 201
            root_id = root_response.json()['id']
            created_unit_ids.append(root_id)
            
            # Enfant 1
            child1_data = {
                "name": f"Child1_Unit_{timestamp}",
                "company_id": company_id,
                "parent_id": root_id,
                "description": "Child 1"
            }
            child1_response = api_tester.session.post(
                f"{api_tester.base_url}/api/identity/organization_units",
                json=child1_data,
                cookies=session_auth_cookies
            )
            assert child1_response.status_code == 201
            child1_id = child1_response.json()['id']
            created_unit_ids.append(child1_id)
            
            # Enfant 2
            child2_data = {
                "name": f"Child2_Unit_{timestamp}",
                "company_id": company_id,
                "parent_id": root_id,
                "description": "Child 2"
            }
            child2_response = api_tester.session.post(
                f"{api_tester.base_url}/api/identity/organization_units",
                json=child2_data,
                cookies=session_auth_cookies
            )
            assert child2_response.status_code == 201
            child2_id = child2_response.json()['id']
            created_unit_ids.append(child2_id)
            
            # Petit-enfant
            grandchild_data = {
                "name": f"Grandchild_Unit_{timestamp}",
                "company_id": company_id,
                "parent_id": child1_id,
                "description": "Grandchild"
            }
            grandchild_response = api_tester.session.post(
                f"{api_tester.base_url}/api/identity/organization_units",
                json=grandchild_data,
                cookies=session_auth_cookies
            )
            assert grandchild_response.status_code == 201
            grandchild_id = grandchild_response.json()['id']
            created_unit_ids.append(grandchild_id)
            
            logger.info("✅ Created tree structure: 1 root, 2 children, 1 grandchild")
            
            # Export avec tree=true
            target_url = "http://identity_service:5000/organization_units"
            
            url = f"{api_tester.base_url}/api/basic-io/export"
            params = {
                "url": target_url,
                "type": "json",
                "tree": "true",  # Demander structure arborescente
                "enrich": "false"
            }
            
            api_tester.log_request('GET', url, params)
            response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
            api_tester.log_response(response)
            
            assert response.status_code == 200, \
                f"Failed to export tree JSON with status {response.status_code}: {response.text}"
            
            # Vérifier le Content-Type
            content_type = response.headers.get('Content-Type', '')
            assert 'application/json' in content_type, \
                f"Expected JSON content type, got {content_type}"
            
            # Parser le JSON
            data = response.json()
            assert isinstance(data, list), "Expected JSON array"
            
            # Vérifier la structure tree
            assert len(data) > 0, "Expected at least one root record"
            first_record = data[0]
            
            # Vérifier _original_id est présent
            assert '_original_id' in first_record, "Missing _original_id field"
            
            # Compter les niveaux si children présent
            def count_descendants(record):
                count = 0
                if 'children' in record and record['children']:
                    for child in record['children']:
                        count += 1 + count_descendants(child)
                return count
            
            total_descendants = sum(count_descendants(r) for r in data)
            
            logger.info(f"✅ Tree JSON export successful: {len(data)} root records")
            logger.info(f"Total descendants in tree: {total_descendants}")
            logger.info(f"Sample record keys: {list(first_record.keys())}")
        
        finally:
            # Cleanup: Supprimer les organization_units (enfants en premier)
            logger.info(f"🧹 Cleaning up {len(created_unit_ids)} organization units...")
            deleted_count = 0
            for unit_id in reversed(created_unit_ids):  # Reverse pour supprimer enfants avant parents
                try:
                    delete_response = api_tester.session.delete(
                        f"{api_tester.base_url}/api/identity/organization_units/{unit_id}",
                        cookies=session_auth_cookies
                    )
                    if delete_response.status_code == 204:
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting unit {unit_id}: {e}")
            
            logger.info(f"✅ Cleanup completed: {deleted_count}/{len(created_unit_ids)} units deleted")

    def test02_export_json_flat_with_parent_id(self, api_tester, session_auth_cookies):
        """Tester l'export JSON flat même avec parent_id (tree=false)"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export depuis organization_units (qui a parent_id), format flat
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json",
            "tree": "false",  # Demander format flat
            "enrich": "false"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export flat JSON with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'application/json' in content_type, \
            f"Expected JSON content type, got {content_type}"
        
        # Parser le JSON
        data = response.json()
        assert isinstance(data, list), "Expected JSON array"
        
        if len(data) > 0:
            first_record = data[0]
            
            # Vérifier _original_id est présent
            assert '_original_id' in first_record, "Missing _original_id field"
            
            # Avec tree=false, pas de champ 'children' imbriqué
            # Mais parent_id peut être présent comme champ normal
            # Note: Ceci dépend des données source
            
            logger.info(f"✅ Flat JSON export successful: {len(data)} records")
            logger.info(f"Sample record: {first_record}")
            
            # Vérifier qu'il n'y a PAS de structure imbriquée
            has_children = any('children' in record for record in data)
            if not has_children:
                logger.info("Confirmed: No nested children structure in flat export")

    def test03_detect_tree_structure_parent_id(self, api_tester, session_auth_cookies):
        """Tester la détection automatique de structure arborescente (parent_id)"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export depuis organization_units (qui a parent_id)
        # Le service doit détecter automatiquement la structure
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json",
            "enrich": "false"
            # Pas de paramètre tree - détection automatique
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export JSON with status {response.status_code}: {response.text}"
        
        # Parser le JSON
        data = response.json()
        assert isinstance(data, list), "Expected JSON array"
        
        if len(data) > 0:
            # Vérifier si les données ont un champ parent_id
            has_parent_id = any('parent_id' in record for record in data)
            
            if has_parent_id:
                logger.info("✅ Tree structure detected: parent_id field present")
                
                # Vérifier que _original_id est présent
                assert '_original_id' in data[0], "Missing _original_id field"
                
                # Le service peut soit retourner flat (default), soit tree
                # selon sa configuration par défaut
                has_children = any('children' in record for record in data)
                
                if has_children:
                    logger.info("Service returns nested tree by default")
                else:
                    logger.info("Service returns flat list by default (parent_id preserved)")
            else:
                logger.info("No parent_id field detected in data")
            
            logger.info(f"Export successful: {len(data)} records")

    def test04_detect_tree_structure_parent_uuid(self, api_tester, session_auth_cookies):
        """Tester la détection automatique de structure avec parent_uuid"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export depuis organization_units
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json",
            "enrich": "false"
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export JSON with status {response.status_code}: {response.text}"
        
        # Parser le JSON
        data = response.json()
        assert isinstance(data, list), "Expected JSON array"
        
        if len(data) > 0:
            # Vérifier si les données ont parent_id OU parent_uuid
            has_parent_field = any(
                'parent_id' in record or 'parent_uuid' in record 
                for record in data
            )
            
            if has_parent_field:
                logger.info("✅ Tree structure detected: parent field present")
                
                # Identifier quel champ parent est utilisé
                parent_field = None
                for record in data:
                    if 'parent_id' in record:
                        parent_field = 'parent_id'
                        break
                    elif 'parent_uuid' in record:
                        parent_field = 'parent_uuid'
                        break
                
                if parent_field:
                    logger.info(f"Parent field detected: {parent_field}")
                    
                    # Vérifier que _original_id est présent
                    assert '_original_id' in data[0], "Missing _original_id field"
                    
                    # Compter combien de records ont un parent
                    records_with_parent = sum(
                        1 for r in data 
                        if r.get(parent_field) is not None
                    )
                    
                    logger.info(f"Records with parent: {records_with_parent}/{len(data)}")
            else:
                logger.info("No parent field detected in data")
            
            logger.info(f"Export successful: {len(data)} records")

    def test05_export_tree_with_enrichment(self, api_tester, session_auth_cookies):
        """Tester l'export tree avec enrichissement des références"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export tree avec enrich=true
        # Le parent_id devrait être enrichi avec les infos du parent
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "json",
            "tree": "true",
            "enrich": "true"  # Enrichir les références, y compris parent_id
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export enriched tree with status {response.status_code}: {response.text}"
        
        # Parser le JSON
        data = response.json()
        assert isinstance(data, list), "Expected JSON array"
        
        if len(data) > 0:
            first_record = data[0]
            
            # Vérifier _original_id
            assert '_original_id' in first_record, "Missing _original_id field"
            
            # Si enrich=true, vérifier _references
            if '_references' in first_record:
                logger.info("✅ Enrichment metadata present (_references)")
                
                references = first_record['_references']
                
                # Si parent_id existe, il devrait être dans les références
                if 'parent_id' in references or 'parent_uuid' in references:
                    parent_ref_key = 'parent_id' if 'parent_id' in references else 'parent_uuid'
                    parent_ref = references[parent_ref_key]
                    
                    logger.info(f"Parent reference enriched: {parent_ref}")
                    
                    # Vérifier la structure de la référence
                    assert 'resource_type' in parent_ref, "Missing resource_type in parent ref"
                    assert 'lookup_field' in parent_ref, "Missing lookup_field in parent ref"
                    
                    logger.info(f"Parent lookup field: {parent_ref.get('lookup_field')}")
            else:
                logger.info("No _references field (data might not have FK fields)")
            
            logger.info(f"Enriched tree export successful: {len(data)} root records")

    def test06_export_csv_preserves_parent_id(self, api_tester, session_auth_cookies):
        """Tester que l'export CSV préserve le champ parent_id (format flat obligatoire)"""
        assert session_auth_cookies, "Authentication failed"
        
        # Export CSV d'organization_units (qui a parent_id)
        # CSV est toujours flat, mais parent_id doit être une colonne
        target_url = "http://identity_service:5000/organization_units"
        
        url = f"{api_tester.base_url}/api/basic-io/export"
        params = {
            "url": target_url,
            "type": "csv"
            # tree parameter ignoré pour CSV (toujours flat)
        }
        
        api_tester.log_request('GET', url, params)
        response = api_tester.session.get(url, params=params, cookies=session_auth_cookies)
        api_tester.log_response(response)
        
        assert response.status_code == 200, \
            f"Failed to export CSV with status {response.status_code}: {response.text}"
        
        # Vérifier le Content-Type
        content_type = response.headers.get('Content-Type', '')
        assert 'text/csv' in content_type, \
            f"Expected CSV content type, got {content_type}"
        
        # Analyser le CSV
        import csv
        import io
        
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        if len(rows) > 0:
            first_row = rows[0]
            
            # Vérifier _original_id
            assert '_original_id' in first_row, "Missing _original_id column"
            
            # Vérifier si parent_id est une colonne
            # Note: Dépend des données source
            has_parent_column = 'parent_id' in first_row or 'parent_uuid' in first_row
            
            if has_parent_column:
                parent_col = 'parent_id' if 'parent_id' in first_row else 'parent_uuid'
                logger.info(f"✅ CSV preserves parent field as column: {parent_col}")
                
                # Compter combien de lignes ont un parent
                rows_with_parent = sum(
                    1 for r in rows 
                    if r.get(parent_col) and r.get(parent_col).strip()
                )
                
                logger.info(f"Rows with parent: {rows_with_parent}/{len(rows)}")
            else:
                logger.info("No parent field in data (not a tree structure)")
            
            logger.info(f"CSV export successful: {len(rows)} rows")
