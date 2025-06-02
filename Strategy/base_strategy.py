"""
Base Strategy Class for Real-Time Supabase Integration
Provides common functionality for all trading strategies
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    Provides real-time Supabase integration and common functionality
    """

    def __init__(self, meta_trader, config: Dict, supabase_client, symbol: str, bot):
        self.meta_trader = meta_trader
        self.config = config
        self.supabase_client = supabase_client
        self.symbol = symbol
        self.bot = bot
        self.logger = logger
        self.is_running = False
        self.stop_requested = False

        # Performance tracking
        self.last_update = datetime.utcnow()
        self.update_count = 0

        # Real-time state
        self.active_cycles: Dict[str, Any] = {}
        self.active_orders: Dict[str, Any] = {}

        # Add stop flag for compatibility with old code
        self.stop = False

    async def initialize(self) -> bool:
        """Initialize the strategy with database sync"""
        try:
            # Load configuration from database
            await self.load_config_from_db()

            # Load active cycles and orders
            await self.load_active_state()

            # Initialize strategy-specific settings
            await self.init_strategy_settings()

            self.logger.info(
                f"Strategy {self.__class__.__name__} initialized for {self.symbol}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize strategy: {e}")
            return False

    async def load_config_from_db(self):
        """Load bot configuration from Supabase"""
        try:
            # Get bot configuration
            result = await self.supabase_client.table('bot-configs').select('*').eq(
                'user', self.bot.user_id
            ).eq('name', f"{self.symbol}_{self.__class__.__name__}").execute()

            if result.data:
                db_config = result.data[0]['configs']
                # Update config with database values
                self.config.update(db_config)
                self.logger.info(
                    f"Loaded configuration from database for {self.symbol}")
            else:
                # Create default configuration
                await self.save_config_to_db()

        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")

    async def save_config_to_db(self):
        """Save current configuration to database"""
        try:
            config_data = {
                'name': f"{self.symbol}_{self.__class__.__name__}",
                'user': self.bot.user_id,
                'strategy': self.bot.strategy_id,
                'configs': self.config,
                'by_admin': False
            }

            await self.supabase_client.table('bot-configs').upsert(config_data).execute()
            self.logger.info(
                f"Saved configuration to database for {self.symbol}")

        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")

    async def load_active_state(self):
        """Load active cycles and orders from database"""
        try:
            # Load active cycles
            cycles_result = await self.supabase_client.table('cycles').select(
                '*, orders(*)'
            ).eq('account', self.bot.account_id).eq('bot', self.bot.id).eq('is_closed', False).execute()

            for cycle_data in cycles_result.data:
                self.active_cycles[cycle_data['id']] = cycle_data

                # Load orders for this cycle
                for order_data in cycle_data.get('orders', []):
                    self.active_orders[order_data['id']] = order_data

            self.logger.info(
                f"Loaded {len(self.active_cycles)} active cycles, {len(self.active_orders)} active orders")

        except Exception as e:
            self.logger.error(f"Error loading active state: {e}")

    async def create_cycle(self, order1_data: Dict, order2_data: Optional[Dict] = None,
                           cycle_type: str = "BUY", is_pending: bool = False) -> str:
        """Create a new trading cycle with real-time updates"""
        try:
            cycle_data = {
                'account': self.bot.account_id,
                'bot': self.bot.id,
                'symbol': self.symbol,
                'cycle_type': cycle_type,
                'is_closed': False,
                'is_favorite': False,
                'total_volume': order1_data.get('volume', 0),
                'total_profit': 0,
                'use_pending_orders': is_pending,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Insert cycle
            cycle_result = await self.supabase_client.table('cycles').insert(cycle_data).execute()
            cycle_id = cycle_result.data[0]['id']

            # Create primary order
            await self.create_order(cycle_id, order1_data)

            # Create secondary order if provided
            if order2_data:
                await self.create_order(cycle_id, order2_data)

            # Update local state
            cycle_data['id'] = cycle_id
            self.active_cycles[cycle_id] = cycle_data

            # Send real-time event
            await self.send_event('CYCLE_CREATED', {
                'cycle_id': cycle_id,
                'symbol': self.symbol,
                'type': cycle_type
            })

            self.logger.info(f"Created cycle {cycle_id} for {self.symbol}")
            return cycle_id

        except Exception as e:
            self.logger.error(f"Error creating cycle: {e}")
            return None

    async def create_order(self, cycle_id: str, order_data: Dict) -> str:
        """Create a new order with real-time updates"""
        try:
            order_record = {
                'cycle': cycle_id,
                'account': self.bot.account_id,
                'bot': self.bot.id,
                'strategy': self.bot.strategy_id,
                'order_data': order_data,
                'status': order_data.get('status', 'PENDING'),
                'type': order_data.get('type', 'BUY'),
                'price': order_data.get('price', 0),
                'volume': order_data.get('volume', 0),
                'symbol': self.symbol,
                'profit': order_data.get('profit', 0),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Insert order
            order_result = await self.supabase_client.table('orders').insert(order_record).execute()
            order_id = order_result.data[0]['id']

            # Update local state
            order_record['id'] = order_id
            self.active_orders[order_id] = order_record

            # Send real-time event
            await self.send_event('ORDER_CREATED', {
                'order_id': order_id,
                'cycle_id': cycle_id,
                'symbol': self.symbol,
                'type': order_data.get('type'),
                'price': order_data.get('price'),
                'volume': order_data.get('volume')
            })

            return order_id

        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            return None

    async def update_cycle(self, cycle_id: str, updates: Dict):
        """Update cycle with real-time sync"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()

            # Update database
            await self.supabase_client.table('cycles').update(updates).eq('id', cycle_id).execute()

            # Update local state
            if cycle_id in self.active_cycles:
                self.active_cycles[cycle_id].update(updates)

            # Send real-time event
            await self.send_event('CYCLE_UPDATED', {
                'cycle_id': cycle_id,
                'updates': updates
            })

        except Exception as e:
            self.logger.error(f"Error updating cycle {cycle_id}: {e}")

    async def close_cycle(self, cycle_id: str, profit: float = 0):
        """Close a cycle with real-time updates"""
        try:
            updates = {
                'is_closed': True,
                'total_profit': profit,
                'updated_at': datetime.utcnow().isoformat()
            }

            await self.update_cycle(cycle_id, updates)

            # Remove from active cycles
            if cycle_id in self.active_cycles:
                del self.active_cycles[cycle_id]

            # Send real-time event
            await self.send_event('CYCLE_CLOSED', {
                'cycle_id': cycle_id,
                'profit': profit
            })

            self.logger.info(f"Closed cycle {cycle_id} with profit {profit}")

        except Exception as e:
            self.logger.error(f"Error closing cycle {cycle_id}: {e}")

    async def send_event(self, event_type: str, content: Dict, severity: str = 'INFO'):
        """Send real-time event to Supabase"""
        try:
            event_data = {
                'uuid': f"{datetime.utcnow().timestamp()}_{self.bot.id}",
                'account': self.bot.account_id,
                'bot': self.bot.id,
                'strategy': self.bot.strategy_id,
                'content': content,
                'event_type': event_type,
                'severity': severity,
                'created_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.table('events').insert(event_data).execute()

        except Exception as e:
            self.logger.error(f"Error sending event: {e}")

    async def handle_connection_failure(self, operation: str, retry_count: int = 3):
        """Handle Supabase connection failures with exponential backoff"""
        for attempt in range(retry_count):
            try:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

                # Test connection
                await self.supabase_client.table('meta-trader-accounts').select('id').limit(1).execute()

                self.logger.info(
                    f"Connection restored after {attempt + 1} attempts")
                return True

            except Exception as e:
                self.logger.warning(
                    f"Connection attempt {attempt + 1} failed: {e}")

                if attempt == retry_count - 1:
                    self.logger.error(
                        f"Failed to restore connection after {retry_count} attempts")
                    # Send emergency stop signal
                    self.stop_requested = True
                    return False

        return False

    @abstractmethod
    async def init_strategy_settings(self):
        """Initialize strategy-specific settings (to be implemented by subclasses)"""
        pass

    @abstractmethod
    async def handle_event(self, event: Dict):
        """Handle incoming events (to be implemented by subclasses)"""
        pass

    @abstractmethod
    async def run(self):
        """Main strategy loop (to be implemented by subclasses)"""
        pass

    async def start(self):
        """Start the strategy"""
        if await self.initialize():
            self.is_running = True
            self.stop_requested = False
            await self.run()

    async def stop_strategy(self):
        """Stop the strategy gracefully"""
        self.stop_requested = True
        self.is_running = False

        # Save final state
        await self.save_config_to_db()

        self.logger.info(
            f"Strategy {self.__class__.__name__} stopped for {self.symbol}")
