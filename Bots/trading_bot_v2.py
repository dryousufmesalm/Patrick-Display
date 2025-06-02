"""
Unified Trading Bot with Real-Time Supabase Integration
Manages multiple strategies with sub-second performance
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import uuid

from services.supabase_service import get_supabase_service
from Strategy.CycleTrader_v2 import CycleTraderV2
from Strategy.AdaptiveHedging_v2 import AdaptiveHedgingV2

logger = logging.getLogger(__name__)


class TradingBotV2:
    """
    Unified trading bot with real-time Supabase integration
    Supports multiple strategies and symbols
    """

    def __init__(self, meta_trader, account_id: str, user_id: str, strategy_id: str, config: Dict):
        self.meta_trader = meta_trader
        self.account_id = account_id
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.config = config
        self.magic = config.get('magic', 12345)

        # Bot identification
        self.id = str(uuid.uuid4())
        self.name = config.get('name', f"Bot_{self.account_id}")

        # Strategy management
        self.strategies: Dict[str, Any] = {}  # symbol -> strategy instance
        self.active_symbols = config.get('symbols', ['EURUSD'])
        self.strategy_type = config.get('strategy_type', 'CycleTrader')

        # Supabase client
        self.supabase_client = None

        # Event handling
        self.event_queue = asyncio.Queue()
        self.is_running = False
        self.stop_requested = False

        # Performance tracking
        self.start_time = datetime.utcnow()
        self.events_processed = 0
        self.last_heartbeat = datetime.utcnow()

        # Connection status
        self.connection_status = 'disconnected'

    async def initialize(self) -> bool:
        """Initialize the trading bot"""
        try:
            # Initialize Supabase client
            self.supabase_client = await get_supabase_service()

            if not self.supabase_client.is_connected:
                logger.error("Failed to connect to Supabase")
                return False

            # Create strategies for each symbol
            for symbol in self.active_symbols:
                await self.create_strategy_for_symbol(symbol)

            # Register bot in database
            await self.register_bot()

            self.connection_status = 'connected'
            logger.info(
                f"Trading bot {self.name} initialized with {len(self.strategies)} strategies")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize trading bot: {e}")
            return False

    async def create_strategy_for_symbol(self, symbol: str):
        """Create and initialize a strategy for a specific symbol"""
        try:
            # Strategy-specific configuration
            strategy_config = self.config.copy()
            strategy_config['symbol'] = symbol

            # Create strategy instance based on type
            if self.strategy_type == 'CycleTrader':
                strategy = CycleTraderV2(
                    self.meta_trader,
                    strategy_config,
                    self.supabase_client,
                    symbol,
                    self
                )
            elif self.strategy_type == 'AdaptiveHedging':
                strategy = AdaptiveHedgingV2(
                    self.meta_trader,
                    strategy_config,
                    self.supabase_client,
                    symbol,
                    self
                )
            else:
                raise ValueError(
                    f"Unknown strategy type: {self.strategy_type}")

            # Initialize strategy
            if await strategy.initialize():
                self.strategies[symbol] = strategy
                logger.info(
                    f"Strategy {self.strategy_type} created for {symbol}")
            else:
                logger.error(f"Failed to initialize strategy for {symbol}")

        except Exception as e:
            logger.error(f"Error creating strategy for {symbol}: {e}")

    async def register_bot(self):
        """Register bot in the database"""
        try:
            bot_data = {
                'id': self.id,
                'name': self.name,
                'account': self.account_id,
                'user': self.user_id,
                'strategy': self.strategy_id,
                'magic': self.magic,
                'symbols': self.active_symbols,
                'strategy_type': self.strategy_type,
                'status': 'running',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Use Supabase client to create bot record
            result = await self.supabase_client.execute_query(
                'upsert',
                table='bots',
                data=bot_data
            )

            if result:
                logger.info(f"Bot {self.name} registered in database")
            else:
                logger.warning("Failed to register bot in database")

        except Exception as e:
            logger.error(f"Error registering bot: {e}")

    async def start(self):
        """Start the trading bot"""
        try:
            if not await self.initialize():
                logger.error("Failed to initialize bot, cannot start")
                return

            self.is_running = True
            self.stop_requested = False

            # Start main event loop
            main_task = asyncio.create_task(self.main_loop())

            # Start strategies
            strategy_tasks = []
            for symbol, strategy in self.strategies.items():
                task = asyncio.create_task(strategy.start())
                strategy_tasks.append(task)

            # Start event listener
            event_task = asyncio.create_task(self.listen_for_events())

            # Start heartbeat
            heartbeat_task = asyncio.create_task(self.heartbeat_loop())

            # Wait for completion
            await asyncio.gather(
                main_task,
                event_task,
                heartbeat_task,
                *strategy_tasks,
                return_exceptions=True
            )

        except Exception as e:
            logger.error(f"Error starting bot: {e}")
        finally:
            await self.cleanup()

    async def main_loop(self):
        """Main bot loop"""
        logger.info(f"Starting main loop for bot {self.name}")

        while self.is_running and not self.stop_requested:
            try:
                # Process events from queue
                await self.process_event_queue()

                # Check strategy health
                await self.check_strategy_health()

                # Update bot status
                await self.update_bot_status()

                # Short sleep to prevent CPU overload
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1)

        logger.info(f"Main loop stopped for bot {self.name}")

    async def process_event_queue(self):
        """Process events from the queue"""
        try:
            while not self.event_queue.empty():
                event = await self.event_queue.get()
                await self.handle_event(event)
                self.events_processed += 1

        except Exception as e:
            logger.error(f"Error processing event queue: {e}")

    async def handle_event(self, event: Dict):
        """Handle incoming events"""
        try:
            event_type = event.get('event_type', '')
            content = event.get('content', {})
            target_symbol = content.get('symbol', '')

            # Route event to appropriate strategy
            if target_symbol and target_symbol in self.strategies:
                strategy = self.strategies[target_symbol]
                await strategy.handle_event(event)
            elif not target_symbol:
                # Broadcast to all strategies
                for strategy in self.strategies.values():
                    await strategy.handle_event(event)
            else:
                logger.warning(f"No strategy found for symbol {target_symbol}")

        except Exception as e:
            logger.error(f"Error handling event: {e}")

    async def listen_for_events(self):
        """Listen for real-time events from Supabase"""
        logger.info(f"Starting event listener for bot {self.name}")

        while self.is_running and not self.stop_requested:
            try:
                # Get events from database
                events = await self.get_pending_events()

                for event in events:
                    await self.event_queue.put(event)

                    # Mark event as processed
                    await self.mark_event_processed(event.get('id'))

                # Wait before next check
                await asyncio.sleep(0.1)  # 100ms polling for real-time feel

            except Exception as e:
                logger.error(f"Error in event listener: {e}")
                await asyncio.sleep(1)

        logger.info(f"Event listener stopped for bot {self.name}")

    async def get_pending_events(self) -> List[Dict]:
        """Get pending events from database"""
        try:
            result = await self.supabase_client.execute_query(
                'select',
                table='events',
                filters={
                    'eq': {
                        'account': self.account_id,
                        'bot': self.id,
                        'processed': False
                    }
                },
                order={'created_at': True},
                limit=10
            )

            return result.data if result else []

        except Exception as e:
            logger.error(f"Error getting pending events: {e}")
            return []

    async def mark_event_processed(self, event_id: str):
        """Mark an event as processed"""
        try:
            await self.supabase_client.execute_query(
                'update',
                table='events',
                data={'processed': True,
                      'processed_at': datetime.utcnow().isoformat()},
                filters={'eq': {'id': event_id}}
            )

        except Exception as e:
            logger.error(f"Error marking event {event_id} as processed: {e}")

    async def check_strategy_health(self):
        """Check health of all strategies"""
        try:
            unhealthy_strategies = []

            for symbol, strategy in self.strategies.items():
                if not strategy.is_running or strategy.stop_requested:
                    unhealthy_strategies.append(symbol)

            # Restart unhealthy strategies
            for symbol in unhealthy_strategies:
                logger.warning(f"Restarting unhealthy strategy for {symbol}")
                await self.restart_strategy(symbol)

        except Exception as e:
            logger.error(f"Error checking strategy health: {e}")

    async def restart_strategy(self, symbol: str):
        """Restart a strategy for a specific symbol"""
        try:
            if symbol in self.strategies:
                # Stop old strategy
                old_strategy = self.strategies[symbol]
                await old_strategy.stop()

                # Create new strategy
                await self.create_strategy_for_symbol(symbol)

                # Start new strategy
                if symbol in self.strategies:
                    new_strategy = self.strategies[symbol]
                    asyncio.create_task(new_strategy.start())

        except Exception as e:
            logger.error(f"Error restarting strategy for {symbol}: {e}")

    async def update_bot_status(self):
        """Update bot status in database"""
        try:
            # Update every 30 seconds
            current_time = datetime.utcnow()
            if (current_time - self.last_heartbeat).seconds >= 30:

                status_data = {
                    'status': 'running' if self.is_running else 'stopped',
                    'last_heartbeat': current_time.isoformat(),
                    'events_processed': self.events_processed,
                    'active_symbols': list(self.strategies.keys()),
                    'updated_at': current_time.isoformat()
                }

                await self.supabase_client.execute_query(
                    'update',
                    table='bots',
                    data=status_data,
                    filters={'eq': {'id': self.id}}
                )

                self.last_heartbeat = current_time

        except Exception as e:
            logger.error(f"Error updating bot status: {e}")

    async def heartbeat_loop(self):
        """Send periodic heartbeat to show bot is alive"""
        logger.info(f"Starting heartbeat loop for bot {self.name}")

        while self.is_running and not self.stop_requested:
            try:
                # Send heartbeat event
                await self.send_heartbeat_event()

                # Wait 60 seconds before next heartbeat
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(60)

        logger.info(f"Heartbeat loop stopped for bot {self.name}")

    async def send_heartbeat_event(self):
        """Send heartbeat event"""
        try:
            # Get performance stats
            stats = await self.get_performance_stats()

            event_data = {
                'uuid': f"heartbeat_{datetime.utcnow().timestamp()}_{self.id}",
                'account': self.account_id,
                'bot': self.id,
                'strategy': self.strategy_id,
                'event_type': 'HEARTBEAT',
                'content': {
                    'bot_name': self.name,
                    'status': 'running',
                    'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds(),
                    'events_processed': self.events_processed,
                    'active_strategies': len(self.strategies),
                    'performance_stats': stats
                },
                'severity': 'INFO',
                'created_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.create_event(event_data)

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

    async def get_performance_stats(self) -> Dict:
        """Get bot performance statistics"""
        try:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

            # Get strategy stats
            strategy_stats = {}
            for symbol, strategy in self.strategies.items():
                strategy_stats[symbol] = {
                    'is_running': strategy.is_running,
                    'active_cycles': len(strategy.active_cycles),
                    'active_orders': len(strategy.active_orders),
                    'update_count': getattr(strategy, 'update_count', 0)
                }

            return {
                'uptime_seconds': uptime,
                'events_processed': self.events_processed,
                'events_per_minute': (self.events_processed / max(uptime / 60, 1)) if uptime > 0 else 0,
                'connection_status': self.connection_status,
                'strategy_stats': strategy_stats
            }

        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}

    async def stop(self):
        """Stop the trading bot gracefully"""
        logger.info(f"Stopping bot {self.name}")

        self.stop_requested = True
        self.is_running = False

        # Stop all strategies
        for symbol, strategy in self.strategies.items():
            try:
                await strategy.stop()
                logger.info(f"Strategy for {symbol} stopped")
            except Exception as e:
                logger.error(f"Error stopping strategy for {symbol}: {e}")

        # Update bot status in database
        try:
            await self.supabase_client.execute_query(
                'update',
                table='bots',
                data={
                    'status': 'stopped',
                    'stopped_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                },
                filters={'eq': {'id': self.id}}
            )
        except Exception as e:
            logger.error(f"Error updating bot status on stop: {e}")

        logger.info(f"Bot {self.name} stopped")

    async def cleanup(self):
        """Clean up resources"""
        try:
            # Send final status update
            await self.send_shutdown_event()

            # Clear strategies
            self.strategies.clear()

            # Update connection status
            self.connection_status = 'disconnected'

            logger.info(f"Bot {self.name} cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def send_shutdown_event(self):
        """Send shutdown event"""
        try:
            final_stats = await self.get_performance_stats()

            event_data = {
                'uuid': f"shutdown_{datetime.utcnow().timestamp()}_{self.id}",
                'account': self.account_id,
                'bot': self.id,
                'strategy': self.strategy_id,
                'event_type': 'BOT_SHUTDOWN',
                'content': {
                    'bot_name': self.name,
                    'shutdown_reason': 'graceful_stop',
                    'final_stats': final_stats
                },
                'severity': 'INFO',
                'created_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.create_event(event_data)

        except Exception as e:
            logger.error(f"Error sending shutdown event: {e}")

    # Public API methods for external control

    async def send_command(self, command: str, symbol: str = None, **kwargs):
        """Send a command to the bot or specific strategy"""
        try:
            event_data = {
                'uuid': f"command_{datetime.utcnow().timestamp()}_{self.id}",
                'account': self.account_id,
                'bot': self.id,
                'strategy': self.strategy_id,
                'event_type': 'COMMAND',
                'content': {
                    'message': command,
                    'symbol': symbol,
                    **kwargs
                },
                'severity': 'INFO',
                'processed': False,
                'created_at': datetime.utcnow().isoformat()
            }

            # Insert event directly into database
            await self.supabase_client.create_event(event_data)

            logger.info(f"Command '{command}' sent to bot {self.name}")

        except Exception as e:
            logger.error(f"Error sending command: {e}")

    async def get_status(self) -> Dict:
        """Get current bot status"""
        try:
            stats = await self.get_performance_stats()

            return {
                'id': self.id,
                'name': self.name,
                'account_id': self.account_id,
                'user_id': self.user_id,
                'strategy_type': self.strategy_type,
                'is_running': self.is_running,
                'connection_status': self.connection_status,
                'active_symbols': list(self.strategies.keys()),
                'start_time': self.start_time.isoformat(),
                'performance_stats': stats
            }

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {'error': str(e)}
