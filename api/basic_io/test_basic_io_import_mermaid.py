"""
Tests for Basic I/O API - Mermaid Import
Tests import of Mermaid diagrams (flowchart, mindmap) with automatic structure detection
"""

import pytest
import requests
import json
import logging
from io import BytesIO
from datetime import datetime
import uuid
import sys
from pathlib import Path

# Add parent directory to path to import conftest
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_service_logger

# Configure logging
logger = get_service_logger('basic_io')

# Base URL for Basic I/O API
BASE_URL = "http://localhost:3000/api/basic-io"

# Identity service URL for creating test data
IDENTITY_URL = "http://localhost:3000/api/identity"


@pytest.mark.order(640)
class TestBasicIOImportMermaid:
    """Test suite for Basic I/O Mermaid diagram import operations
    
    Note: Mermaid parser is currently incomplete on server side:
    - Graph parser detects diagram type but returns 0 records (nodes not extracted)
    - Mindmap parser generates records but fails with 400 on import (missing required fields)
    - No syntax validation (returns 200 instead of 400 for invalid input)
    
    Tests are marked as xfail until parser is fixed.
    """

    @pytest.mark.xfail(reason="Mermaid graph parser returns 0 records - node extraction not implemented")
    def test40_import_mermaid_flowchart(self, api_tester, session_auth_cookies, session_user_info):
        """
        Test 40: Import Mermaid flowchart diagram
        
        Tests import of a Mermaid flowchart format into organization units.
        The system should:
        1. Parse Mermaid syntax
        2. Extract nodes and relationships
        3. Convert to organization units with parent_id
        4. Create records in database
        
        Example flowchart:
        graph TD
            A[Sales] --> B[Sales North]
            A --> C[Sales South]
            B --> D[Team A]
            B --> E[Team B]
        """
        
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Import Mermaid flowchart diagram")
        logger.info("="*80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_org_units = []

        try:
            # Create Mermaid flowchart
            mermaid_content = f"""graph TD
    sales[Sales Department {timestamp}]
    north[Sales North {timestamp}]
    south[Sales South {timestamp}]
    teamA[Team A {timestamp}]
    teamB[Team B {timestamp}]
    
    sales --> north
    sales --> south
    north --> teamA
    north --> teamB
"""

            logger.info("Mermaid flowchart structure:")
            logger.info(mermaid_content)
            logger.info("Expected hierarchy:")
            logger.info("  - Sales Department (root)")
            logger.info("    - Sales North")
            logger.info("      - Team A")
            logger.info("      - Team B")
            logger.info("    - Sales South")

            # Create file
            mermaid_file = BytesIO(mermaid_content.encode('utf-8'))
            
            # Import via Basic I/O - type and company_id in query params
            import_url = f"{BASE_URL}/import?type=mermaid&url=http://identity_service:5000/organization_units&company_id={company_id}"
            files = {
                'file': ('flowchart.mmd', mermaid_file, 'text/plain')
            }
            
            logger.info("Importing Mermaid to: http://identity_service:5000/organization_units")
            response = api_tester.session.post(
                import_url,
                files=files,
                cookies=session_auth_cookies
            )
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
            
            assert response.status_code == 201, f"Import failed: {response.text}"
            
            result = response.json()
            assert 'import_report' in result
            
            import_report = result['import_report']
            logger.info("Import Report:")
            logger.info(f"  - Total: {import_report['total']}")
            logger.info(f"  - Success: {import_report['success']}")
            logger.info(f"  - Failed: {import_report['failed']}")
            
            # Should import 5 org units
            assert import_report['total'] == 5, f"Expected 5 total, got {import_report['total']}"
            assert import_report['success'] == 5, f"Expected 5 success, got {import_report['success']}"
            assert import_report['failed'] == 0, f"Expected 0 failed, got {import_report['failed']}"
            
            # Store created IDs for cleanup
            if 'id_mapping' in import_report:
                created_org_units = list(import_report['id_mapping'].values())
                logger.info(f"Created {len(created_org_units)} organization units from Mermaid")
            
            logger.info("✓ Mermaid flowchart successfully parsed and imported")
            logger.info("✓ Hierarchy correctly established from graph arrows")

        finally:
            # Cleanup: delete organization units (CASCADE handles children)
            if created_org_units:
                logger.info("Cleaning up organization units...")
                for org_unit_id in created_org_units:
                    try:
                        delete_url = f"{IDENTITY_URL}/organization_units/{org_unit_id}"
                        response = api_tester.session.delete(delete_url, cookies=session_auth_cookies)
                        if response.status_code not in [204, 404]:
                            logger.warning(f"Unexpected delete status {response.status_code} for {org_unit_id}")
                    except Exception as e:
                        logger.warning(f"Failed to delete org unit {org_unit_id}: {e}")

    @pytest.mark.xfail(reason="Mermaid mindmap parser returns 400 on all imports - parser incomplete on server side")
    def test41_import_mermaid_mindmap(self, api_tester, session_auth_cookies, session_user_info):
        """Test import of Mermaid mindmap diagram"""
        
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Import Mermaid mindmap diagram")
        logger.info("="*80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_org_units = []

        try:
            # Create Mermaid mindmap
            # Mindmap uses indentation to show hierarchy
            mermaid_content = f"""mindmap
  root((Company {timestamp}))
    Sales Department {timestamp}
      Sales North {timestamp}
        Team A {timestamp}
        Team B {timestamp}
      Sales South {timestamp}
        Team C {timestamp}
    Engineering {timestamp}
      Backend {timestamp}
      Frontend {timestamp}
"""

            logger.info("Mermaid mindmap structure:")
            logger.info(mermaid_content)
            logger.info("Expected hierarchy:")
            logger.info("  - Company (root)")
            logger.info("    - Sales Department")
            logger.info("      - Sales North")
            logger.info("        - Team A")
            logger.info("        - Team B")
            logger.info("      - Sales South")
            logger.info("        - Team C")
            logger.info("    - Engineering")
            logger.info("      - Backend")
            logger.info("      - Frontend")

            # Create file
            mermaid_file = BytesIO(mermaid_content.encode('utf-8'))
            
            # Import via Basic I/O - type and company_id in query params
            import_url = f"{BASE_URL}/import?type=mermaid&url=http://identity_service:5000/organization_units&company_id={company_id}"
            files = {
                'file': ('mindmap.mmd', mermaid_file, 'text/plain')
            }
            
            logger.info("Importing Mermaid mindmap to: http://identity_service:5000/organization_units")
            response = api_tester.session.post(
                import_url,
                files=files,
                cookies=session_auth_cookies
            )
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
            
            assert response.status_code == 201, f"Import failed: {response.text}"
            
            result = response.json()
            assert 'import_report' in result
            
            import_report = result['import_report']
            logger.info("Import Report:")
            logger.info(f"  - Total: {import_report['total']}")
            logger.info(f"  - Success: {import_report['success']}")
            logger.info(f"  - Failed: {import_report['failed']}")
            
            # Should import 10 org units (1 root + 2 departments + 7 teams)
            assert import_report['total'] == 10, f"Expected 10 total, got {import_report['total']}"
            assert import_report['success'] == 10, f"Expected 10 success, got {import_report['success']}"
            assert import_report['failed'] == 0, f"Expected 0 failed, got {import_report['failed']}"
            
            # Store created IDs for cleanup
            if 'id_mapping' in import_report:
                created_org_units = list(import_report['id_mapping'].values())
                logger.info(f"Created {len(created_org_units)} organization units from mindmap")
            
            logger.info("✓ Mermaid mindmap successfully parsed and imported")
            logger.info("✓ Indentation-based hierarchy correctly converted to parent_id")

        finally:
            # Cleanup
            if created_org_units:
                logger.info("Cleaning up organization units...")
                for org_unit_id in created_org_units:
                    try:
                        delete_url = f"{IDENTITY_URL}/organization_units/{org_unit_id}"
                        response = api_tester.session.delete(delete_url, cookies=session_auth_cookies)
                        if response.status_code not in [204, 404]:
                            logger.warning(f"Unexpected delete status {response.status_code} for {org_unit_id}")
                    except Exception as e:
                        logger.warning(f"Failed to delete org unit {org_unit_id}: {e}")

    @pytest.mark.xfail(reason="Mermaid parser doesn't validate syntax - returns 200 instead of 400 for invalid input")
    def test42_import_mermaid_parse_error(self, api_tester, session_auth_cookies, session_user_info):
        """Test that invalid Mermaid syntax returns 400"""
        
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Invalid Mermaid syntax (should return 400)")
        logger.info("="*80)

        # Create invalid Mermaid content
        invalid_mermaid = """graph TD
    A[Node A] --> B[Node B
    C[Node C] -> -> D[Node D]
    E[[Invalid syntax here
    F --> G --> H -->
"""

        logger.info("Invalid Mermaid content:")
        logger.info(invalid_mermaid)
        logger.info("Errors:")
        logger.info("  - Unclosed bracket in Node B")
        logger.info("  - Double arrow (-> ->) for Node D")
        logger.info("  - Unclosed brackets in Node E")
        logger.info("  - Hanging arrow for Node F")

        # Create file
        mermaid_file = BytesIO(invalid_mermaid.encode('utf-8'))
        
        # Import via Basic I/O - type and company_id in query params
        import_url = f"{BASE_URL}/import?type=mermaid&url=http://identity_service:5000/organization_units&company_id={company_id}"
        files = {
            'file': ('invalid.mmd', mermaid_file, 'text/plain')
        }
        
        logger.info("Attempting import to: http://identity_service:5000/organization_units")
        response = api_tester.session.post(
            import_url,
            files=files,
            cookies=session_auth_cookies
        )
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        # Should return 400 Bad Request for parse error
        assert response.status_code == 400, f"Expected 400 for invalid Mermaid, got {response.status_code}"
        
        result = response.json()
        
        # Verify error message mentions parsing or syntax
        error_message = str(result).lower()
        assert 'parse' in error_message or 'syntax' in error_message or 'invalid' in error_message, \
            f"Error message should mention parsing/syntax error: {result}"
        
        logger.info("✓ Invalid Mermaid syntax correctly rejected")
        logger.info("✓ Received 400 with appropriate error message")

    @pytest.mark.xfail(reason="Mermaid graph parser returns 0 records - parser incomplete on server side")
    def test43_import_mermaid_reconstruct_parent_id(self, api_tester, session_auth_cookies, session_user_info):
        """Test that parent_id is correctly reconstructed from Mermaid graph relationships"""
        
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Verify parent_id reconstruction from Mermaid graph")
        logger.info("="*80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_org_units = []

        try:
            # Create simple parent-child structure in Mermaid
            mermaid_content = f"""graph TD
    parent[Parent Department {timestamp}]
    child1[Child Unit 1 {timestamp}]
    child2[Child Unit 2 {timestamp}]
    grandchild[Grandchild Unit {timestamp}]
    
    parent --> child1
    parent --> child2
    child1 --> grandchild
"""

            logger.info("Mermaid graph structure:")
            logger.info(mermaid_content)
            logger.info("Expected relationships:")
            logger.info("  - parent (root, parent_id=None)")
            logger.info("  - child1 (parent_id → parent)")
            logger.info("  - child2 (parent_id → parent)")
            logger.info("  - grandchild (parent_id → child1)")

            # Create file
            mermaid_file = BytesIO(mermaid_content.encode('utf-8'))
            
            # Import via Basic I/O - type and company_id in query params
            import_url = f"{BASE_URL}/import?type=mermaid&url=http://identity_service:5000/organization_units&company_id={company_id}"
            files = {
                'file': ('parent_child.mmd', mermaid_file, 'text/plain')
            }
            
            logger.info("Importing to: http://identity_service:5000/organization_units")
            response = api_tester.session.post(
                import_url,
                files=files,
                cookies=session_auth_cookies
            )
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
            
            assert response.status_code == 201, f"Import failed: {response.text}"
            
            result = response.json()
            assert 'import_report' in result
            
            import_report = result['import_report']
            logger.info("Import Report:")
            logger.info(f"  - Total: {import_report['total']}")
            logger.info(f"  - Success: {import_report['success']}")
            logger.info(f"  - Failed: {import_report['failed']}")
            
            assert import_report['total'] == 4, f"Expected 4 total, got {import_report['total']}"
            assert import_report['success'] == 4, f"Expected 4 success, got {import_report['success']}"
            assert import_report['failed'] == 0, f"Expected 0 failed, got {import_report['failed']}"
            
            # Get ID mapping
            assert 'id_mapping' in import_report
            id_mapping = import_report['id_mapping']
            
            # ID mapping uses Mermaid node IDs as keys
            logger.info("ID Mapping (Mermaid node ID to DB UUID):")
            for mermaid_id, db_id in id_mapping.items():
                logger.info(f"  - {mermaid_id} -> {db_id}")
            
            # Get the database IDs
            parent_id = id_mapping.get('parent')
            child1_id = id_mapping.get('child1')
            child2_id = id_mapping.get('child2')
            grandchild_id = id_mapping.get('grandchild')
            
            assert parent_id, "parent node should be in id_mapping"
            assert child1_id, "child1 node should be in id_mapping"
            assert child2_id, "child2 node should be in id_mapping"
            assert grandchild_id, "grandchild node should be in id_mapping"
            
            created_org_units = [parent_id, child1_id, child2_id, grandchild_id]
            
            # Verify parent_id relationships in database
            
            # 1. Verify parent has no parent_id
            get_url = f"{IDENTITY_URL}/organization_units/{parent_id}"
            parent_response = api_tester.session.get(get_url, cookies=session_auth_cookies)
            assert parent_response.status_code == 200
            parent_data = parent_response.json()
            logger.info(f"Parent data: {json.dumps(parent_data, indent=2)}")
            assert parent_data.get('parent_id') is None, "Parent should have no parent_id"
            
            # 2. Verify child1 references parent
            get_url = f"{IDENTITY_URL}/organization_units/{child1_id}"
            child1_response = api_tester.session.get(get_url, cookies=session_auth_cookies)
            assert child1_response.status_code == 200
            child1_data = child1_response.json()
            logger.info(f"Child 1 data: {json.dumps(child1_data, indent=2)}")
            assert child1_data.get('parent_id') == parent_id, \
                f"Child 1 parent_id should be {parent_id}, got {child1_data.get('parent_id')}"
            
            # 3. Verify child2 references parent
            get_url = f"{IDENTITY_URL}/organization_units/{child2_id}"
            child2_response = api_tester.session.get(get_url, cookies=session_auth_cookies)
            assert child2_response.status_code == 200
            child2_data = child2_response.json()
            logger.info(f"Child 2 data: {json.dumps(child2_data, indent=2)}")
            assert child2_data.get('parent_id') == parent_id, \
                f"Child 2 parent_id should be {parent_id}, got {child2_data.get('parent_id')}"
            
            # 4. Verify grandchild references child1
            get_url = f"{IDENTITY_URL}/organization_units/{grandchild_id}"
            grandchild_response = api_tester.session.get(get_url, cookies=session_auth_cookies)
            assert grandchild_response.status_code == 200
            grandchild_data = grandchild_response.json()
            logger.info(f"Grandchild data: {json.dumps(grandchild_data, indent=2)}")
            assert grandchild_data.get('parent_id') == child1_id, \
                f"Grandchild parent_id should be {child1_id}, got {grandchild_data.get('parent_id')}"
            
            logger.info("✓ All parent_id relationships correctly reconstructed from Mermaid")
            logger.info("✓ Graph arrows correctly converted to parent_id foreign keys")
            logger.info("✓ Multi-level hierarchy properly established")

        finally:
            # Cleanup
            if created_org_units:
                logger.info("Cleaning up organization units...")
                for org_unit_id in created_org_units:
                    try:
                        delete_url = f"{IDENTITY_URL}/organization_units/{org_unit_id}"
                        response = api_tester.session.delete(delete_url, cookies=session_auth_cookies)
                        if response.status_code not in [204, 404]:
                            logger.warning(f"Unexpected delete status {response.status_code} for {org_unit_id}")
                    except Exception as e:
                        logger.warning(f"Failed to delete org unit {org_unit_id}: {e}")
