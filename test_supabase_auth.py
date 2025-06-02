#!/usr/bin/env python3
"""
Test Script for Supabase Authentication Integration
Tests login, account loading, and session management
"""

from Views.auth import supabase_auth
from services.supabase_auth_service import get_auth_service
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import Supabase auth components

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("SupabaseAuthTest")


async def test_supabase_connection():
    """Test basic Supabase connection"""
    logger.info("🔗 Testing Supabase connection...")

    try:
        auth_service = await get_auth_service()
        connected = await auth_service.test_connection()

        if connected:
            logger.info("✅ Supabase connection successful")
            return True
        else:
            logger.error("❌ Supabase connection failed")
            return False

    except Exception as e:
        logger.error(f"❌ Supabase connection error: {e}")
        return False


async def test_user_login():
    """Test user login functionality"""
    logger.info("🔐 Testing user login...")

    # Test credentials (replace with actual test user)
    test_email = "test@example.com"
    test_password = "testpassword"

    try:
        success, message = await supabase_auth.login(test_email, test_password)

        if success:
            logger.info(f"✅ Login successful: {message}")

            # Test getting current user
            user_id = await supabase_auth.get_current_user_id()
            if user_id:
                logger.info(f"✅ Current user ID: {user_id}")
            else:
                logger.warning("⚠️ Could not get current user ID")

            return True
        else:
            logger.error(f"❌ Login failed: {message}")
            return False

    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        return False


async def test_account_loading():
    """Test loading user accounts"""
    logger.info("📊 Testing account loading...")

    try:
        # Get current user ID
        user_id = await supabase_auth.get_current_user_id()

        if not user_id:
            logger.error("❌ No authenticated user for account loading test")
            return False

        # Load accounts
        accounts = await supabase_auth.get_user_accounts(user_id)

        logger.info(f"✅ Loaded {len(accounts)} accounts for user {user_id}")

        for i, account in enumerate(accounts):
            logger.info(f"  Account {i+1}:")
            logger.info(f"    ID: {account.get('id')}")
            logger.info(f"    Name: {account.get('name')}")
            logger.info(f"    Account Number: {account.get('account_number')}")
            logger.info(f"    Broker: {account.get('broker')}")
            logger.info(f"    Status: {account.get('status')}")
            logger.info(f"    Balance: {account.get('balance')}")

        return True

    except Exception as e:
        logger.error(f"❌ Account loading error: {e}")
        return False


async def test_session_management():
    """Test session management"""
    logger.info("🔄 Testing session management...")

    try:
        # Check if session is valid
        valid = await supabase_auth.is_authenticated()

        if valid:
            logger.info("✅ Session is valid")
        else:
            logger.warning("⚠️ No valid session")

        return True

    except Exception as e:
        logger.error(f"❌ Session management error: {e}")
        return False


async def test_logout():
    """Test user logout"""
    logger.info("🚪 Testing logout...")

    try:
        success, message = await supabase_auth.logout()

        if success:
            logger.info(f"✅ Logout successful: {message}")

            # Verify no authenticated user
            authenticated = await supabase_auth.is_authenticated()
            if not authenticated:
                logger.info("✅ No authenticated user after logout")
            else:
                logger.warning(
                    "⚠️ User still appears authenticated after logout")

            return True
        else:
            logger.error(f"❌ Logout failed: {message}")
            return False

    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        return False


async def run_all_tests():
    """Run all authentication tests"""
    logger.info("🚀 Starting Supabase Authentication Tests")
    logger.info("=" * 60)

    tests = [
        ("Connection Test", test_supabase_connection),
        ("User Login Test", test_user_login),
        ("Account Loading Test", test_account_loading),
        ("Session Management Test", test_session_management),
        ("Logout Test", test_logout),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name}...")
        try:
            result = await test_func()
            if result:
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} ERROR: {e}")

    logger.info("\n" + "=" * 60)
    logger.info(f"🏁 Test Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info(
            "🎉 All tests passed! Supabase authentication is working correctly.")
        return True
    else:
        logger.error(
            f"💥 {total - passed} tests failed. Please check configuration.")
        return False


async def main():
    """Main test function"""
    # Check environment variables
    required_env_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(
            f"❌ Missing required environment variables: {missing_vars}")
        logger.error("Please set up your .env file with Supabase credentials")
        return False

    logger.info(f"🔧 Supabase URL: {os.getenv('SUPABASE_URL')}")
    logger.info(f"🔧 Anon Key: {os.getenv('SUPABASE_ANON_KEY')[:10]}...")

    # Run tests
    success = await run_all_tests()

    # Cleanup
    try:
        await supabase_auth.cleanup_auth()
        logger.info("🧹 Cleanup completed")
    except Exception as e:
        logger.error(f"⚠️ Cleanup error: {e}")

    return success


if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("📋 Environment variables loaded from .env file")
    except ImportError:
        logger.warning(
            "⚠️ python-dotenv not available, using system environment variables")
    except Exception as e:
        logger.warning(f"⚠️ Could not load .env file: {e}")

    # Run tests
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Test runner error: {e}")
        sys.exit(1)
