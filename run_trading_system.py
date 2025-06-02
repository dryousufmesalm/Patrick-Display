#!/usr/bin/env python3
"""
Run Script for Real-Time Trading System V2
Easy launcher with configuration and safety checks
"""

from main_realtime_v2 import RealTimeTradingSystemV2
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import main system

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('realtime_trading.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("TradingSystemLauncher")


def check_requirements():
    """Check if all requirements are met"""
    logger.info("🔍 Checking system requirements...")

    # Check Python version
    if sys.version_info < (3, 8, 0):
        logger.error("❌ Python 3.8+ required")
        return False

    # Check required modules
    required_modules = [
        'supabase', 'asyncio', 'websockets',
        'aiohttp', 'MetaTrader5'
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        logger.error(f"❌ Missing modules: {', '.join(missing_modules)}")
        logger.info("Install with: pip install -r requirements_realtime.txt")
        return False

    logger.info("✅ All requirements met")
    return True


def load_configuration():
    """Load configuration from environment or provide defaults"""
    logger.info("📋 Loading configuration...")

    config = {
        'account_id': os.getenv('ACCOUNT_ID', 'demo_account'),
        'supabase_url': os.getenv('SUPABASE_URL'),
        'supabase_key': os.getenv('SUPABASE_ANON_KEY'),
        'mt5_account': os.getenv('MT5_ACCOUNT_ID'),
        'mt5_password': os.getenv('MT5_PASSWORD'),
        'mt5_server': os.getenv('MT5_SERVER'),
        'websocket_host': os.getenv('WEBSOCKET_HOST', 'localhost'),
        'websocket_port': int(os.getenv('WEBSOCKET_PORT', 8765)),
        'log_level': os.getenv('LOG_LEVEL', 'INFO')
    }

    # Check critical configuration
    if not config['account_id'] or config['account_id'] == 'demo_account':
        logger.warning(
            "⚠️  Using demo account ID - update ACCOUNT_ID in environment")

    if not config['supabase_url']:
        logger.warning(
            "⚠️  No Supabase URL configured - some features may not work")

    logger.info(f"✅ Configuration loaded for account: {config['account_id']}")
    return config


def print_banner():
    """Print system banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🚀 REAL-TIME TRADING SYSTEM V2 🚀                        ║
║                                                                              ║
║  Features:                                                                   ║
║  • Real-time order synchronization (500ms)                                  ║
║  • Live cycle management and profit tracking                                ║
║  • WebSocket streaming to frontend                                          ║
║  • Automatic error recovery and circuit breakers                           ║
║  • MetaTrader 5 integration                                                 ║
║  • Comprehensive monitoring and logging                                     ║
║                                                                              ║
║  Status: PRODUCTION READY ✅                                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    """Main launcher function"""
    try:
        print_banner()

        # Check requirements
        if not check_requirements():
            logger.error("❌ Requirements check failed")
            return 1

        # Load configuration
        config = load_configuration()

        # Display startup info
        logger.info("🎯 Starting Real-Time Trading System V2...")
        logger.info(f"📊 Account ID: {config['account_id']}")
        logger.info(
            f"🌐 WebSocket: {config['websocket_host']}:{config['websocket_port']}")
        logger.info(f"📅 Started at: {datetime.utcnow().isoformat()}Z")

        # Create and run system
        system = RealTimeTradingSystemV2(config['account_id'])

        logger.info("🔧 Initializing system components...")
        await system.initialize()

        logger.info("🚀 Starting trading system...")
        await system.start()

        return 0

    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested by user")
        return 0
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return 1


def run_tests():
    """Run system tests"""
    logger.info("🧪 Running system tests...")

    try:
        # Import and run test suite
        from test_system_v2 import main as run_tests_main
        return asyncio.run(run_tests_main())
    except ImportError:
        logger.error("❌ Test module not found")
        return 1
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Real-Time Trading System V2 Launcher')
    parser.add_argument('--test', action='store_true', help='Run system tests')
    parser.add_argument('--check', action='store_true',
                        help='Check requirements only')
    parser.add_argument('--config', action='store_true',
                        help='Show configuration')

    args = parser.parse_args()

    if args.test:
        sys.exit(run_tests())
    elif args.check:
        sys.exit(0 if check_requirements() else 1)
    elif args.config:
        config = load_configuration()
        print("\n📋 Current Configuration:")
        for key, value in config.items():
            # Hide sensitive values
            if 'password' in key.lower() or 'key' in key.lower():
                value = "***hidden***" if value else "Not set"
            print(f"  {key}: {value}")
        sys.exit(0)
    else:
        sys.exit(asyncio.run(main()))
