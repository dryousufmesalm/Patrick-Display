#!/usr/bin/env python3
"""
Patrick Display - Supabase Integration
Main application demonstrating integration with Peaceful Investment database

This replaces the PocketBase integration with direct Supabase connection
while maintaining all existing functionality.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Any

# Import the new Supabase-based components
from services.trading_service import trading_service
from handlers.event_handler import EventType, EventSeverity
from db.repositories.metatrader_repository import MetaTraderRepository
from db.repositories.bot_repository import BotRepository
from db.supabase_client import supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('patrick_display.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class PatrickDisplayApp:
    """
    Main Patrick Display application with Supabase integration
    """

    def __init__(self):
        self.trading_service = trading_service
        self.is_running = False
        self.shutdown_event = asyncio.Event()

    async def startup(self):
        """Initialize the application"""
        try:
            logger.info(
                "🚀 Starting Patrick Display with Supabase integration...")

            # Initialize trading service
            await self.trading_service.initialize()

            # Set up signal handlers for graceful shutdown
            self.setup_signal_handlers()

            self.is_running = True
            logger.info("✅ Patrick Display started successfully")

            # Perform initial health check
            health = await self.trading_service.health_check()
            logger.info(f"📊 System Health: {health}")

        except Exception as e:
            logger.error(f"❌ Failed to start Patrick Display: {e}")
            raise

    async def shutdown(self):
        """Gracefully shutdown the application"""
        try:
            logger.info("🛑 Shutting down Patrick Display...")
            self.is_running = False

            # Shutdown trading service
            await self.trading_service.shutdown()

            # Set shutdown event
            self.shutdown_event.set()

            logger.info("✅ Patrick Display shutdown completed")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📨 Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run_main_loop(self):
        """Main application loop"""
        try:
            logger.info("🔄 Starting main application loop...")

            while self.is_running:
                try:
                    # Perform periodic tasks
                    await self.periodic_tasks()

                    # Wait for shutdown event or timeout
                    try:
                        await asyncio.wait_for(self.shutdown_event.wait(), timeout=30.0)
                        break  # Shutdown requested
                    except asyncio.TimeoutError:
                        continue  # Continue main loop

                except Exception as e:
                    logger.error(f"❌ Error in main loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying

            logger.info("🏁 Main loop completed")
        except Exception as e:
            logger.error(f"❌ Fatal error in main loop: {e}")
            raise

    async def periodic_tasks(self):
        """Perform periodic maintenance tasks"""
        try:
            # Sync account data every 30 seconds
            current_time = datetime.utcnow()

            # Initialize last_sync if not set
            if not hasattr(self, '_last_sync'):
                self._last_sync = current_time

            # Example: Sync all active accounts
            if (current_time - self._last_sync).seconds < 30:
                return

            mt_repo = MetaTraderRepository(supabase_client)
            accounts = await mt_repo.get_active_accounts()

            for account in accounts[:5]:  # Limit to 5 accounts per cycle
                try:
                    await self.trading_service.sync_account_data(account['id'])
                except Exception as e:
                    logger.warning(
                        f"⚠️ Failed to sync account {account['id']}: {e}")

            self._last_sync = current_time

            # Cleanup old events (daily)
            if not hasattr(self, '_last_cleanup'):
                self._last_cleanup = current_time

            if (current_time - self._last_cleanup).days >= 1:
                try:
                    cleaned = await self.trading_service.event_handler.cleanup_old_events(days_to_keep=30)
                    logger.info(f"🧹 Cleaned up {cleaned} old events")
                    self._last_cleanup = current_time
                except Exception as e:
                    logger.warning(f"⚠️ Failed to cleanup old events: {e}")

        except Exception as e:
            logger.error(f"❌ Error in periodic tasks: {e}")


async def demonstrate_integration():
    """
    Demonstrate the Supabase integration functionality
    """
    logger.info("🧪 Running integration demonstration...")

    try:
        # Initialize repositories
        mt_repo = MetaTraderRepository(supabase_client)
        bot_repo = BotRepository(supabase_client)

        # Test 1: Get active accounts
        logger.info("📋 Testing account retrieval...")
        accounts = await mt_repo.get_active_accounts()
        logger.info(f"✅ Found {len(accounts)} active accounts")

        # Test 2: Get active bots
        logger.info("🤖 Testing bot retrieval...")
        bots = await bot_repo.get_active_bots()
        logger.info(f"✅ Found {len(bots)} active bots")

        # Test 3: Send a test event
        logger.info("📤 Testing event system...")
        if accounts:
            account_id = accounts[0]['id']
            event_id = await trading_service.event_handler.send_event(
                account_id=account_id,
                event_type=EventType.SYSTEM_INFO,
                content={"message": "Supabase integration test",
                         "timestamp": datetime.utcnow().isoformat()},
                severity=EventSeverity.INFO
            )
            logger.info(f"✅ Sent test event: {event_id}")

        # Test 4: Health check
        logger.info("🏥 Testing health check...")
        health = await trading_service.health_check()
        logger.info(f"✅ Health check: {health}")

        logger.info("🎉 Integration demonstration completed successfully!")

    except Exception as e:
        logger.error(f"❌ Integration demonstration failed: {e}")
        raise


async def main():
    """
    Main entry point
    """
    app = PatrickDisplayApp()

    try:
        # Start the application
        await app.startup()

        # Run demonstration if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--demo":
            await demonstrate_integration()
            return

        # Run main application loop
        await app.run_main_loop()

    except KeyboardInterrupt:
        logger.info("🔌 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        return 1
    finally:
        # Ensure cleanup
        if app.is_running:
            await app.shutdown()

    return 0

if __name__ == "__main__":
    # Set up asyncio event loop policy for Windows compatibility
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
