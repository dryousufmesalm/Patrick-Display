"""
Main Real-Time Trading System v2 - Complete Integration
Includes Orders Manager, Cycles Manager, and Strategy Management
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Import real-time components
from services.supabase_service import SupabaseService
from Bots.trading_bot_v2 import TradingBotV2
from Orders.orders_manager_v2 import OrdersManagerV2
from cycles.cycles_manager_v2 import CyclesManagerV2
from Strategy.CycleTrader_v2 import CycleTraderV2
from Strategy.AdaptiveHedging_v2 import AdaptiveHedgingV2
from MetaTrader.mt5_real_connector import MT5RealConnector
from services.websocket_service import get_websocket_service

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('realtime_trading.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class RealTimeTradingSystemV2:
    """
    Complete real-time trading system with all managers
    Orchestrates order management, cycle management, and strategy execution
    """

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.logger = logger
        self.running = False
        self.startup_time = datetime.utcnow()

        # Core components
        self.supabase_service = None
        self.mt5_connector = None
        self.orders_manager = None
        self.cycles_manager = None
        self.trading_bot = None
        self.websocket_service = None

        # Strategies
        self.cycle_trader = None
        self.adaptive_hedging = None
        self.active_strategies = {}

        # Management tasks
        self.management_tasks = []
        self.strategy_tasks = []

        # System statistics
        self.system_stats = {
            'startup_time': self.startup_time.isoformat(),
            'orders_synced': 0,
            'cycles_synced': 0,
            'strategies_running': 0,
            'total_errors': 0,
            'uptime_seconds': 0
        }

    async def initialize(self):
        """Initialize all system components"""
        try:
            self.logger.info(
                f"Initializing Real-Time Trading System v2 for account {self.account_id}")

            # Initialize core services
            await self.initialize_core_services()

            # Initialize managers
            await self.initialize_managers()

            # Initialize strategies
            await self.initialize_strategies()

            # Setup graceful shutdown
            self.setup_signal_handlers()

            self.logger.info(
                "Real-Time Trading System v2 initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize system: {e}")
            raise

    async def initialize_core_services(self):
        """Initialize Supabase and MT5 connections"""
        try:
            # Initialize Supabase service
            self.supabase_service = SupabaseService()
            await self.supabase_service.initialize()
            self.logger.info("Supabase service initialized")

            # Initialize WebSocket service
            self.websocket_service = await get_websocket_service()
            self.logger.info("WebSocket service initialized")

            # Initialize MT5 connector
            self.mt5_connector = MT5RealConnector()
            await self.mt5_connector.initialize()
            await self.mt5_connector.login(self.account_id)
            self.logger.info("MT5 connector initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            raise

    async def initialize_managers(self):
        """Initialize order and cycle managers"""
        try:
            # Initialize Orders Manager
            self.orders_manager = OrdersManagerV2(
                self.mt5_connector,
                self.supabase_service.client,
                self.account_id,
                self.websocket_service
            )
            self.logger.info("Orders Manager v2 initialized")

            # Initialize Cycles Manager
            self.cycles_manager = CyclesManagerV2(
                self.mt5_connector,
                self.supabase_service.client,
                self.account_id,
                self.orders_manager,
                self.websocket_service
            )
            self.logger.info("Cycles Manager v2 initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize managers: {e}")
            raise

    async def initialize_strategies(self):
        """Initialize trading strategies"""
        try:
            # Initialize Trading Bot with proper constructor parameters
            bot_config = {
                'magic': 123456,
                'symbols': ['EURUSD'],
                'strategy_type': 'CycleTrader',
                'name': f'Bot_{self.account_id}'
            }

            self.trading_bot = TradingBotV2(
                self.mt5_connector,
                self.account_id,
                'system_user',  # user_id
                'default_strategy',  # strategy_id
                bot_config
            )

            # Initialize strategies with proper constructor parameters
            strategy_config = {
                'symbol': 'EURUSD',
                'lot_sizes': [0.01],
                'take_profit': 5,
                'max_cycles': 1
            }

            # Initialize CycleTrader strategy
            self.cycle_trader = CycleTraderV2(
                self.mt5_connector,  # meta_trader
                strategy_config,     # config
                self.supabase_service.client,  # supabase_client
                'EURUSD',           # symbol
                self.trading_bot    # bot
            )
            self.active_strategies['CycleTrader'] = self.cycle_trader

            # Initialize AdaptiveHedging strategy
            self.adaptive_hedging = AdaptiveHedgingV2(
                self.mt5_connector,  # meta_trader
                strategy_config,     # config
                self.supabase_service.client,  # supabase_client
                'EURUSD',           # symbol
                self.trading_bot    # bot
            )
            self.active_strategies['AdaptiveHedging'] = self.adaptive_hedging

            self.logger.info(
                f"Initialized {len(self.active_strategies)} trading strategies")

        except Exception as e:
            self.logger.error(f"Failed to initialize strategies: {e}")
            raise

    async def start(self):
        """Start the complete trading system"""
        try:
            self.running = True
            self.logger.info("Starting Real-Time Trading System v2")

            # Start managers in background
            await self.start_managers()

            # Start strategies
            await self.start_strategies()

            # Start system monitoring
            await self.start_monitoring()

            # Main system loop
            await self.run_main_loop()

        except Exception as e:
            self.logger.error(f"Error in main system: {e}")
            raise
        finally:
            await self.shutdown()

    async def start_managers(self):
        """Start order and cycle managers"""
        try:
            # Start Orders Manager
            orders_task = asyncio.create_task(
                self.orders_manager.start(),
                name="OrdersManager"
            )
            self.management_tasks.append(orders_task)

            # Start Cycles Manager
            cycles_task = asyncio.create_task(
                self.cycles_manager.start(),
                name="CyclesManager"
            )
            self.management_tasks.append(cycles_task)

            # Give managers time to initialize
            await asyncio.sleep(2)

            self.logger.info("Management systems started")

        except Exception as e:
            self.logger.error(f"Failed to start managers: {e}")
            raise

    async def start_strategies(self):
        """Start trading strategies"""
        try:
            for strategy_name, strategy in self.active_strategies.items():
                strategy_task = asyncio.create_task(
                    strategy.run(),
                    name=f"Strategy_{strategy_name}"
                )
                self.strategy_tasks.append(strategy_task)
                self.logger.info(f"Started strategy: {strategy_name}")

            self.system_stats['strategies_running'] = len(self.strategy_tasks)

        except Exception as e:
            self.logger.error(f"Failed to start strategies: {e}")
            raise

    async def start_monitoring(self):
        """Start system monitoring and statistics"""
        try:
            monitor_task = asyncio.create_task(
                self.run_system_monitor(),
                name="SystemMonitor"
            )
            self.management_tasks.append(monitor_task)

            self.logger.info("System monitoring started")

        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise

    async def run_main_loop(self):
        """Main system event loop"""
        while self.running:
            try:
                # Check task health
                await self.check_task_health()

                # Update system statistics
                await self.update_system_stats()

                # Wait before next iteration
                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                self.system_stats['total_errors'] += 1
                await asyncio.sleep(5)

    async def check_task_health(self):
        """Check health of all running tasks"""
        try:
            # Check management tasks
            for task in self.management_tasks[:]:  # Copy list to safely modify
                if task.done():
                    task_name = task.get_name()
                    if task.exception():
                        self.logger.error(
                            f"Management task {task_name} failed: {task.exception()}")
                        # Restart failed management tasks
                        await self.restart_management_task(task_name)
                    else:
                        self.logger.warning(
                            f"Management task {task_name} completed unexpectedly")
                    self.management_tasks.remove(task)

            # Check strategy tasks
            for task in self.strategy_tasks[:]:  # Copy list to safely modify
                if task.done():
                    task_name = task.get_name()
                    if task.exception():
                        self.logger.error(
                            f"Strategy task {task_name} failed: {task.exception()}")
                        # Restart failed strategy tasks
                        await self.restart_strategy_task(task_name)
                    else:
                        self.logger.warning(
                            f"Strategy task {task_name} completed unexpectedly")
                    self.strategy_tasks.remove(task)

        except Exception as e:
            self.logger.error(f"Error checking task health: {e}")

    async def restart_management_task(self, task_name: str):
        """Restart a failed management task"""
        try:
            self.logger.info(f"Restarting management task: {task_name}")

            if task_name == "OrdersManager":
                orders_task = asyncio.create_task(
                    self.orders_manager.start(),
                    name="OrdersManager"
                )
                self.management_tasks.append(orders_task)

            elif task_name == "CyclesManager":
                cycles_task = asyncio.create_task(
                    self.cycles_manager.start(),
                    name="CyclesManager"
                )
                self.management_tasks.append(cycles_task)

            elif task_name == "SystemMonitor":
                monitor_task = asyncio.create_task(
                    self.run_system_monitor(),
                    name="SystemMonitor"
                )
                self.management_tasks.append(monitor_task)

        except Exception as e:
            self.logger.error(
                f"Failed to restart management task {task_name}: {e}")

    async def restart_strategy_task(self, task_name: str):
        """Restart a failed strategy task"""
        try:
            self.logger.info(f"Restarting strategy task: {task_name}")

            strategy_name = task_name.replace("Strategy_", "")
            if strategy_name in self.active_strategies:
                strategy = self.active_strategies[strategy_name]
                strategy_task = asyncio.create_task(
                    strategy.run(),
                    name=task_name
                )
                self.strategy_tasks.append(strategy_task)

        except Exception as e:
            self.logger.error(
                f"Failed to restart strategy task {task_name}: {e}")

    async def run_system_monitor(self):
        """System monitoring and reporting"""
        while self.running:
            try:
                # Get system statistics
                await self.update_system_stats()

                # Log comprehensive status every 5 minutes
                if int(self.system_stats['uptime_seconds']) % 300 == 0:
                    await self.log_system_status()

                # Send system health events
                await self.send_system_health_event()

                await asyncio.sleep(30)  # Monitor every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in system monitor: {e}")
                await asyncio.sleep(60)

    async def update_system_stats(self):
        """Update system statistics"""
        try:
            current_time = datetime.utcnow()
            self.system_stats['uptime_seconds'] = int(
                (current_time - self.startup_time).total_seconds())

            # Get manager statistics
            if self.orders_manager:
                orders_stats = await self.orders_manager.get_order_statistics()
                self.system_stats['orders_synced'] = orders_stats.get(
                    'total_syncs', 0)

            if self.cycles_manager:
                cycles_stats = await self.cycles_manager.get_cycle_statistics()
                self.system_stats['cycles_synced'] = cycles_stats.get(
                    'total_syncs', 0)

            self.system_stats['strategies_running'] = len(
                [t for t in self.strategy_tasks if not t.done()])

        except Exception as e:
            self.logger.error(f"Error updating system stats: {e}")

    async def log_system_status(self):
        """Log comprehensive system status"""
        try:
            orders_stats = await self.orders_manager.get_order_statistics() if self.orders_manager else {}
            cycles_stats = await self.cycles_manager.get_cycle_statistics() if self.cycles_manager else {}

            self.logger.info(f"""
=== REAL-TIME TRADING SYSTEM STATUS ===
Account: {self.account_id}
Uptime: {self.system_stats['uptime_seconds']} seconds
Active Strategies: {self.system_stats['strategies_running']}/{len(self.active_strategies)}
Management Tasks: {len([t for t in self.management_tasks if not t.done()])}/{len(self.management_tasks)}

ORDERS MANAGER:
- MT5 Orders: {orders_stats.get('mt5_orders_count', 0)}
- DB Orders: {orders_stats.get('db_orders_count', 0)}
- Suspicious Orders: {orders_stats.get('suspicious_orders_count', 0)}
- Fixed Orders: {orders_stats.get('fixed_orders', 0)}
- Total Syncs: {orders_stats.get('total_syncs', 0)}

CYCLES MANAGER:
- Active Cycles: {cycles_stats.get('total_active_cycles', 0)}
- CT Cycles: {cycles_stats.get('ct_cycles_count', 0)} (Profit: ${cycles_stats.get('ct_total_profit', 0)})
- AH Cycles: {cycles_stats.get('ah_cycles_count', 0)} (Profit: ${cycles_stats.get('ah_total_profit', 0)})
- Total Profit: ${cycles_stats.get('total_profit', 0)}
- Fixed Cycles: {cycles_stats.get('fixed_cycles', 0)}
- Total Syncs: {cycles_stats.get('total_syncs', 0)}

SYSTEM HEALTH:
- Total Errors: {self.system_stats['total_errors']}
- System Status: {'HEALTHY' if self.system_stats['total_errors'] < 100 else 'DEGRADED'}
=======================================
            """)

        except Exception as e:
            self.logger.error(f"Error logging system status: {e}")

    async def send_system_health_event(self):
        """Send system health event to Supabase"""
        try:
            if self.supabase_service:
                health_status = 'HEALTHY' if self.system_stats['total_errors'] < 100 else 'DEGRADED'

                event_data = {
                    'uuid': f"{datetime.utcnow().timestamp()}_{self.account_id}_system_health",
                    'account': self.account_id,
                    'content': {
                        'system_stats': self.system_stats,
                        'health_status': health_status,
                        'active_managers': len([t for t in self.management_tasks if not t.done()]),
                        'active_strategies': len([t for t in self.strategy_tasks if not t.done()])
                    },
                    'event_type': 'SYSTEM_HEALTH',
                    'severity': 'INFO' if health_status == 'HEALTHY' else 'WARNING',
                    'created_at': datetime.utcnow().isoformat()
                }

                await self.supabase_service.client.table('events').insert(event_data).execute()

        except Exception as e:
            self.logger.error(f"Error sending system health event: {e}")

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
            self.logger.info("Initiating system shutdown...")
            self.running = False

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

            self.logger.info("System shutdown completed")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    async def emergency_stop(self, reason: str = "Emergency stop requested"):
        """Emergency stop all trading activities"""
        try:
            self.logger.warning(f"EMERGENCY STOP: {reason}")

            # Close all cycles
            if self.cycles_manager:
                closed_count = await self.cycles_manager.close_all_cycles("system", "emergency_stop")
                self.logger.info(f"Emergency closed {closed_count} cycles")

            # Stop all strategies
            for task in self.strategy_tasks:
                if not task.done():
                    task.cancel()

            # Send emergency event
            if self.supabase_service:
                event_data = {
                    'uuid': f"{datetime.utcnow().timestamp()}_{self.account_id}_emergency",
                    'account': self.account_id,
                    'content': {'reason': reason, 'closed_cycles': closed_count if 'closed_count' in locals() else 0},
                    'event_type': 'EMERGENCY_STOP',
                    'severity': 'CRITICAL',
                    'created_at': datetime.utcnow().isoformat()
                }
                await self.supabase_service.client.table('events').insert(event_data).execute()

            self.logger.warning("Emergency stop completed")

        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")


async def main():
    """Main entry point"""
    # Configuration - should come from environment or config file
    ACCOUNT_ID = "your_account_id_here"  # Replace with actual account ID

    system = RealTimeTradingSystemV2(ACCOUNT_ID)

    try:
        await system.initialize()
        await system.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"System error: {e}")
        await system.emergency_stop(f"System error: {e}")
    finally:
        await system.shutdown()


if __name__ == "__main__":
    # Run the real-time trading system
    asyncio.run(main())
