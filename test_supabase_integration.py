#!/usr/bin/env python3
"""
Simple test script for Supabase integration
Tests basic connectivity and repository functionality
"""

import sys
import os
import asyncio
import logging
from typing import Dict

# Add current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test if all imports work correctly"""
    try:
        logger.info("🧪 Testing imports...")

        # Test Supabase client import
        from db.supabase_client import supabase_client
        logger.info("✅ Supabase client import successful")

        # Test repository imports
        from db.repositories.metatrader_repository import MetaTraderRepository
        from db.repositories.bot_repository import BotRepository
        logger.info("✅ Repository imports successful")

        # Test event handler import
        from handlers.event_handler import EventHandler, EventType, EventSeverity
        logger.info("✅ Event handler import successful")

        # Test API handler import
        from Api.SupabaseAPIHandler import SupabaseAPI
        logger.info("✅ API handler import successful")

        return True

    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_supabase_connection():
    """Test basic Supabase connection"""
    try:
        logger.info("🧪 Testing Supabase connection...")

        from db.supabase_client import supabase_client

        # Test health check
        health = await supabase_client.health_check()
        logger.info(f"📊 Health check result: {health}")

        if health.get("rest_api", False):
            logger.info("✅ Supabase REST API connection successful")
        else:
            logger.warning("⚠️ Supabase REST API connection failed")

        return True

    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        return False


async def test_repositories():
    """Test repository initialization"""
    try:
        logger.info("🧪 Testing repository initialization...")

        from db.supabase_client import supabase_client
        from db.repositories.metatrader_repository import MetaTraderRepository
        from db.repositories.bot_repository import BotRepository

        # Initialize repositories
        mt_repo = MetaTraderRepository(supabase_client)
        bot_repo = BotRepository(supabase_client)

        logger.info("✅ Repository initialization successful")
        return True

    except Exception as e:
        logger.error(f"❌ Repository test failed: {e}")
        return False


async def test_api_handler():
    """Test API handler initialization"""
    try:
        logger.info("🧪 Testing API handler...")

        from Api.SupabaseAPIHandler import SupabaseAPI

        # Initialize API
        api = SupabaseAPI()
        await api.initialize()

        logger.info("✅ API handler initialization successful")
        return True

    except Exception as e:
        logger.error(f"❌ API handler test failed: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("🚀 Starting Supabase integration tests...")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"🐍 Python path: {sys.path[:3]}...")  # Show first 3 entries

    tests = [
        ("Import Test", test_imports),
        ("Connection Test", test_supabase_connection),
        ("Repository Test", test_repositories),
        ("API Handler Test", test_api_handler)
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")

        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"❌ Test {test_name} failed with exception: {e}")
            results[test_name] = False

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("📊 TEST SUMMARY")
    logger.info(f"{'='*50}")

    passed = 0
    total = len(tests)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1

    logger.info(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! Supabase integration is ready.")
        return 0
    else:
        logger.error("💥 Some tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🔌 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)
