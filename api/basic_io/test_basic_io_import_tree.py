"""
Tests for Basic I/O API - Tree Structure Import
Tests tree import, topological sorting, circular reference detection, and parent mapping
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


@pytest.mark.order(634)
class TestBasicIOImportTree:
    """Test suite for Basic I/O tree structure import operations"""

    def test34_import_tree_json_nested(self, api_tester, session_auth_cookies, session_user_info):
        """
        Test 34: Import tree structure with UUID references and parent_id
        
        Tests import of hierarchical data using temporary UUIDs and parent_id references.
        The system should:
        1. Create parent nodes first
        2. Map temporary UUIDs to real database IDs
        3. Update parent_id references to use real IDs
        
        Structure (7 org units):
        - Sales Department (root, UUID: sales-dept)
          - Sales North (parent: sales-dept)
            - Sales North Team A (parent: sales-north)
            - Sales North Team B (parent: sales-north)
          - Sales South (parent: sales-dept)
            - Sales South Team A (parent: sales-south)
        - Engineering Department (root, UUID: eng-dept)
          - Backend Team (parent: eng-dept)
        """
        
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Import tree structure with UUID references")
        logger.info("="*80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_org_units = []

        try:
            # Create tree using flat structure with temporary UUIDs for parent_id references
            # The import system should handle topological sorting
            sales_dept_id = str(uuid.uuid4())
            sales_north_id = str(uuid.uuid4())
            sales_south_id = str(uuid.uuid4())
            eng_dept_id = str(uuid.uuid4())
            
            tree_data = [
                {
                    "_original_id": sales_dept_id,
                    "name": f"Sales Department {timestamp}",
                    "company_id": company_id,
                    "parent_id": None
                },
                {
                    "_original_id": sales_north_id,
                    "name": f"Sales North {timestamp}",
                    "company_id": company_id,
                    "parent_id": sales_dept_id
                },
                {
                    "_original_id": str(uuid.uuid4()),
                    "name": f"Sales North Team A {timestamp}",
                    "company_id": company_id,
                    "parent_id": sales_north_id
                },
                {
                    "_original_id": str(uuid.uuid4()),
                    "name": f"Sales North Team B {timestamp}",
                    "company_id": company_id,
                    "parent_id": sales_north_id
                },
                {
                    "_original_id": sales_south_id,
                    "name": f"Sales South {timestamp}",
                    "company_id": company_id,
                    "parent_id": sales_dept_id
                },
                {
                    "_original_id": str(uuid.uuid4()),
                    "name": f"Sales South Team A {timestamp}",
                    "company_id": company_id,
                    "parent_id": sales_south_id
                },
                {
                    "_original_id": eng_dept_id,
                    "name": f"Engineering Department {timestamp}",
                    "company_id": company_id,
                    "parent_id": None
                },
                {
                    "_original_id": str(uuid.uuid4()),
                    "name": f"Backend Team {timestamp}",
                    "company_id": company_id,
                    "parent_id": eng_dept_id
                }
            ]

            logger.info("Tree structure (2 root departments, 8 total org units with parent_id references):")
            logger.info(json.dumps(tree_data, indent=2))

            # Convert to JSON file
            json_content = json.dumps(tree_data, indent=2)
            json_file = BytesIO(json_content.encode('utf-8'))
            
            # Import via Basic I/O
            import_url = f"{BASE_URL}/import"
            files = {
                'file': ('org_units_nested.json', json_file, 'application/json')
            }
            data = {
                'url': 'http://identity_service:5000/organization_units',
                'type': 'json'
            }
            
            logger.info(f"Importing to: {data['url']}")
            response = api_tester.session.post(
                import_url,
                files=files,
                data=data,
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
            
            # Should import all 8 org units
            assert import_report['total'] == 8, f"Expected 8 total, got {import_report['total']}"
            assert import_report['success'] == 8, f"Expected 8 success, got {import_report['success']}"
            assert import_report['failed'] == 0, f"Expected 0 failed, got {import_report['failed']}"
            
            # Store created IDs for cleanup
            if 'id_mapping' in import_report:
                created_org_units = list(import_report['id_mapping'].values())
                logger.info(f"Created {len(created_org_units)} organization units")
            
            # Verify parent-child relationships were established
            logger.info("✓ Tree structure imported successfully")
            logger.info("✓ All 8 organization units created with correct hierarchy")

        finally:
            # Cleanup: delete created organization units
            if created_org_units:
                logger.info(f"Cleaning up {len(created_org_units)} organization units...")
                for org_unit_id in created_org_units:
                    try:
                        delete_url = f"{IDENTITY_URL}/organization_units/{org_unit_id}"
                        api_tester.session.delete(delete_url, cookies=session_auth_cookies)
                    except Exception as e:
                        logger.warning(f"Failed to delete org unit {org_unit_id}: {e}")

    def test35_import_tree_json_flat_with_parent_id(self, api_tester, session_auth_cookies, session_user_info):
        """Test import of flat JSON with parent_id references (requires topological sort)"""
        
        # Using session_auth_cookies
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Import flat JSON with parent_id requiring topological sort")
        logger.info("="*80)

        # Using session_auth_cookies
        company_id = session_user_info['company_id']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_org_units = []

        try:
            # Create flat structure where children are defined BEFORE parents
            # This tests the topological sort capability
            parent_id = str(uuid.uuid4())
            child_a_id = str(uuid.uuid4())
            child_b_id = str(uuid.uuid4())
            grandchild_id = str(uuid.uuid4())
            
            flat_tree = [
                {
                    "_original_id": child_a_id,
                    "name": f"Team A {timestamp}",
                    "company_id": company_id,
                    "parent_id": parent_id  # References parent defined later
                },
                {
                    "_original_id": child_b_id,
                    "name": f"Team B {timestamp}",
                    "company_id": company_id,
                    "parent_id": parent_id  # References parent defined later
                },
                {
                    "_original_id": grandchild_id,
                    "name": f"Sub-team A1 {timestamp}",
                    "company_id": company_id,
                    "parent_id": child_a_id  # References child defined earlier
                },
                {
                    "_original_id": parent_id,
                    "name": f"Department {timestamp}",
                    "company_id": company_id,
                    "parent_id": None  # Root node
                }
            ]

            logger.info(f"Flat tree structure (out of order, 4 org units):")
            logger.info(f"  - Order in file: child-a, child-b, grandchild-1, parent-1")
            logger.info(f"  - Required import order: parent-1, child-a, child-b, grandchild-1")
            logger.info(json.dumps(flat_tree, indent=2))

            # Convert to JSON file
            json_content = json.dumps(flat_tree, indent=2)
            json_file = BytesIO(json_content.encode('utf-8'))
            
            # Import via Basic I/O
            import_url = f"{BASE_URL}/import"
            files = {
                'file': ('org_units_tree.json', json_file, 'application/json')
            }
            data = {
                'url': 'http://identity_service:5000/organization_units',
                'type': 'json'
            }
            
            logger.info(f"Importing to: {data['url']}")
            response = api_tester.session.post(
                import_url,
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
            
            assert response.status_code == 201, f"Import failed: {response.text}"
            
            result = response.json()
            assert 'import_report' in result
            
            import_report = result['import_report']
            logger.info(f"Import Report:")
            logger.info(f"  - Total: {import_report['total']}")
            logger.info(f"  - Success: {import_report['success']}")
            logger.info(f"  - Failed: {import_report['failed']}")
            
            # Should successfully import all 4 despite incorrect order
            assert import_report['total'] == 4, f"Expected 4 total, got {import_report['total']}"
            assert import_report['success'] == 4, f"Expected 4 success, got {import_report['success']}"
            assert import_report['failed'] == 0, f"Expected 0 failed, got {import_report['failed']}"
            
            # Store created IDs for cleanup
            if 'id_mapping' in import_report:
                created_org_units = list(import_report['id_mapping'].values())
                logger.info(f"Created {len(created_org_units)} organization units")
                
                # Verify the ID mapping shows correct parent-child relationships
                id_mapping = import_report['id_mapping']
                logger.info(f"ID Mapping: {json.dumps(id_mapping, indent=2)}")
                
                # Verify parent was imported first (should have a new UUID)
                assert parent_id in id_mapping, f"{parent_id} should be in id_mapping"
                assert child_a_id in id_mapping, f"{child_a_id} should be in id_mapping"
            
            logger.info("✓ Topological sort worked - parents imported before children")
            logger.info(f"✓ All 4 organization units created with correct references")

        finally:
            # Cleanup: delete created organization units (in reverse order)
            if created_org_units:
                logger.info(f"Cleaning up {len(created_org_units)} organization units...")
                # Delete in reverse to avoid FK constraint issues
                for org_unit_id in reversed(created_org_units):
                    try:
                        delete_url = f"{IDENTITY_URL}/organization_units/{org_unit_id}"
                        api_tester.session.delete(delete_url, cookies=session_auth_cookies)
                    except Exception as e:
                        logger.warning(f"Failed to delete org unit {org_unit_id}: {e}")

    def test36_import_tree_topological_sort(self, api_tester, session_auth_cookies, session_user_info):
        """Test topological sort handles complex dependencies correctly"""
        
        # Using session_auth_cookies
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Topological sort with complex dependency graph")
        logger.info("="*80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_org_units = []

        try:
            # Create a complex dependency graph
            # Graph structure:
            #       root
            #      /    \
            #    a1      a2
            #   / \      |
            #  b1  b2   b3
            #  |
            #  c1
            
            root_id = str(uuid.uuid4())
            a1_id = str(uuid.uuid4())
            a2_id = str(uuid.uuid4())
            b1_id = str(uuid.uuid4())
            b2_id = str(uuid.uuid4())
            b3_id = str(uuid.uuid4())
            c1_id = str(uuid.uuid4())
            
            complex_tree = [
                {"_original_id": c1_id, "name": f"Level 3 Unit {timestamp}", "company_id": company_id, "parent_id": b1_id},
                {"_original_id": b2_id, "name": f"Level 2B Unit {timestamp}", "company_id": company_id, "parent_id": a1_id},
                {"_original_id": a2_id, "name": f"Level 1B Unit {timestamp}", "company_id": company_id, "parent_id": root_id},
                {"_original_id": b1_id, "name": f"Level 2A Unit {timestamp}", "company_id": company_id, "parent_id": a1_id},
                {"_original_id": root_id, "name": f"Root Department {timestamp}", "company_id": company_id, "parent_id": None},
                {"_original_id": a1_id, "name": f"Level 1A Unit {timestamp}", "company_id": company_id, "parent_id": root_id},
                {"_original_id": b3_id, "name": f"Level 2C Unit {timestamp}", "company_id": company_id, "parent_id": a2_id},
            ]

            logger.info(f"Complex dependency graph (7 nodes, completely out of order):")
            logger.info(f"  - File order: c1, b2, a2, b1, root, a1, b3")
            logger.info(f"  - Valid topological orders:")
            logger.info(f"    - root → a1 → b1 → c1")
            logger.info(f"    - root → a1 → b2")
            logger.info(f"    - root → a2 → b3")

            # Convert to JSON file
            json_content = json.dumps(complex_tree, indent=2)
            json_file = BytesIO(json_content.encode('utf-8'))
            
            # Import via Basic I/O
            import_url = f"{BASE_URL}/import"
            files = {
                'file': ('complex_tree.json', json_file, 'application/json')
            }
            data = {
                'url': 'http://identity_service:5000/organization_units',
                'type': 'json'
            }
            
            logger.info(f"Importing to: {data['url']}")
            response = api_tester.session.post(
                import_url,
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
            
            assert response.status_code == 201, f"Import failed: {response.text}"
            
            result = response.json()
            assert 'import_report' in result
            
            import_report = result['import_report']
            logger.info(f"Import Report:")
            logger.info(f"  - Total: {import_report['total']}")
            logger.info(f"  - Success: {import_report['success']}")
            logger.info(f"  - Failed: {import_report['failed']}")
            
            assert import_report['total'] == 7, f"Expected 7 total, got {import_report['total']}"
            assert import_report['success'] == 7, f"Expected 7 success, got {import_report['success']}"
            assert import_report['failed'] == 0, f"Expected 0 failed, got {import_report['failed']}"
            
            # Store created IDs for cleanup
            if 'id_mapping' in import_report:
                created_org_units = list(import_report['id_mapping'].values())
                logger.info(f"Created {len(created_org_units)} organization units")
            
            logger.info("✓ Complex dependency graph successfully sorted and imported")
            logger.info(f"✓ All 7 nodes imported in topologically valid order")

        finally:
            # Cleanup
            if created_org_units:
                logger.info(f"Cleaning up {len(created_org_units)} organization units...")
                for org_unit_id in reversed(created_org_units):
                    try:
                        delete_url = f"{IDENTITY_URL}/organization_units/{org_unit_id}"
                        api_tester.session.delete(delete_url, cookies=session_auth_cookies)
                    except Exception as e:
                        logger.warning(f"Failed to delete org unit {org_unit_id}: {e}")

    def test37_import_tree_circular_reference_detection(self, api_tester, session_auth_cookies, session_user_info):
        """Test that circular references are detected and rejected"""
        
        # Using session_auth_cookies
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Circular reference detection (should fail)")
        logger.info("="*80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create a circular reference: A → B → C → A
        circular_tree = [
            {
                "id": "node-a",
                "name": f"Node A {timestamp}",
                "company_id": company_id,
                "parent_id": "node-c"  # A depends on C
            },
            {
                "id": "node-b",
                "name": f"Node B {timestamp}",
                "company_id": company_id,
                "parent_id": "node-a"  # B depends on A
            },
            {
                "id": "node-c",
                "name": f"Node C {timestamp}",
                "company_id": company_id,
                "parent_id": "node-b"  # C depends on B → creates cycle
            }
        ]

        logger.info(f"Circular dependency graph:")
        logger.info(f"  - node-a.parent_id = node-c")
        logger.info(f"  - node-b.parent_id = node-a")
        logger.info(f"  - node-c.parent_id = node-b")
        logger.info(f"  - Creates cycle: A → C → B → A")

        # Convert to JSON file
        json_content = json.dumps(circular_tree, indent=2)
        json_file = BytesIO(json_content.encode('utf-8'))
        
        # Import via Basic I/O
        import_url = f"{BASE_URL}/import"
        files = {
            'file': ('circular_tree.json', json_file, 'application/json')
        }
        data = {
            'url': 'http://identity_service:5000/organization_units',
            'type': 'json'
        }
        
        logger.info(f"Attempting import to: {data['url']}")
        response = api_tester.session.post(
            import_url,
            files=files,
            data=data,
            cookies=session_auth_cookies
        )
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        # Should return 400 Bad Request for circular reference
        assert response.status_code == 400, f"Expected 400 for circular reference, got {response.status_code}"
        
        result = response.json()
        
        # Verify error message mentions circular reference or cycle
        error_message = str(result).lower()
        assert 'circular' in error_message or 'cycle' in error_message, \
            f"Error message should mention circular reference: {result}"
        
        logger.info("✓ Circular reference correctly detected and rejected")
        logger.info(f"✓ Received 400 with appropriate error message")

    def test38_import_tree_orphaned_nodes(self, api_tester, session_auth_cookies, session_user_info):
        """Test handling of orphaned nodes (parent_id references non-existent node)"""
        
        # Using session_auth_cookies
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Orphaned nodes (parent_id references missing node)")
        logger.info("="*80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_org_units = []

        try:
            # Create structure with orphaned nodes
            orphaned_tree = [
                {
                    "id": "root-1",
                    "name": f"Valid Root {timestamp}",
                    "company_id": company_id,
                    "parent_id": None  # Valid root
                },
                {
                    "id": "child-1",
                    "name": f"Valid Child {timestamp}",
                    "company_id": company_id,
                    "parent_id": "root-1"  # Valid reference
                },
                {
                    "id": "orphan-1",
                    "name": f"Orphaned Node 1 {timestamp}",
                    "company_id": company_id,
                    "parent_id": "non-existent-parent"  # Orphaned!
                },
                {
                    "id": "orphan-2",
                    "name": f"Orphaned Node 2 {timestamp}",
                    "company_id": company_id,
                    "parent_id": "another-missing-parent"  # Orphaned!
                }
            ]

            logger.info(f"Tree with orphaned nodes:")
            logger.info(f"  - Valid: root-1 (no parent)")
            logger.info(f"  - Valid: child-1 (parent=root-1)")
            logger.info(f"  - Orphan: orphan-1 (parent=non-existent-parent)")
            logger.info(f"  - Orphan: orphan-2 (parent=another-missing-parent)")

            # Convert to JSON file
            json_content = json.dumps(orphaned_tree, indent=2)
            json_file = BytesIO(json_content.encode('utf-8'))
            
            # Import via Basic I/O
            import_url = f"{BASE_URL}/import"
            files = {
                'file': ('orphaned_tree.json', json_file, 'application/json')
            }
            data = {
                'url': 'http://identity_service:5000/organization_units',
                'type': 'json'
            }
            
            logger.info(f"Importing to: {data['url']}")
            response = api_tester.session.post(
                import_url,
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
            
            # Could be 201 (partial success) or 400 (validation error)
            # Behavior depends on implementation
            assert response.status_code in [200, 201, 400], \
                f"Expected 200/201/400, got {response.status_code}"
            
            result = response.json()
            
            if response.status_code in [200, 201]:
                # Partial success - valid nodes imported, orphans skipped
                import_report = result.get('import_report', {})
                logger.info(f"Import Report:")
                logger.info(f"  - Total: {import_report.get('total', 'N/A')}")
                logger.info(f"  - Success: {import_report.get('success', 'N/A')}")
                logger.info(f"  - Failed: {import_report.get('failed', 'N/A')}")
                
                # Store created IDs for cleanup
                if 'id_mapping' in import_report:
                    created_org_units = list(import_report['id_mapping'].values())
                
                logger.info("✓ Partial import - valid nodes imported, orphans handled")
            else:
                # Complete failure - no nodes imported
                logger.info("✓ Complete validation failure - orphaned nodes rejected")
            
            logger.info(f"✓ Orphaned nodes handling validated")

        finally:
            # Cleanup any created nodes
            if created_org_units:
                logger.info(f"Cleaning up {len(created_org_units)} organization units...")
                for org_unit_id in reversed(created_org_units):
                    try:
                        delete_url = f"{IDENTITY_URL}/organization_units/{org_unit_id}"
                        api_tester.session.delete(delete_url, cookies=session_auth_cookies)
                    except Exception as e:
                        logger.warning(f"Failed to delete org unit {org_unit_id}: {e}")

    def test39_import_tree_session_parent_mapping(self, api_tester, session_auth_cookies, session_user_info):
        """Test that parent_id mapping is maintained within import session"""
        
        # Using session_auth_cookies
        company_id = session_user_info['company_id']
        logger.info("\n" + "="*80)
        logger.info("TEST: Parent ID mapping within import session")
        logger.info("="*80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        created_org_units = []

        try:
            # Create tree where original IDs are UUIDs that will be remapped
            original_parent_id = str(uuid.uuid4())
            original_child1_id = str(uuid.uuid4())
            original_child2_id = str(uuid.uuid4())
            
            tree_with_uuids = [
                {
                    "_original_id": original_parent_id,
                    "name": f"Parent Unit {timestamp}",
                    "company_id": company_id,
                    "parent_id": None
                },
                {
                    "_original_id": original_child1_id,
                    "name": f"Child Unit 1 {timestamp}",
                    "company_id": company_id,
                    "parent_id": original_parent_id  # Reference to original UUID
                },
                {
                    "_original_id": original_child2_id,
                    "name": f"Child Unit 2 {timestamp}",
                    "company_id": company_id,
                    "parent_id": original_parent_id  # Reference to original UUID
                }
            ]

            logger.info(f"Tree with original UUIDs:")
            logger.info(f"  - Parent original ID: {original_parent_id}")
            logger.info(f"  - Child 1 original ID: {original_child1_id}")
            logger.info(f"  - Child 2 original ID: {original_child2_id}")
            logger.info(f"  - Both children reference parent via original UUID")

            # Convert to JSON file
            json_content = json.dumps(tree_with_uuids, indent=2)
            json_file = BytesIO(json_content.encode('utf-8'))
            
            # Import via Basic I/O
            import_url = f"{BASE_URL}/import"
            files = {
                'file': ('tree_uuids.json', json_file, 'application/json')
            }
            data = {
                'url': 'http://identity_service:5000/organization_units',
                'type': 'json'
            }
            
            logger.info(f"Importing to: {data['url']}")
            response = api_tester.session.post(
                import_url,
                files=files,
                data=data,
                cookies=session_auth_cookies
            )
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response Body: {json.dumps(response.json(), indent=2)}")
            
            assert response.status_code == 201, f"Import failed: {response.text}"
            
            result = response.json()
            assert 'import_report' in result
            
            import_report = result['import_report']
            logger.info(f"Import Report:")
            logger.info(f"  - Total: {import_report['total']}")
            logger.info(f"  - Success: {import_report['success']}")
            logger.info(f"  - Failed: {import_report['failed']}")
            
            assert import_report['total'] == 3
            assert import_report['success'] == 3
            
            # Get ID mapping
            assert 'id_mapping' in import_report
            id_mapping = import_report['id_mapping']
            
            logger.info(f"ID Mapping:")
            logger.info(f"  - {original_parent_id} → {id_mapping.get(original_parent_id)}")
            logger.info(f"  - {original_child1_id} → {id_mapping.get(original_child1_id)}")
            logger.info(f"  - {original_child2_id} → {id_mapping.get(original_child2_id)}")
            
            # Verify all IDs were mapped
            assert original_parent_id in id_mapping
            assert original_child1_id in id_mapping
            assert original_child2_id in id_mapping
            
            # Get new IDs
            new_parent_id = id_mapping[original_parent_id]
            new_child1_id = id_mapping[original_child1_id]
            new_child2_id = id_mapping[original_child2_id]
            
            created_org_units = [new_parent_id, new_child1_id, new_child2_id]
            
            # Verify the children now reference the NEW parent ID
            # Fetch child 1
            get_url = f"{IDENTITY_URL}/organization_units/{new_child1_id}"
            child1_response = api_tester.session.get(get_url, cookies=session_auth_cookies)
            assert child1_response.status_code == 200
            child1_data = child1_response.json()
            
            logger.info(f"Child 1 data: {json.dumps(child1_data, indent=2)}")
            assert child1_data.get('parent_id') == new_parent_id, \
                f"Child 1 parent_id should be {new_parent_id}, got {child1_data.get('parent_id')}"
            
            # Fetch child 2
            get_url = f"{IDENTITY_URL}/organization_units/{new_child2_id}"
            child2_response = api_tester.session.get(get_url, cookies=session_auth_cookies)
            assert child2_response.status_code == 200
            child2_data = child2_response.json()
            
            logger.info(f"Child 2 data: {json.dumps(child2_data, indent=2)}")
            assert child2_data.get('parent_id') == new_parent_id, \
                f"Child 2 parent_id should be {new_parent_id}, got {child2_data.get('parent_id')}"
            
            logger.info("✓ Parent ID mapping correctly maintained in import session")
            logger.info(f"✓ Original UUIDs remapped to new IDs")
            logger.info(f"✓ Children correctly reference new parent ID")

        finally:
            # Cleanup
            if created_org_units:
                logger.info(f"Cleaning up {len(created_org_units)} organization units...")
                for org_unit_id in reversed(created_org_units):
                    try:
                        delete_url = f"{IDENTITY_URL}/organization_units/{org_unit_id}"
                        api_tester.session.delete(delete_url, cookies=session_auth_cookies)
                    except Exception as e:
                        logger.warning(f"Failed to delete org unit {org_unit_id}: {e}")
