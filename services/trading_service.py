import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from db.supabase_client import SupabaseClient, supabase_client
from db.repositories.metatrader_repository import MetaTraderRepository
from db.repositories.bot_repository import BotRepository
from handlers.event_handler import EventHandler, EventType, EventSeverity

logger = logging.getLogger(__name__)


class TradingService:
    """
    Main trading service that orchestrates bot management and account synchronization
    Integrates Patrick Display with Peaceful Investment Supabase database
    """

    def __init__(self):
        self.supabase_client = supabase_client
        self.mt_repository = MetaTraderRepository(self.supabase_client)
        self.bot_repository = BotRepository(self.supabase_client)
        self.event_handler = EventHandler(self.supabase_client)

        # Runtime state
        self.active_bots: Dict[str, Dict] = {}
        self.account_balances: Dict[str, Dict] = {}
        self.is_running = False

        logger.info("TradingService initialized")

    async def initialize(self):
        """Initialize the trading service"""
        try:
            # Initialize database connection pool
            await self.supabase_client.init_db_pool()

            # Set up event listeners
            self.setup_event_listeners()

            # Load active accounts and bots
            await self.load_active_accounts()
            await self.load_active_bots()

            # Start real-time event listener
            self.event_handler.start_real_time_listener()

            self.is_running = True
            logger.info("TradingService initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing TradingService: {e}")
            raise

    async def shutdown(self):
        """Shutdown the trading service gracefully"""
        try:
            self.is_running = False

            # Stop all bots
            await self.stop_all_bots()

            # Stop event listener
            self.event_handler.stop_real_time_listener()

            # Close database connections
            await self.supabase_client.close_pool()

            logger.info("TradingService shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def setup_event_listeners(self):
        """Set up event listeners for real-time communication"""
        # Bot management events
        self.event_handler.add_event_listener(
            EventType.BOT_START, self.handle_bot_start)
        self.event_handler.add_event_listener(
            EventType.BOT_STOP, self.handle_bot_stop)
        self.event_handler.add_event_listener(
            EventType.BOT_UPDATE_SETTINGS, self.handle_bot_update_settings)

        # Order events
        self.event_handler.add_event_listener(
            EventType.ORDER_CREATE, self.handle_order_create)
        self.event_handler.add_event_listener(
            EventType.ORDER_MODIFY, self.handle_order_modify)
        self.event_handler.add_event_listener(
            EventType.ORDER_CLOSE, self.handle_order_close)

        # Account events
        self.event_handler.add_event_listener(
            EventType.ACCOUNT_BALANCE_UPDATE, self.handle_balance_update)

        logger.info("Event listeners configured")

    async def load_active_accounts(self):
        """Load all active MetaTrader accounts"""
        try:
            accounts = await self.mt_repository.get_active_accounts()

            for account in accounts:
                account_id = account["id"]
                self.account_balances[account_id] = {
                    "balance": account.get("balance", 0.0),
                    "equity": account.get("equity", 0.0),
                    "margin": account.get("margin", 0.0),
                    "last_update": datetime.utcnow()
                }

            logger.info(f"Loaded {len(accounts)} active accounts")
        except Exception as e:
            logger.error(f"Error loading active accounts: {e}")
            raise

    async def load_active_bots(self):
        """Load all active bots"""
        try:
            bots = await self.bot_repository.get_active_bots()

            for bot in bots:
                bot_id = bot["id"]
                self.active_bots[bot_id] = {
                    "data": bot,
                    "status": bot["status"],
                    "last_update": datetime.utcnow()
                }

            logger.info(f"Loaded {len(bots)} active bots")
        except Exception as e:
            logger.error(f"Error loading active bots: {e}")
            raise

    # Event Handlers
    async def handle_bot_start(self, event: Dict):
        """Handle bot start command"""
        try:
            bot_id = event.get("bot")
            if not bot_id:
                return

            # Get bot details
            bot = await self.bot_repository.find_by_id(bot_id)
            if not bot:
                logger.warning(f"Bot {bot_id} not found for start command")
                return

            # Start the bot (implement your bot starting logic here)
            success = await self.start_bot(bot)

            if success:
                # Update bot status
                await self.bot_repository.update_bot_status(bot_id, "ACTIVE")
                self.active_bots[bot_id] = {
                    "data": bot,
                    "status": "ACTIVE",
                    "last_update": datetime.utcnow()
                }
                logger.info(f"Bot {bot_id} started successfully")
            else:
                await self.bot_repository.update_bot_status(bot_id, "ERROR", "Failed to start")
                logger.error(f"Failed to start bot {bot_id}")

            # Mark event as processed
            await self.event_handler.mark_event_processed(event["id"])
        except Exception as e:
            logger.error(f"Error handling bot start: {e}")

    async def handle_bot_stop(self, event: Dict):
        """Handle bot stop command"""
        try:
            bot_id = event.get("bot")
            if not bot_id:
                return

            # Stop the bot (implement your bot stopping logic here)
            success = await self.stop_bot(bot_id)

            if success:
                # Update bot status
                await self.bot_repository.update_bot_status(bot_id, "INACTIVE")
                if bot_id in self.active_bots:
                    self.active_bots[bot_id]["status"] = "INACTIVE"
                logger.info(f"Bot {bot_id} stopped successfully")
            else:
                logger.error(f"Failed to stop bot {bot_id}")

            # Mark event as processed
            await self.event_handler.mark_event_processed(event["id"])
        except Exception as e:
            logger.error(f"Error handling bot stop: {e}")

    async def handle_bot_update_settings(self, event: Dict):
        """Handle bot settings update"""
        try:
            bot_id = event.get("bot")
            content = event.get("content", {})
            parameters = content.get("parameters", {})

            if not bot_id:
                return

            # Update bot settings
            await self.bot_repository.update_bot_settings(bot_id, parameters)

            # Update local cache
            if bot_id in self.active_bots:
                self.active_bots[bot_id]["last_update"] = datetime.utcnow()

            logger.info(f"Updated settings for bot {bot_id}")

            # Mark event as processed
            await self.event_handler.mark_event_processed(event["id"])
        except Exception as e:
            logger.error(f"Error handling bot settings update: {e}")

    async def handle_order_create(self, event: Dict):
        """Handle order creation command"""
        try:
            bot_id = event.get("bot")
            account_id = event.get("account")
            content = event.get("content", {})

            # Extract order parameters
            order_type = content.get("order_type")
            symbol = content.get("symbol")
            volume = content.get("volume")
            price = content.get("price")

            logger.info(
                f"Order create command: {order_type} {volume} {symbol} for bot {bot_id}")

            # Implement your order creation logic here
            # This would interface with your MetaTrader system

            # Mark event as processed
            await self.event_handler.mark_event_processed(event["id"])
        except Exception as e:
            logger.error(f"Error handling order create: {e}")

    async def handle_order_modify(self, event: Dict):
        """Handle order modification command"""
        try:
            content = event.get("content", {})
            order_id = content.get("order_id")

            logger.info(f"Order modify command for order {order_id}")

            # Implement your order modification logic here

            # Mark event as processed
            await self.event_handler.mark_event_processed(event["id"])
        except Exception as e:
            logger.error(f"Error handling order modify: {e}")

    async def handle_order_close(self, event: Dict):
        """Handle order close command"""
        try:
            content = event.get("content", {})
            order_id = content.get("order_id")

            logger.info(f"Order close command for order {order_id}")

            # Implement your order closing logic here

            # Mark event as processed
            await self.event_handler.mark_event_processed(event["id"])
        except Exception as e:
            logger.error(f"Error handling order close: {e}")

    async def handle_balance_update(self, event: Dict):
        """Handle account balance update"""
        try:
            account_id = event.get("account")
            content = event.get("content", {})

            balance = content.get("balance")
            equity = content.get("equity")
            margin = content.get("margin")

            if account_id and balance is not None and equity is not None:
                # Update database
                await self.mt_repository.update_account_balance(account_id, balance, equity, margin)

                # Update local cache
                self.account_balances[account_id] = {
                    "balance": balance,
                    "equity": equity,
                    "margin": margin,
                    "last_update": datetime.utcnow()
                }

                logger.info(
                    f"Updated balance for account {account_id}: ${balance}")

            # Mark event as processed
            await self.event_handler.mark_event_processed(event["id"])
        except Exception as e:
            logger.error(f"Error handling balance update: {e}")

    # Bot Management Methods
    async def start_bot(self, bot: Dict) -> bool:
        """Start a specific bot"""
        try:
            bot_id = bot["id"]
            magic_number = bot["magic_number"]

            # Implement your bot starting logic here
            # This would interface with your MetaTrader system
            logger.info(
                f"Starting bot {bot_id} with magic number {magic_number}")

            # Placeholder for actual implementation
            await asyncio.sleep(0.1)  # Simulate async operation

            return True
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return False

    async def stop_bot(self, bot_id: str) -> bool:
        """Stop a specific bot"""
        try:
            logger.info(f"Stopping bot {bot_id}")

            # Implement your bot stopping logic here
            # This would interface with your MetaTrader system

            # Placeholder for actual implementation
            await asyncio.sleep(0.1)  # Simulate async operation

            return True
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            return False

    async def stop_all_bots(self):
        """Stop all active bots"""
        try:
            bot_ids = list(self.active_bots.keys())

            for bot_id in bot_ids:
                await self.stop_bot(bot_id)
                await self.bot_repository.update_bot_status(bot_id, "INACTIVE")

            self.active_bots.clear()
            logger.info(f"Stopped {len(bot_ids)} bots")
        except Exception as e:
            logger.error(f"Error stopping all bots: {e}")

    # Utility Methods
    async def get_bot_status(self, bot_id: str) -> Optional[str]:
        """Get current status of a bot"""
        if bot_id in self.active_bots:
            return self.active_bots[bot_id]["status"]

        # Check database if not in cache
        bot = await self.bot_repository.find_by_id(bot_id)
        return bot["status"] if bot else None

    async def get_account_balance(self, account_id: str) -> Optional[Dict]:
        """Get current balance of an account"""
        if account_id in self.account_balances:
            return self.account_balances[account_id]

        # Check database if not in cache
        account = await self.mt_repository.find_by_id(account_id)
        if account:
            return {
                "balance": account.get("balance", 0.0),
                "equity": account.get("equity", 0.0),
                "margin": account.get("margin", 0.0),
                "last_update": datetime.utcnow()
            }

        return None

    async def sync_account_data(self, account_id: str):
        """Synchronize account data with MetaTrader"""
        try:
            # Implement your account data synchronization logic here
            # This would fetch current data from MetaTrader and update the database

            logger.info(f"Syncing account data for {account_id}")

            # Placeholder for actual implementation
            await asyncio.sleep(0.1)  # Simulate async operation

        except Exception as e:
            logger.error(f"Error syncing account data: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the trading service"""
        try:
            health = await self.supabase_client.health_check()

            health.update({
                "service_running": self.is_running,
                "active_bots": len(self.active_bots),
                "tracked_accounts": len(self.account_balances),
                "timestamp": datetime.utcnow().isoformat()
            })

            return health
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            return {
                "service_running": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global service instance
trading_service = TradingService()
