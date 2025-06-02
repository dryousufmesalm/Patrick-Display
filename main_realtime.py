"""
Real-Time Trading System with Supabase Integration
Entry point for the new architecture
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Dict, List
from datetime import datetime

# Import the new components
from Bots.trading_bot_v2 import TradingBotV2
from services.supabase_service import get_supabase_service, cleanup_supabase_service
from MetaTrader.mt5_connector import MT5Connector  # Assuming this exists

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_realtime.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TradingSystemManager:
    """
    Manages the entire real-time trading system
    Coordinates multiple bots and strategies
    """

    def __init__(self):
        self.bots: Dict[str, TradingBotV2] = {}
        self.mt5_connector = None
        self.supabase_service = None
        self.is_running = False
        self.shutdown_event = asyncio.Event()

        # System configuration
        self.config = {
            'max_bots': int(os.getenv('MAX_BOTS', '10')),
            'update_interval': float(os.getenv('UPDATE_INTERVAL', '0.1')),
            'heartbeat_interval': int(os.getenv('HEARTBEAT_INTERVAL', '60')),
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }

    async def initialize(self) -> bool:
        """Initialize the trading system"""
        try:
            logger.info("Initializing Real-Time Trading System...")

            # Initialize Supabase service
            self.supabase_service = await get_supabase_service()
            if not self.supabase_service.is_connected:
                logger.error("Failed to connect to Supabase")
                return False

            # Initialize MetaTrader 5 connection
            self.mt5_connector = MT5Connector()
            if not await self.mt5_connector.initialize():
                logger.error("Failed to initialize MetaTrader 5")
                return False

            # Load active bots from database
            await self.load_active_bots()

            # Set up signal handlers for graceful shutdown
            self.setup_signal_handlers()

            logger.info(
                f"Trading system initialized with {len(self.bots)} bots")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize trading system: {e}")
            return False

    async def load_active_bots(self):
        """Load active bots from the database"""
        try:
            # Get active trading accounts
            result = await self.supabase_service.execute_query(
                'select',
                table='meta-trader-accounts',
                filters={'eq': {'is_active': True}},
                columns='*, bots(*)'
            )

            if not result or not result.data:
                logger.info("No active trading accounts found")
                return

            for account_data in result.data:
                account_id = account_data['id']
                user_id = account_data['user']

                # Get bot configurations for this account
                bot_configs = await self.get_bot_configs(user_id, account_id)

                for config in bot_configs:
                    await self.create_bot(account_id, user_id, config)

            logger.info(f"Loaded {len(self.bots)} active bots")

        except Exception as e:
            logger.error(f"Error loading active bots: {e}")

    async def get_bot_configs(self, user_id: str, account_id: str) -> List[Dict]:
        """Get bot configurations for a user and account"""
        try:
            result = await self.supabase_service.execute_query(
                'select',
                table='bot-configs',
                filters={'eq': {'user': user_id}},
                columns='*'
            )

            configs = []
            if result and result.data:
                for config_data in result.data:
                    # Parse configuration
                    bot_config = {
                        'name': config_data.get('name', f"Bot_{account_id}"),
                        'strategy_type': self.extract_strategy_type(config_data.get('name', '')),
                        'symbols': ['EURUSD'],  # Default, can be extended
                        'magic': 12345,  # Default magic number
                        **config_data.get('configs', {})
                    }
                    configs.append(bot_config)

            # If no configs found, create default
            if not configs:
                configs.append({
                    'name': f"DefaultBot_{account_id}",
                    'strategy_type': 'CycleTrader',
                    'symbols': ['EURUSD'],
                    'magic': 12345
                })

            return configs

        except Exception as e:
            logger.error(f"Error getting bot configs: {e}")
            return []

    def extract_strategy_type(self, config_name: str) -> str:
        """Extract strategy type from config name"""
        if 'AdaptiveHedging' in config_name:
            return 'AdaptiveHedging'
        elif 'CycleTrader' in config_name:
            return 'CycleTrader'
        else:
            return 'CycleTrader'  # Default

    async def create_bot(self, account_id: str, user_id: str, config: Dict):
        """Create a new trading bot"""
        try:
            if len(self.bots) >= self.config['max_bots']:
                logger.warning(
                    f"Maximum number of bots ({self.config['max_bots']}) reached")
                return

            # Create strategy record if it doesn't exist
            strategy_id = await self.ensure_strategy_exists(config['strategy_type'])

            # Create bot instance
            bot = TradingBotV2(
                self.mt5_connector,
                account_id,
                user_id,
                strategy_id,
                config
            )

            # Store bot
            bot_key = f"{account_id}_{user_id}_{config['name']}"
            self.bots[bot_key] = bot

            logger.info(
                f"Created bot: {config['name']} for account {account_id}")

        except Exception as e:
            logger.error(f"Error creating bot: {e}")

    async def ensure_strategy_exists(self, strategy_type: str) -> str:
        """Ensure strategy record exists in database"""
        try:
            # Check if strategy exists
            result = await self.supabase_service.execute_query(
                'select',
                table='strategies',
                filters={'eq': {'name': strategy_type}},
                limit=1
            )

            if result and result.data:
                return result.data[0]['id']

            # Create strategy record
            strategy_data = {
                'name': strategy_type,
                'description': f"{strategy_type} trading strategy",
                'is_active': True,
                'created_at': datetime.utcnow().isoformat()
            }

            create_result = await self.supabase_service.execute_query(
                'insert',
                table='strategies',
                data=strategy_data
            )

            if create_result and create_result.data:
                return create_result.data[0]['id']

            # Fallback: generate UUID
            import uuid
            return str(uuid.uuid4())

        except Exception as e:
            logger.error(f"Error ensuring strategy exists: {e}")
            import uuid
            return str(uuid.uuid4())

    async def start_all_bots(self):
        """Start all trading bots"""
        try:
            if not self.bots:
                logger.info("No bots to start")
                return

            # Start bots concurrently
            tasks = []
            for bot_key, bot in self.bots.items():
                task = asyncio.create_task(bot.start())
                tasks.append(task)
                logger.info(f"Starting bot: {bot.name}")

            # Wait for all bots to start
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error starting bots: {e}")

    async def stop_all_bots(self):
        """Stop all trading bots gracefully"""
        try:
            if not self.bots:
                return

            logger.info("Stopping all trading bots...")

            # Stop bots concurrently
            stop_tasks = []
            for bot_key, bot in self.bots.items():
                task = asyncio.create_task(bot.stop())
                stop_tasks.append(task)
                logger.info(f"Stopping bot: {bot.name}")

            # Wait for all bots to stop
            await asyncio.gather(*stop_tasks, return_exceptions=True)

            logger.info("All bots stopped")

        except Exception as e:
            logger.error(f"Error stopping bots: {e}")

    async def monitor_system(self):
        """Monitor system health and performance"""
        logger.info("Starting system monitor")

        while self.is_running:
            try:
                # Check system health
                await self.health_check()

                # Log system statistics
                await self.log_system_stats()

                # Wait before next check
                await asyncio.sleep(self.config['heartbeat_interval'])

            except Exception as e:
                logger.error(f"Error in system monitor: {e}")
                await asyncio.sleep(10)

        logger.info("System monitor stopped")

    async def health_check(self):
        """Perform system health check"""
        try:
            # Check Supabase connection
            if not self.supabase_service.is_connected:
                logger.warning(
                    "Supabase connection lost, attempting reconnect...")
                await self.supabase_service.reconnect()

            # Check MetaTrader connection
            if not self.mt5_connector.is_connected():
                logger.warning(
                    "MetaTrader connection lost, attempting reconnect...")
                await self.mt5_connector.reconnect()

            # Check bot health
            unhealthy_bots = []
            for bot_key, bot in self.bots.items():
                if not bot.is_running:
                    unhealthy_bots.append(bot_key)

            if unhealthy_bots:
                logger.warning(f"Found {len(unhealthy_bots)} unhealthy bots")
                for bot_key in unhealthy_bots:
                    await self.restart_bot(bot_key)

        except Exception as e:
            logger.error(f"Error in health check: {e}")

    async def restart_bot(self, bot_key: str):
        """Restart a specific bot"""
        try:
            if bot_key in self.bots:
                bot = self.bots[bot_key]
                logger.info(f"Restarting bot: {bot.name}")

                # Stop bot
                await bot.stop()

                # Start bot again
                asyncio.create_task(bot.start())

        except Exception as e:
            logger.error(f"Error restarting bot {bot_key}: {e}")

    async def log_system_stats(self):
        """Log system performance statistics"""
        try:
            stats = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_bots': len(self.bots),
                'running_bots': sum(1 for bot in self.bots.values() if bot.is_running),
                'supabase_queries': self.supabase_service.query_count,
                'system_uptime': (datetime.utcnow() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
            }

            # Get bot-specific stats
            bot_stats = {}
            for bot_key, bot in self.bots.items():
                bot_status = await bot.get_status()
                bot_stats[bot_key] = {
                    'is_running': bot_status.get('is_running', False),
                    'events_processed': bot_status.get('performance_stats', {}).get('events_processed', 0),
                    'active_symbols': len(bot_status.get('active_symbols', []))
                }

            stats['bot_stats'] = bot_stats

            logger.info(f"System Stats: {stats}")

            # Optionally save to database
            await self.save_system_stats(stats)

        except Exception as e:
            logger.error(f"Error logging system stats: {e}")

    async def save_system_stats(self, stats: Dict):
        """Save system statistics to database"""
        try:
            event_data = {
                'uuid': f"system_stats_{datetime.utcnow().timestamp()}",
                'account': 'system',
                'bot': 'system',
                'strategy': 'system',
                'event_type': 'SYSTEM_STATS',
                'content': stats,
                'severity': 'INFO',
                'created_at': datetime.utcnow().isoformat()
            }

            await self.supabase_service.create_event(event_data)

        except Exception as e:
            logger.error(f"Error saving system stats: {e}")

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(
                f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        """Main run method"""
        try:
            self.start_time = datetime.utcnow()
            self.is_running = True

            if not await self.initialize():
                logger.error("Failed to initialize system")
                return

            logger.info("Starting Real-Time Trading System...")

            # Start system monitor
            monitor_task = asyncio.create_task(self.monitor_system())

            # Start all bots
            bots_task = asyncio.create_task(self.start_all_bots())

            # Wait for shutdown signal or tasks to complete
            try:
                await asyncio.wait([
                    asyncio.create_task(self.shutdown_event.wait()),
                    monitor_task,
                    bots_task
                ], return_when=asyncio.FIRST_COMPLETED)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")

        except Exception as e:
            logger.error(f"Error in main run: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up system resources"""
        try:
            logger.info("Cleaning up system resources...")

            self.is_running = False

            # Stop all bots
            await self.stop_all_bots()

            # Close MetaTrader connection
            if self.mt5_connector:
                await self.mt5_connector.shutdown()

            # Clean up Supabase service
            await cleanup_supabase_service()

            logger.info("System cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main entry point"""
    try:
        # Create and run the trading system
        system = TradingSystemManager()
        await system.run()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Set event loop policy for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Run the main function
    asyncio.run(main())
