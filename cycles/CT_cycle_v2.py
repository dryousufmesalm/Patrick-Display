"""
CycleTrader Cycle Class - Real-Time Supabase Integration
Refactored for direct Supabase operations without PocketBase dependencies
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class CTCycleV2:
    """
    CycleTrader Cycle with direct Supabase integration
    Optimized for real-time performance and sub-second updates
    """

    def __init__(self, supabase_client, meta_trader, bot, cycle_data: Dict = None):
        self.supabase_client = supabase_client
        self.meta_trader = meta_trader
        self.bot = bot
        self.logger = logger

        # Core cycle properties
        self.id = cycle_data.get('id', '') if cycle_data else ''
        self.bot_id = cycle_data.get('bot', '') if cycle_data else bot.id
        self.account = cycle_data.get(
            'account', '') if cycle_data else bot.account_id
        self.symbol = cycle_data.get('symbol', '') if cycle_data else ''
        self.cycle_type = cycle_data.get(
            'cycle_type', 'BUY') if cycle_data else 'BUY'

        # Status and bounds
        self.is_closed = cycle_data.get(
            'is_closed', False) if cycle_data else False
        self.is_pending = cycle_data.get(
            'is_pending', False) if cycle_data else False
        self.status = cycle_data.get(
            'status', 'initial') if cycle_data else 'initial'
        self.lower_bound = cycle_data.get(
            'lower_bound', 0) if cycle_data else 0
        self.upper_bound = cycle_data.get(
            'upper_bound', 0) if cycle_data else 0

        # Trading metrics
        self.total_profit = cycle_data.get(
            'total_profit', 0) if cycle_data else 0
        self.total_volume = cycle_data.get(
            'total_volume', 0) if cycle_data else 0
        self.lot_idx = cycle_data.get('lot_idx', 0) if cycle_data else 0
        self.zone_index = cycle_data.get('zone_index', 0) if cycle_data else 0

        # Order arrays - stored as order IDs for Supabase
        self.initial_orders = cycle_data.get(
            'initial_orders', []) if cycle_data else []
        self.hedge_orders = cycle_data.get(
            'hedge_orders', []) if cycle_data else []
        self.recovery_orders = cycle_data.get(
            'recovery_orders', []) if cycle_data else []
        self.pending_orders = cycle_data.get(
            'pending_orders', []) if cycle_data else []
        self.threshold_orders = cycle_data.get(
            'threshold_orders', []) if cycle_data else []
        self.closed_orders = cycle_data.get(
            'closed_orders', []) if cycle_data else []

        # Threshold system for CT strategy
        self.threshold_upper = cycle_data.get(
            'threshold_upper', 0) if cycle_data else 0
        self.threshold_lower = cycle_data.get(
            'threshold_lower', 0) if cycle_data else 0
        self.base_threshold_upper = cycle_data.get(
            'base_threshold_upper', 0) if cycle_data else 0
        self.base_threshold_lower = cycle_data.get(
            'base_threshold_lower', 0) if cycle_data else 0

        # Zone forward system
        self.done_price_levels = cycle_data.get(
            'done_price_levels', []) if cycle_data else []
        self.current_direction = cycle_data.get(
            'current_direction', 'BUY') if cycle_data else 'BUY'
        self.initial_threshold_price = cycle_data.get(
            'initial_threshold_price', 0) if cycle_data else 0
        self.direction_switched = cycle_data.get(
            'direction_switched', False) if cycle_data else False
        self.next_order_index = cycle_data.get(
            'next_order_index', 0) if cycle_data else 0

        # Metadata
        self.closing_method = cycle_data.get(
            'closing_method', {}) if cycle_data else {}
        self.opened_by = cycle_data.get('opened_by', {}) if cycle_data else {}
        self.created_at = cycle_data.get('created_at', datetime.utcnow(
        ).isoformat()) if cycle_data else datetime.utcnow().isoformat()
        self.updated_at = cycle_data.get('updated_at', datetime.utcnow(
        ).isoformat()) if cycle_data else datetime.utcnow().isoformat()

        # Performance optimization
        self._orders_cache = {}  # Cache order data to reduce DB calls
        self._last_cache_update = None

    async def create_cycle(self) -> str:
        """Create cycle in Supabase with real-time updates"""
        try:
            cycle_data = self.to_supabase_dict()

            # Insert into Supabase
            result = await self.supabase_client.table('cycles').insert(cycle_data).execute()

            if result.data:
                self.id = result.data[0]['id']
                self.logger.info(
                    f"Created CT cycle {self.id} for {self.symbol}")

                # Send real-time event
                await self.send_event('CT_CYCLE_CREATED', {
                    'cycle_id': self.id,
                    'symbol': self.symbol,
                    'cycle_type': self.cycle_type
                })

                return self.id
            else:
                self.logger.error("Failed to create cycle in Supabase")
                return None

        except Exception as e:
            self.logger.error(f"Error creating CT cycle: {e}")
            return None

    async def update_cycle(self, updates: Dict = None):
        """Update cycle in Supabase with real-time sync"""
        try:
            if not self.id:
                self.logger.warning("Cannot update cycle without ID")
                return False

            # Calculate current profit and volume from orders
            await self.calculate_metrics()

            # Prepare update data
            update_data = {
                'total_profit': self.total_profit,
                'total_volume': self.total_volume,
                'status': self.status,
                'threshold_upper': self.threshold_upper,
                'threshold_lower': self.threshold_lower,
                'updated_at': datetime.utcnow().isoformat()
            }

            # Add any additional updates
            if updates:
                update_data.update(updates)

            # Update in Supabase
            result = await self.supabase_client.table('cycles').update(update_data).eq('id', self.id).execute()

            if result.data:
                # Update local properties
                for key, value in update_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

                # Send real-time event
                await self.send_event('CT_CYCLE_UPDATED', {
                    'cycle_id': self.id,
                    'updates': update_data
                })

                return True
            else:
                self.logger.error(f"Failed to update cycle {self.id}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating CT cycle {self.id}: {e}")
            return False

    async def close_cycle(self, sent_by_admin: bool = False, user_id: str = "", username: str = ""):
        """Close cycle with real-time updates"""
        try:
            # Calculate final profit
            await self.calculate_metrics()

            # Close all open orders first
            await self.close_all_orders()

            # Update cycle as closed
            closing_data = {
                'is_closed': True,
                'status': 'closed',
                'total_profit': self.total_profit,
                'closing_method': {
                    'sent_by_admin': sent_by_admin,
                    'user_id': user_id,
                    'username': username,
                    'closed_at': datetime.utcnow().isoformat()
                },
                'updated_at': datetime.utcnow().isoformat()
            }

            result = await self.supabase_client.table('cycles').update(closing_data).eq('id', self.id).execute()

            if result.data:
                self.is_closed = True
                self.status = 'closed'
                self.closing_method = closing_data['closing_method']

                # Send real-time event
                await self.send_event('CT_CYCLE_CLOSED', {
                    'cycle_id': self.id,
                    'symbol': self.symbol,
                    'final_profit': self.total_profit,
                    'closed_by': username
                })

                self.logger.info(
                    f"Closed CT cycle {self.id} with profit {self.total_profit}")
                return True
            else:
                self.logger.error(f"Failed to close cycle {self.id}")
                return False

        except Exception as e:
            self.logger.error(f"Error closing CT cycle {self.id}: {e}")
            return False

    async def add_order(self, order_id: str, order_type: str = "initial"):
        """Add order to appropriate list and update in Supabase"""
        try:
            # Add to appropriate list
            if order_type == "initial":
                self.initial_orders.append(order_id)
                self.status = "initial"
            elif order_type == "hedge":
                self.hedge_orders.append(order_id)
                self.status = "hedge"
            elif order_type == "recovery":
                self.recovery_orders.append(order_id)
                self.status = "recovery"
            elif order_type == "pending":
                self.pending_orders.append(order_id)
                self.status = "pending"
            elif order_type == "threshold":
                self.threshold_orders.append(order_id)
                self.status = "threshold"

            # Update in Supabase
            update_data = {
                'initial_orders': self.initial_orders,
                'hedge_orders': self.hedge_orders,
                'recovery_orders': self.recovery_orders,
                'pending_orders': self.pending_orders,
                'threshold_orders': self.threshold_orders,
                'status': self.status,
                'updated_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.table('cycles').update(update_data).eq('id', self.id).execute()

            # Clear cache to force refresh
            self._orders_cache = {}

            self.logger.info(
                f"Added {order_type} order {order_id} to cycle {self.id}")

        except Exception as e:
            self.logger.error(f"Error adding order to cycle: {e}")

    async def remove_order(self, order_id: str):
        """Remove order from all lists and update in Supabase"""
        try:
            removed = False

            # Remove from all lists
            if order_id in self.initial_orders:
                self.initial_orders.remove(order_id)
                removed = True
            if order_id in self.hedge_orders:
                self.hedge_orders.remove(order_id)
                removed = True
            if order_id in self.recovery_orders:
                self.recovery_orders.remove(order_id)
                removed = True
            if order_id in self.pending_orders:
                self.pending_orders.remove(order_id)
                removed = True
            if order_id in self.threshold_orders:
                self.threshold_orders.remove(order_id)
                removed = True

            if removed:
                # Add to closed orders
                self.closed_orders.append(order_id)

                # Update in Supabase
                update_data = {
                    'initial_orders': self.initial_orders,
                    'hedge_orders': self.hedge_orders,
                    'recovery_orders': self.recovery_orders,
                    'pending_orders': self.pending_orders,
                    'threshold_orders': self.threshold_orders,
                    'closed_orders': self.closed_orders,
                    'updated_at': datetime.utcnow().isoformat()
                }

                await self.supabase_client.table('cycles').update(update_data).eq('id', self.id).execute()

                # Clear cache
                self._orders_cache = {}

                self.logger.info(
                    f"Removed order {order_id} from cycle {self.id}")

        except Exception as e:
            self.logger.error(f"Error removing order from cycle: {e}")

    async def get_all_orders(self, include_closed: bool = False) -> List[str]:
        """Get all order IDs for this cycle"""
        orders = (self.initial_orders + self.hedge_orders + self.recovery_orders +
                  self.pending_orders + self.threshold_orders)

        if include_closed:
            orders.extend(self.closed_orders)

        return orders

    async def get_orders_by_type(self, order_type: str) -> List[str]:
        """Get orders by type"""
        type_map = {
            'initial': self.initial_orders,
            'hedge': self.hedge_orders,
            'recovery': self.recovery_orders,
            'pending': self.pending_orders,
            'threshold': self.threshold_orders,
            'closed': self.closed_orders
        }

        return type_map.get(order_type, [])

    async def calculate_metrics(self):
        """Calculate total profit and volume from all orders"""
        try:
            all_order_ids = await self.get_all_orders(include_closed=True)

            if not all_order_ids:
                self.total_profit = 0
                self.total_volume = 0
                return

            # Get orders from Supabase
            orders_result = await self.supabase_client.table('orders').select('*').in_('id', all_order_ids).execute()

            total_profit = 0
            total_volume = 0

            for order in orders_result.data:
                total_profit += order.get('profit', 0)
                total_volume += order.get('volume', 0)

            self.total_profit = round(total_profit, 2)
            self.total_volume = round(total_volume, 2)

        except Exception as e:
            self.logger.error(f"Error calculating metrics: {e}")
            self.total_profit = 0
            self.total_volume = 0

    async def close_all_orders(self):
        """Close all open orders for this cycle"""
        try:
            open_order_ids = await self.get_all_orders(include_closed=False)

            for order_id in open_order_ids:
                # Get order data
                order_result = await self.supabase_client.table('orders').select('*').eq('id', order_id).execute()

                if order_result.data:
                    order = order_result.data[0]
                    ticket = order.get('order_data', {}).get('ticket')

                    if ticket:
                        # Close order in MetaTrader
                        success = self.meta_trader.close_order(ticket)

                        if success:
                            # Update order status in database
                            await self.supabase_client.table('orders').update({
                                'status': 'CLOSED',
                                'updated_at': datetime.utcnow().isoformat()
                            }).eq('id', order_id).execute()

                            # Move to closed orders
                            await self.remove_order(order_id)

        except Exception as e:
            self.logger.error(f"Error closing all orders: {e}")

    async def manage_cycle_orders(self, threshold: float, threshold2: float):
        """Main order management logic for CT strategy"""
        try:
            # Check if cycle is closed
            if self.is_closed:
                return

            # Get current price
            current_price = self.meta_trader.get_ask(
                self.symbol) if self.cycle_type == 'BUY' else self.meta_trader.get_bid(self.symbol)

            # Update metrics
            await self.calculate_metrics()

            # Handle threshold orders based on CT strategy logic
            await self.handle_threshold_orders(threshold, threshold2, current_price)

            # Handle zone forward logic
            await self.handle_zone_forward(current_price)

            # Update cycle
            await self.update_cycle()

        except Exception as e:
            self.logger.error(f"Error managing cycle orders: {e}")

    async def handle_threshold_orders(self, threshold: float, threshold2: float, current_price: float):
        """Handle threshold order logic"""
        try:
            # Implement threshold order logic based on the original CT strategy
            # This is simplified - you'll need to implement the full logic from the original

            if len(self.threshold_orders) < 10:  # Max threshold orders
                # Check if we need to place threshold orders
                pip_value = self.meta_trader.get_pips(self.symbol)
                threshold_distance = threshold * pip_value

                # Place threshold orders based on current position
                if self.cycle_type == 'BUY' and current_price <= (self.initial_threshold_price - threshold_distance):
                    await self.create_threshold_buy_order(current_price)
                elif self.cycle_type == 'SELL' and current_price >= (self.initial_threshold_price + threshold_distance):
                    await self.create_threshold_sell_order(current_price)

        except Exception as e:
            self.logger.error(f"Error handling threshold orders: {e}")

    async def handle_zone_forward(self, current_price: float):
        """Handle zone forward logic"""
        try:
            # Check if price level has been done before
            price_level = round(current_price, 4)

            if not self.should_skip_price_level(price_level, self.current_direction):
                # Mark price level as done
                self.mark_price_level_as_done(
                    price_level, self.current_direction)

                # Update in database
                await self.supabase_client.table('cycles').update({
                    'done_price_levels': self.done_price_levels,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', self.id).execute()

        except Exception as e:
            self.logger.error(f"Error handling zone forward: {e}")

    def mark_price_level_as_done(self, price_level: float, direction: str):
        """Mark price level as done"""
        level_key = f"{price_level}_{direction}"
        if level_key not in self.done_price_levels:
            self.done_price_levels.append(level_key)

    def should_skip_price_level(self, price_level: float, direction: str) -> bool:
        """Check if price level should be skipped"""
        level_key = f"{price_level}_{direction}"
        return level_key in self.done_price_levels

    async def create_threshold_buy_order(self, price: float):
        """Create threshold buy order"""
        try:
            # Implement buy order creation logic
            # This would integrate with your MetaTrader order creation
            self.logger.info(
                f"Creating threshold buy order at {price} for cycle {self.id}")
            # TODO: Implement actual order creation

        except Exception as e:
            self.logger.error(f"Error creating threshold buy order: {e}")

    async def create_threshold_sell_order(self, price: float):
        """Create threshold sell order"""
        try:
            # Implement sell order creation logic
            # This would integrate with your MetaTrader order creation
            self.logger.info(
                f"Creating threshold sell order at {price} for cycle {self.id}")
            # TODO: Implement actual order creation

        except Exception as e:
            self.logger.error(f"Error creating threshold sell order: {e}")

    async def check_take_profit(self, take_profit_amount: float) -> bool:
        """Check if cycle should be closed due to take profit"""
        try:
            await self.calculate_metrics()

            if self.total_profit >= take_profit_amount:
                await self.close_cycle(sent_by_admin=False, user_id="system", username="system")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking take profit: {e}")
            return False

    def to_supabase_dict(self) -> Dict:
        """Convert cycle to Supabase format"""
        return {
            'bot': self.bot_id,
            'account': self.account,
            'symbol': self.symbol,
            'cycle_type': self.cycle_type,
            'is_closed': self.is_closed,
            'is_pending': self.is_pending,
            'status': self.status,
            'lower_bound': self.lower_bound,
            'upper_bound': self.upper_bound,
            'total_profit': self.total_profit,
            'total_volume': self.total_volume,
            'lot_idx': self.lot_idx,
            'zone_index': self.zone_index,
            'initial_orders': self.initial_orders,
            'hedge_orders': self.hedge_orders,
            'recovery_orders': self.recovery_orders,
            'pending_orders': self.pending_orders,
            'threshold_orders': self.threshold_orders,
            'closed_orders': self.closed_orders,
            'threshold_upper': self.threshold_upper,
            'threshold_lower': self.threshold_lower,
            'base_threshold_upper': self.base_threshold_upper,
            'base_threshold_lower': self.base_threshold_lower,
            'done_price_levels': self.done_price_levels,
            'current_direction': self.current_direction,
            'initial_threshold_price': self.initial_threshold_price,
            'direction_switched': self.direction_switched,
            'next_order_index': self.next_order_index,
            'closing_method': self.closing_method,
            'opened_by': self.opened_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    async def send_event(self, event_type: str, content: Dict, severity: str = 'INFO'):
        """Send real-time event to Supabase"""
        try:
            event_data = {
                'uuid': f"{datetime.utcnow().timestamp()}_{self.bot.id}_{self.id}",
                'account': self.account,
                'bot': self.bot_id,
                'content': content,
                'event_type': event_type,
                'severity': severity,
                'created_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.table('events').insert(event_data).execute()

        except Exception as e:
            self.logger.error(f"Error sending event: {e}")

    def __str__(self):
        return f"CTCycle({self.id}, {self.symbol}, {self.cycle_type}, P&L: {self.total_profit})"

    def __repr__(self):
        return self.__str__()
