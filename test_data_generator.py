"""
Tests for DataGenerator - Organization Structure Generation

This script tests the data generator by creating a complete organizational
structure with positions.

Run with pytest:
    pytest test_data_generator.py -v -s
"""

import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.data_generators import DataGenerator
from conftest import get_service_logger

logger = get_service_logger('test_data_gen')


class TestDataGenerator:
    """Test suite for DataGenerator class"""
    
    # Shared generator instance and data
    generator = None
    org_data = None
    
    def test01_generate_organization_structure(self, api_tester, session_auth_cookies, session_user_info):
        """Test generating organizational structure with positions (without cleanup)."""
        
        assert session_auth_cookies is not None, "No auth cookies available"
        assert session_user_info is not None, "No user info available"
        
        logger.info("=" * 80)
        logger.info("🧪 TEST 1: Generate Organization Structure (No Cleanup)")
        logger.info("=" * 80)
        
        # Get configuration from fixtures
        base_url = api_tester.base_url
        cookies_dict = session_auth_cookies
        company_id = session_user_info['company_id']
        
        logger.info("✅ Using configuration from fixtures:")
        logger.info(f"   Base URL: {base_url}")
        logger.info(f"   Company ID: {company_id}")
        
        # Initialize DataGenerator
        logger.info("\n🔧 Initializing DataGenerator...")
        TestDataGenerator.generator = DataGenerator(
            base_url=base_url,
            cookies=cookies_dict,
            company_id=company_id,
            locale='fr_FR'
        )
        logger.info("✅ DataGenerator initialized")
        
        # Generate organizational structure
        logger.info("\n🏢 Generating organizational structure...")
        logger.info("-" * 80)
        
        try:
            TestDataGenerator.org_data = TestDataGenerator.generator.generate_organization_structure()
            
            logger.info("\n" + "=" * 80)
            logger.info("📊 GENERATION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"✅ Organization Units created: {len(TestDataGenerator.org_data['organization_units'])}")
            logger.info(f"✅ Positions created: {len(TestDataGenerator.org_data['positions'])}")
            logger.info(f"✅ Hierarchy levels: {len(TestDataGenerator.org_data['hierarchy'])} parents")
            
            # Assertions
            assert len(TestDataGenerator.org_data['organization_units']) > 0, "No organization units created"
            assert len(TestDataGenerator.org_data['positions']) > 0, "No positions created"
            
            # Show some sample positions
            logger.info("\n📋 Sample positions created:")
            for i, pos in enumerate(TestDataGenerator.org_data['positions'][:10]):
                logger.info(f"  • {pos['title']}")
            
            if len(TestDataGenerator.org_data['positions']) > 10:
                logger.info(f"  ... and {len(TestDataGenerator.org_data['positions']) - 10} more positions")
            
            # Show organization structure
            logger.info("\n🌳 Organization structure (root level):")
            root_units = [u for u in TestDataGenerator.org_data['organization_units'] if not u.get('parent_id')]
            for unit in root_units:
                children_count = len(TestDataGenerator.org_data['hierarchy'].get(unit['id'], []))
                logger.info(f"  • {unit['name']} ({children_count} direct children)")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ TEST 1 PASSED - Data generated and ready for exploration!")
            logger.info("=" * 80)
            logger.info("\n⚠️  Data NOT cleaned up - run test02_cleanup to delete all data")
            
        except Exception as e:
            logger.error(f"\n❌ TEST FAILED: {e}")
            # Cleanup on failure
            logger.info("\n🧹 Cleaning up due to failure...")
            try:
                if TestDataGenerator.generator:
                    TestDataGenerator.generator.cleanup()
                    logger.info("✅ Cleanup completed")
            except Exception as cleanup_error:
                logger.error(f"⚠️ Cleanup failed: {cleanup_error}")
            raise
    
    def test02_cleanup(self, api_tester, session_auth_cookies, session_user_info):
        """Test cleanup of generated data."""
        
        logger.info("\n" + "=" * 80)
        logger.info("� TEST 2: Cleanup Generated Data")
        logger.info("=" * 80)
        
        if TestDataGenerator.generator is None:
            logger.warning("⚠️ No generator found - nothing to clean up")
            logger.info("Run test01_generate_organization_structure first to generate data")
            pytest.skip("No data to clean up")
        
        if TestDataGenerator.org_data is None:
            logger.warning("⚠️ No org data found - nothing to clean up")
            pytest.skip("No data to clean up")
        
        logger.info("📊 Data to clean up:")
        logger.info(f"   • {len(TestDataGenerator.org_data['organization_units'])} organization units")
        logger.info(f"   • {len(TestDataGenerator.org_data['positions'])} positions")
        
        try:
            logger.info("\n🧹 Starting cleanup...")
            TestDataGenerator.generator.cleanup()
            logger.info("\n" + "=" * 80)
            logger.info("✅ TEST 2 PASSED - All data cleaned up successfully!")
            logger.info("=" * 80)
            
            # Reset shared data
            TestDataGenerator.generator = None
            TestDataGenerator.org_data = None
            
        except Exception as e:
            logger.error(f"\n❌ CLEANUP FAILED: {e}")
            raise

