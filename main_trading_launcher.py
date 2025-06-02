"""
Enhanced Trading System Launcher for Phase 3
Accepts command-line parameters from the process manager and launches configured trading systems
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import real-time components
from services.supabase_service import SupabaseService
from Bots.trading_bot_v2 import TradingBotV2
from Orders.orders_manager_v2 import OrdersManagerV2
from cycles.cycles_manager_v2 import CyclesManagerV2
from Strategy.CycleTrader_v2 import CycleTraderV2
from Strategy.AdaptiveHedging_v2 import AdaptiveHedgingV2
from MetaTrader.mt5_real_connector import MT5RealConnector
from services.websocket_service import get_websocket_service

# Configure logging for the launcher


def setup_logging(session_id: str, account_id: str):
    """Setup logging for the trading session"""
    log_filename = f"trading_session_{session_id}_{account_id}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


class EnhancedTradingSystemLauncher:
    """
    Enhanced Trading System Launcher for Phase 3
    Launches trading systems with specific user/account parameters and strategy configurations
    """

    def __init__(self, session_id: str, user_id: str, account_id: str,
                 strategies: List[str], config: Dict[str, Any]):
        self.session_id = session_id
        self.user_id = user_id
        self.account_id = account_id
        self.strategies = strategies
        self.config = config

        # Setup logging
        self.logger = setup_logging(session_id, account_id)

        self.running = False
        self.startup_time = datetime.utcnow()

        # Core components
        self.supabase_service = None
        self.mt5_connector = None
        self.orders_manager = None
        self.cycles_manager = None
        self.trading_bot = None
        self.websocket_service = None

        # Strategy instances
        self.active_strategies = {}
        self.strategy_tasks = []
        self.management_tasks = []

        # Session tracking
        self.session_stats = {
            'session_id': session_id,
            'user_id': user_id,
            'account_id': account_id,
            'strategies': strategies,
            'startup_time': self.startup_time.isoformat(),
            'status': 'initializing',
            'orders_processed': 0,
            'cycles_processed': 0,
            'total_profit': 0.0,
            'uptime_seconds': 0
        }

        self.logger.info(f"Enhanced Trading System Launcher initialized")
        self.logger.info(f"Session: {session_id}")
        self.logger.info(f"User: {user_id}")
        self.logger.info(f"Account: {account_id}")
        self.logger.info(f"Strategies: {strategies}")

    async def initialize(self):
        """Initialize all system components with session parameters"""
        try:
            self.logger.info("Initializing Enhanced Trading System...")

            # Update session status
            self.session_stats['status'] = 'initializing'
            await self.update_session_status('initializing')

            # Initialize core services
            await self.initialize_core_services()

            # Initialize managers
            await self.initialize_managers()

            # Initialize selected strategies
            await self.initialize_selected_strategies()

            # Setup graceful shutdown
            self.setup_signal_handlers()

            self.session_stats['status'] = 'initialized'
            await self.update_session_status('initialized')

            self.logger.info(
                "Enhanced Trading System initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize system: {e}")
            self.session_stats['status'] = 'error'
            await self.update_session_status('error')
            raise

    async def initialize_core_services(self):
        """Initialize Supabase, MT5, and WebSocket connections"""
        try:
            # Initialize Supabase service
            self.supabase_service = SupabaseService()
            await self.supabase_service.initialize()
            self.logger.info("Supabase service initialized")

            # Initialize WebSocket service
            self.websocket_service = await get_websocket_service()
            self.logger.info("WebSocket service initialized")

            # Initialize MT5 connector with session account
            self.mt5_connector = MT5RealConnector()
            await self.mt5_connector.initialize()
            await self.mt5_connector.login(self.account_id)
            self.logger.info(
                f"MT5 connector initialized for account {self.account_id}")

        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            raise

    async def initialize_managers(self):
        """Initialize order and cycle managers for the session"""
        try:
            # Initialize Orders Manager for this session
            self.orders_manager = OrdersManagerV2(
                self.mt5_connector,
                self.supabase_service.client,
                self.account_id,
                self.websocket_service
            )
            self.logger.info("Orders Manager initialized for session")

            # Initialize Cycles Manager for this session
            self.cycles_manager = CyclesManagerV2(
                self.mt5_connector,
                self.supabase_service.client,
                self.account_id,
                self.orders_manager,
                self.websocket_service
            )
            self.logger.info("Cycles Manager initialized for session")

        except Exception as e:
            self.logger.error(f"Failed to initialize managers: {e}")
            raise

    async def initialize_selected_strategies(self):
        """Initialize only the selected strategies with their configurations"""
        try:
            # Initialize Trading Bot for the session
            bot_config = {
                'magic': int(f"12{self.account_id[-4:]}" if len(self.account_id) >= 4 else "123456"),
                'symbols': self.config.get('symbols', ['EURUSD']),
                'strategy_types': self.strategies,
                'name': f'Bot_{self.session_id[:8]}_{self.account_id}'
            }

            self.trading_bot = TradingBotV2(
                self.mt5_connector,
                self.account_id,
                self.user_id,
                self.session_id,
                bot_config
            )

            # Initialize each selected strategy with its configuration
            for strategy_name in self.strategies:
                await self.initialize_strategy(strategy_name)

            self.logger.info(
                f"Initialized {len(self.active_strategies)} strategies: {list(self.active_strategies.keys())}")

        except Exception as e:
            self.logger.error(f"Failed to initialize strategies: {e}")
            raise

    async def initialize_strategy(self, strategy_name: str):
        """Initialize a specific strategy with its configuration"""
        try:
            strategy_config = self.config.copy()

            # Set default symbol if not provided
            symbol = strategy_config.get('symbol', 'EURUSD')

            if strategy_name == 'CycleTrader':
                # Configure CycleTrader v2
                ct_config = {
                    'symbol': symbol,
                    'lot_sizes': self.parse_lot_sizes(strategy_config.get('lot_sizes', '0.01')),
                    'take_profit': float(strategy_config.get('take_profit', 5)),
                    'max_cycles': int(strategy_config.get('max_cycles', 1)),
                    'autotrade': bool(strategy_config.get('autotrade', False)),
                    'candle_timeframe': strategy_config.get('candle_timeframe', 'H1'),
                    'auto_candle_close': bool(strategy_config.get('auto_candle_close', False)),
                    'zones': self.parse_zones(strategy_config.get('zones', '500'))
                }

                self.active_strategies['CycleTrader'] = CycleTraderV2(
                    self.mt5_connector,
                    ct_config,
                    self.supabase_service.client,
                    symbol,
                    self.trading_bot
                )

                self.logger.info(
                    f"CycleTrader initialized with config: {ct_config}")

            elif strategy_name == 'AdaptiveHedging':
                # Configure AdaptiveHedging v2
                ah_config = {
                    'symbol': symbol,
                    'hedge_distance': float(strategy_config.get('hedge_distance', 50)),
                    'lot_progression': self.parse_lot_sizes(strategy_config.get('lot_progression', '0.01,0.02,0.04')),
                    'max_hedge_levels': int(strategy_config.get('max_hedge_levels', 6)),
                    'hedge_profit_target': float(strategy_config.get('hedge_profit_target', 10)),
                    'auto_hedge': bool(strategy_config.get('auto_hedge', True)),
                    'daily_profit_target': float(strategy_config.get('daily_profit_target', 50)),
                    'daily_loss_limit': float(strategy_config.get('daily_loss_limit', -50))
                }

                self.active_strategies['AdaptiveHedging'] = AdaptiveHedgingV2(
                    self.mt5_connector,
                    ah_config,
                    self.supabase_service.client,
                    symbol,
                    self.trading_bot
                )

                self.logger.info(
                    f"AdaptiveHedging initialized with config: {ah_config}")

            else:
                self.logger.warning(f"Unknown strategy: {strategy_name}")

        except Exception as e:
            self.logger.error(
                f"Failed to initialize strategy {strategy_name}: {e}")
            raise

    def parse_lot_sizes(self, lot_sizes_str: str) -> List[float]:
        """Parse lot sizes from string to list of floats"""
        try:
            if isinstance(lot_sizes_str, str):
                return [float(size.strip()) for size in lot_sizes_str.split(',')]
            elif isinstance(lot_sizes_str, (list, tuple)):
                return [float(size) for size in lot_sizes_str]
            else:
                return [float(lot_sizes_str)]
        except Exception as e:
            self.logger.warning(
                f"Error parsing lot sizes '{lot_sizes_str}': {e}, using default [0.01]")
            return [0.01]

    def parse_zones(self, zones_str: str) -> List[float]:
        """Parse zones from string to list of floats"""
        try:
            if isinstance(zones_str, str):
                return [float(zone.strip()) for zone in zones_str.split(',')]
            elif isinstance(zones_str, (list, tuple)):
                return [float(zone) for zone in zones_str]
            else:
                return [float(zones_str)]
        except Exception as e:
            self.logger.warning(
                f"Error parsing zones '{zones_str}': {e}, using default [500]")
            return [500.0]

    async def start(self):
        """Start the enhanced trading system"""
        try:
            self.logger.info("Starting Enhanced Trading System...")
            self.running = True

            self.session_stats['status'] = 'starting'
            await self.update_session_status('starting')

            # Start managers
            await self.start_managers()

            # Start selected strategies
            await self.start_strategies()

            # Start session monitoring
            await self.start_session_monitoring()

            self.session_stats['status'] = 'running'
            await self.update_session_status('running')

            self.logger.info("Enhanced Trading System started successfully")

            # Run main loop
            await self.run_main_loop()

        except Exception as e:
            self.logger.error(f"Error starting system: {e}")
            self.session_stats['status'] = 'error'
            await self.update_session_status('error')
            raise

    async def start_managers(self):
        """Start order and cycle managers"""
        try:
            # Start Orders Manager
            orders_task = asyncio.create_task(
                self.orders_manager.start_real_time_sync()
            )
            self.management_tasks.append(orders_task)
            self.logger.info("Orders Manager started")

            # Start Cycles Manager
            cycles_task = asyncio.create_task(
                self.cycles_manager.start_cycle_management()
            )
            self.management_tasks.append(cycles_task)
            self.logger.info("Cycles Manager started")

        except Exception as e:
            self.logger.error(f"Error starting managers: {e}")
            raise

    async def start_strategies(self):
        """Start all selected strategies"""
        try:
            for strategy_name, strategy in self.active_strategies.items():
                if hasattr(strategy, 'start'):
                    strategy_task = asyncio.create_task(strategy.start())
                    self.strategy_tasks.append(strategy_task)
                    self.logger.info(f"Started strategy: {strategy_name}")
                else:
                    self.logger.warning(
                        f"Strategy {strategy_name} has no start method")

        except Exception as e:
            self.logger.error(f"Error starting strategies: {e}")
            raise

    async def start_session_monitoring(self):
        """Start session-specific monitoring"""
        try:
            monitor_task = asyncio.create_task(self.run_session_monitor())
            self.management_tasks.append(monitor_task)
            self.logger.info("Session monitoring started")

        except Exception as e:
            self.logger.error(f"Error starting session monitoring: {e}")

    async def run_main_loop(self):
        """Main execution loop"""
        try:
            self.logger.info("Entering main execution loop...")

            while self.running:
                # Check task health
                await self.check_task_health()

                # Update session statistics
                await self.update_session_stats()

                # Send heartbeat
                await self.send_heartbeat()

                # Sleep for 30 seconds
                await asyncio.sleep(30)

        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            await self.shutdown()

    async def check_task_health(self):
        """Check health of all running tasks"""
        try:
            # Check management tasks
            for i, task in enumerate(self.management_tasks):
                if task.done() and not task.cancelled():
                    self.logger.warning(
                        f"Management task {i} completed unexpectedly")
                    # Could implement restart logic here

            # Check strategy tasks
            for i, task in enumerate(self.strategy_tasks):
                if task.done() and not task.cancelled():
                    self.logger.warning(
                        f"Strategy task {i} completed unexpectedly")
                    # Could implement restart logic here

        except Exception as e:
            self.logger.error(f"Error checking task health: {e}")

    async def run_session_monitor(self):
        """Run session-specific monitoring"""
        while self.running:
            try:
                # Update session statistics
                await self.update_session_stats()

                # Log session status periodically
                # Every 5 minutes
                if int(self.session_stats['uptime_seconds']) % 300 == 0:
                    await self.log_session_status()

                await asyncio.sleep(60)  # Monitor every minute

            except Exception as e:
                self.logger.error(f"Error in session monitor: {e}")
                await asyncio.sleep(60)

    async def update_session_stats(self):
        """Update session statistics"""
        try:
            current_time = datetime.utcnow()
            self.session_stats['uptime_seconds'] = int(
                (current_time - self.startup_time).total_seconds())

            # Get manager statistics
            if self.orders_manager:
                orders_stats = await self.orders_manager.get_order_statistics()
                self.session_stats['orders_processed'] = orders_stats.get(
                    'total_syncs', 0)

            if self.cycles_manager:
                cycles_stats = await self.cycles_manager.get_cycle_statistics()
                self.session_stats['cycles_processed'] = cycles_stats.get(
                    'total_syncs', 0)
                self.session_stats['total_profit'] = cycles_stats.get(
                    'total_profit', 0.0)

            self.session_stats['active_strategies'] = len(
                [t for t in self.strategy_tasks if not t.done()])
            self.session_stats['active_managers'] = len(
                [t for t in self.management_tasks if not t.done()])

        except Exception as e:
            self.logger.error(f"Error updating session stats: {e}")

    async def log_session_status(self):
        """Log detailed session status"""
        try:
            self.logger.info(f"""
=== TRADING SESSION STATUS ===
Session ID: {self.session_id}
User ID: {self.user_id}
Account ID: {self.account_id}
Uptime: {self.session_stats['uptime_seconds']} seconds
Status: {self.session_stats['status']}

STRATEGIES: {len(self.active_strategies)}
Active: {self.session_stats.get('active_strategies', 0)}
Configured: {', '.join(self.strategies)}

PERFORMANCE:
Orders Processed: {self.session_stats['orders_processed']}
Cycles Processed: {self.session_stats['cycles_processed']}
Total Profit: ${self.session_stats['total_profit']}

TASKS:
Management Tasks: {self.session_stats.get('active_managers', 0)}/{len(self.management_tasks)}
Strategy Tasks: {self.session_stats.get('active_strategies', 0)}/{len(self.strategy_tasks)}
==============================
            """)

        except Exception as e:
            self.logger.error(f"Error logging session status: {e}")

    async def send_heartbeat(self):
        """Send heartbeat to process manager"""
        try:
            # Update session status in database
            await self.update_session_status('running')

            # Could also send heartbeat via WebSocket or file
            heartbeat_file = f"session_{self.session_id}.heartbeat"
            with open(heartbeat_file, 'w') as f:
                json.dump({
                    'session_id': self.session_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': self.session_stats['status'],
                    'uptime': self.session_stats['uptime_seconds'],
                    'stats': self.session_stats
                }, f)

        except Exception as e:
            self.logger.error(f"Error sending heartbeat: {e}")

    async def update_session_status(self, status: str):
        """Update session status in Supabase"""
        try:
            if self.supabase_service:
                # Update trading session status
                await self.supabase_service.client.table('trading_sessions').update({
                    'status': status,
                    'last_updated': datetime.utcnow().isoformat(),
                    'session_stats': self.session_stats
                }).eq('id', self.session_id).execute()

        except Exception as e:
            self.logger.error(f"Error updating session status: {e}")

    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            self.logger.info(
                f"Received signal {signum}, initiating graceful shutdown...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def shutdown(self):
        """Graceful system shutdown"""
        try:
            self.logger.info("Initiating enhanced trading system shutdown...")
            self.running = False

            self.session_stats['status'] = 'stopping'
            await self.update_session_status('stopping')

            # Cancel all tasks
            all_tasks = self.management_tasks + self.strategy_tasks

            for task in all_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            if all_tasks:
                await asyncio.gather(*all_tasks, return_exceptions=True)

            # Close connections
            if self.supabase_service:
                await self.supabase_service.close()

            if self.mt5_connector:
                await self.mt5_connector.close()

            self.session_stats['status'] = 'stopped'
            await self.update_session_status('stopped')

            self.logger.info("Enhanced trading system shutdown completed")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Enhanced Trading System Launcher')

    parser.add_argument('--session-id', required=True,
                        help='Trading session ID')
    parser.add_argument('--user-id', required=True, help='User ID')
    parser.add_argument('--account-id', required=True,
                        help='MetaTrader account ID')
    parser.add_argument('--strategies', required=True,
                        help='Comma-separated list of strategies')
    parser.add_argument('--config', required=True,
                        help='JSON configuration string')

    return parser.parse_args()


async def main():
    """Main entry point for enhanced trading launcher"""
    try:
        # Parse command-line arguments
        args = parse_arguments()

        # Parse strategies and configuration
        strategies = [s.strip() for s in args.strategies.split(',')]
        config = json.loads(args.config)

        # Create and start the enhanced trading system
        system = EnhancedTradingSystemLauncher(
            session_id=args.session_id,
            user_id=args.user_id,
            account_id=args.account_id,
            strategies=strategies,
            config=config
        )

        await system.initialize()
        await system.start()

    except KeyboardInterrupt:
        print("Received keyboard interrupt")
    except Exception as e:
        print(f"System error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the enhanced trading system launcher
    asyncio.run(main())
