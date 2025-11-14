#!/usr/bin/env python3
"""
Standalone script to generate test data (organization structure with positions).

This script creates a complete organizational structure with:
- Direction Générale (root)
- 3 Competence Centers
- 4 Business Lines
- Multiple levels of sub-departments
- Positions for each department

Usage:
    python generate_test_data.py
    
Or with custom Python environment:
    /path/to/venv/bin/python generate_test_data.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.data_generators import DataGenerator
from conftest import get_service_logger
import requests

logger = get_service_logger('generate_data')

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env.test'))


def main():
    """Generate test data."""
    
    # Configuration from .env.test
    base_url = os.getenv('WEB_URL')
    login = os.getenv('LOGIN')
    password = os.getenv('PASSWORD')
    
    logger.info("=" * 80)
    logger.info("🚀 Generating Test Data - Organization Structure")
    logger.info("=" * 80)
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Login: {login}")
    
    # Step 1: Authenticate
    logger.info("\n🔐 Step 1: Authenticating...")
    session = requests.Session()
    session.verify = False  # Disable SSL verification for local testing
    
    login_response = session.post(
        f"{base_url}/api/auth/login",
        json={"email": login, "password": password}
    )
    
    if login_response.status_code != 200:
        logger.error(f"❌ Login failed: {login_response.status_code} - {login_response.text}")
        return 1
    
    cookies = {
        'access_token': login_response.cookies.get('access_token'),
        'refresh_token': login_response.cookies.get('refresh_token')
    }
    
    # Get company_id
    verify_response = session.get(
        f"{base_url}/api/auth/verify",
        cookies=cookies
    )
    
    if verify_response.status_code != 200:
        logger.error(f"❌ Verify failed: {verify_response.status_code}")
        return 1
    
    company_id = verify_response.json()['company_id']
    logger.info(f"✅ Authenticated - Company ID: {company_id}")
    
    # Step 2: Initialize DataGenerator
    logger.info("\n🔧 Step 2: Initializing DataGenerator...")
    generator = DataGenerator(
        base_url=base_url,
        cookies=cookies,
        company_id=company_id,
        locale='fr_FR'
    )
    logger.info("✅ DataGenerator initialized")
    
    # Step 3: Generate organizational structure
    logger.info("\n🏢 Step 3: Generating organizational structure...")
    logger.info("-" * 80)
    
    try:
        org_data = generator.generate_organization_structure()
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 GENERATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✅ Organization Units created: {len(org_data['organization_units'])}")
        logger.info(f"✅ Positions created: {len(org_data['positions'])}")
        logger.info(f"✅ Hierarchy levels: {len(org_data['hierarchy'])} parents")
        
        # Show some sample positions
        logger.info("\n📋 Sample positions created:")
        for i, pos in enumerate(org_data['positions'][:10]):
            logger.info(f"  • {pos['title']}")
        
        if len(org_data['positions']) > 10:
            logger.info(f"  ... and {len(org_data['positions']) - 10} more positions")
        
        # Show organization structure
        logger.info("\n🌳 Organization structure (root level):")
        root_units = [u for u in org_data['organization_units'] if not u.get('parent_id')]
        for unit in root_units:
            children_count = len(org_data['hierarchy'].get(unit['id'], []))
            logger.info(f"  • {unit['name']} ({children_count} direct children)")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ SUCCESS - Test data generated!")
        logger.info("=" * 80)
        logger.info("\n💡 To clean up, run: python cleanup_test_data.py")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ GENERATION FAILED: {e}")
        logger.info("\n🧹 Attempting cleanup due to failure...")
        try:
            generator.cleanup()
            logger.info("✅ Cleanup completed")
        except Exception as cleanup_error:
            logger.error(f"⚠️ Cleanup failed: {cleanup_error}")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
