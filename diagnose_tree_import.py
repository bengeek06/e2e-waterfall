#!/usr/bin/env python3
"""
Diagnostic script to verify Basic I/O API tree import functionality
Tests if parent_id references are correctly remapped during import
"""
import requests
import json
from io import BytesIO
import uuid
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    # Config
    base_url = "http://localhost:3000"
    
    # Login
    session = requests.Session()
    session.verify = False
    login_response = session.post(
        f"{base_url}/api/auth/login",
        json={"email": "testuser@example.com", "password": "securepassword"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    print(f"✅ Login successful")
    
    # Get company_id using cookies explicitly
    auth_cookies = {
        'access_token': login_response.cookies.get('access_token'),
        'refresh_token': login_response.cookies.get('refresh_token')
    }
    
    verify_response = session.get(f"{base_url}/api/auth/verify", cookies=auth_cookies)
    user_info = verify_response.json()
    
    company_id = user_info.get('company_id') or user_info.get('data', {}).get('company_id')
    
    if not company_id:
        print(f"❌ Could not get company_id from: {user_info}")
        return True
    
    print(f"✅ Company ID: {company_id}")
    
    # Create simple tree with parent-child relationship
    parent_uuid = str(uuid.uuid4())
    child_uuid = str(uuid.uuid4())
    
    tree_data = [
        {
            "_original_id": parent_uuid,
            "name": "DIAG Parent Test",
            "company_id": company_id,
            "parent_id": None
        },
        {
            "_original_id": child_uuid,
            "name": "DIAG Child Test",
            "company_id": company_id,
            "parent_id": parent_uuid  # ← Should be remapped to new parent UUID
        }
    ]
    
    print(f"\n{'='*80}")
    print(f"DIAGNOSTIC: Testing Basic I/O tree import with parent_id remapping")
    print(f"{'='*80}")
    print(f"\n📤 Data sent to Basic I/O:")
    print(f"  Parent: _original_id={parent_uuid[:8]}..., parent_id=None")
    print(f"  Child:  _original_id={child_uuid[:8]}..., parent_id={parent_uuid[:8]}...")
    print(f"\n🔍 Expected behavior:")
    print(f"  1. Parent imported first → receives new UUID (e.g., new-parent-uuid)")
    print(f"  2. Child imported second → parent_id should be REMAPPED to new-parent-uuid")
    print(f"  3. NOT the original UUID {parent_uuid[:8]}...")
    
    # Import via Basic I/O
    json_content = json.dumps(tree_data, indent=2)
    json_file = BytesIO(json_content.encode('utf-8'))
    
    import_response = session.post(
        f"{base_url}/api/basic-io/import",
        files={'file': ('diag_tree.json', json_file, 'application/json')},
        data={
            'url': 'http://identity_service:5000/organization_units',
            'type': 'json'
        },
        cookies=auth_cookies
    )
    
    print(f"\n📥 Basic I/O Response: {import_response.status_code}")
    
    if import_response.status_code not in [200, 201, 207]:
        print(f"❌ Import failed: {import_response.text}")
        return
    
    result = import_response.json()
    import_report = result.get('import_report', {})
    
    print(f"\n📊 Import Report:")
    print(f"  Total: {import_report.get('total', 0)}")
    print(f"  Success: {import_report.get('success', 0)}")
    print(f"  Failed: {import_report.get('failed', 0)}")
    
    id_mapping = import_report.get('id_mapping', {})
    
    if not id_mapping:
        print(f"\n❌ ERROR: No id_mapping in response!")
        print(f"Full response: {json.dumps(result, indent=2)}")
        return
    
    print(f"\n🔄 UUID Mapping:")
    new_parent_id = id_mapping.get(parent_uuid)
    new_child_id = id_mapping.get(child_uuid)
    
    if new_parent_id:
        print(f"  Parent: {parent_uuid[:8]}... → {new_parent_id[:8]}...")
    else:
        print(f"  Parent: {parent_uuid[:8]}... → ❌ NOT IN MAPPING")
    
    if new_child_id:
        print(f"  Child:  {child_uuid[:8]}... → {new_child_id[:8]}...")
    else:
        print(f"  Child:  {child_uuid[:8]}... → ❌ NOT IN MAPPING")
    
    # Verify the child's parent_id in the database
    if new_child_id:
        print(f"\n🔍 Verifying child record in database...")
        child_response = session.get(
            f"{base_url}/api/identity/organization_units/{new_child_id}",
            cookies=auth_cookies
        )
        
        if child_response.status_code == 200:
            child_data = child_response.json()
            actual_parent_id = child_data.get('parent_id')
            
            print(f"\n📋 Child record in database:")
            print(f"  ID: {new_child_id}")
            print(f"  Name: {child_data.get('name')}")
            print(f"  parent_id: {actual_parent_id}")
            
            print(f"\n✅ Expected parent_id: {new_parent_id}")
            print(f"{'✅' if actual_parent_id == new_parent_id else '❌'} Actual parent_id:   {actual_parent_id}")
            
            # Determine result
            if actual_parent_id == new_parent_id:
                print(f"\n{'='*80}")
                print(f"✅ SUCCESS: parent_id correctly remapped!")
                print(f"{'='*80}")
                bug_detected = False
            elif actual_parent_id == parent_uuid:
                print(f"\n{'='*80}")
                print(f"❌ BUG DETECTED: parent_id NOT remapped!")
                print(f"❌ Child still references ORIGINAL UUID instead of new UUID")
                print(f"{'='*80}")
                bug_detected = True
            elif actual_parent_id is None:
                print(f"\n{'='*80}")
                print(f"❌ BUG DETECTED: parent_id is NULL!")
                print(f"❌ Parent reference was lost during import")
                print(f"{'='*80}")
                bug_detected = True
            else:
                print(f"\n{'='*80}")
                print(f"❌ BUG DETECTED: parent_id has unexpected value!")
                print(f"❌ Not the original UUID, not the new UUID, something else")
                print(f"{'='*80}")
                bug_detected = True
        else:
            print(f"❌ Failed to fetch child record: {child_response.status_code}")
            bug_detected = True
    else:
        print(f"\n❌ Cannot verify - child not in mapping")
        bug_detected = True
    
    # Cleanup
    print(f"\n🧹 Cleanup...")
    if new_child_id:
        delete_child = session.delete(
            f"{base_url}/api/identity/organization_units/{new_child_id}",
            cookies=auth_cookies
        )
        print(f"  Child deleted: {delete_child.status_code}")
    if new_parent_id:
        delete_parent = session.delete(
            f"{base_url}/api/identity/organization_units/{new_parent_id}",
            cookies=auth_cookies
        )
        print(f"  Parent deleted: {delete_parent.status_code}")
    
    return bug_detected

if __name__ == '__main__':
    import sys
    bug_detected = main()
    sys.exit(1 if bug_detected else 0)
