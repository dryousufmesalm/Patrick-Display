"""
AdaptiveHedging Cycle Class - Real-Time Supabase Integration
Refactored for direct Supabase operations without PocketBase dependencies
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class AHCycleV2:
    """
    AdaptiveHedging Cycle with direct Supabase integration
    Optimized for real-time hedge management and sub-second updates
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
            'cycle_type', 'HEDGE') if cycle_data else 'HEDGE'

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
        self.max_recovery_orders = cycle_data.get(
            'max_recovery_orders', []) if cycle_data else []
        self.closed_orders = cycle_data.get(
            'closed_orders', []) if cycle_data else []

        # Hedge-specific properties
        self.hedge_distance = cycle_data.get(
            'hedge_distance', 50) if cycle_data else 50  # pips
        self.hedge_levels = cycle_data.get(
            'hedge_levels', []) if cycle_data else []
        self.current_hedge_level = cycle_data.get(
            'current_hedge_level', 0) if cycle_data else 0
        self.max_hedge_levels = cycle_data.get(
            'max_hedge_levels', 6) if cycle_data else 6
        self.hedge_profit_target = cycle_data.get(
            'hedge_profit_target', 10) if cycle_data else 10
        self.hedge_activation_loss = cycle_data.get(
            'hedge_activation_loss', -5) if cycle_data else -5

        # Risk management
        self.max_drawdown = cycle_data.get(
            'max_drawdown', -100) if cycle_data else -100
        self.entry_price = cycle_data.get(
            'entry_price', 0) if cycle_data else 0
        self.initial_direction = cycle_data.get(
            'initial_direction', 'BUY') if cycle_data else 'BUY'

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
        """Create hedge cycle in Supabase with real-time updates"""
        try:
            cycle_data = self.to_supabase_dict()

            # Insert into Supabase
            result = await self.supabase_client.table('cycles').insert(cycle_data).execute()

            if result.data:
                self.id = result.data[0]['id']
                self.logger.info(
                    f"Created AH cycle {self.id} for {self.symbol}")

                # Initialize hedge levels
                await self.prepare_hedge_levels()

                # Send real-time event
                await self.send_event('AH_CYCLE_CREATED', {
                    'cycle_id': self.id,
                    'symbol': self.symbol,
                    'cycle_type': self.cycle_type,
                    'initial_direction': self.initial_direction,
                    'entry_price': self.entry_price
                })

                return self.id
            else:
                self.logger.error("Failed to create AH cycle in Supabase")
                return None

        except Exception as e:
            self.logger.error(f"Error creating AH cycle: {e}")
            return None

    async def prepare_hedge_levels(self):
        """Prepare hedge levels for this cycle"""
        try:
            pip_value = self.meta_trader.get_pips(self.symbol)
            hedge_distance_price = self.hedge_distance * pip_value

            # Calculate hedge levels based on initial direction
            hedge_levels = []

            for level in range(1, self.max_hedge_levels + 1):
                if self.initial_direction == 'BUY':
                    # For BUY, hedges are SELL orders below entry price
                    hedge_price = self.entry_price - \
                        (hedge_distance_price * level)
                    hedge_type = 'SELL'
                else:
                    # For SELL, hedges are BUY orders above entry price
                    hedge_price = self.entry_price + \
                        (hedge_distance_price * level)
                    hedge_type = 'BUY'

                # Progressive lot sizing (martingale)
                # 0.01, 0.02, 0.04, 0.08, etc.
                volume = 0.01 * (2 ** (level - 1))

                hedge_levels.append({
                    'level': level,
                    'price': round(hedge_price, 5),
                    'type': hedge_type,
                    'volume': round(volume, 2),
                    'activated': False,
                    'order_id': None
                })

            self.hedge_levels = hedge_levels

            # Update in database
            await self.supabase_client.table('cycles').update({
                'hedge_levels': self.hedge_levels,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', self.id).execute()

            self.logger.info(
                f"Prepared {len(hedge_levels)} hedge levels for cycle {self.id}")

        except Exception as e:
            self.logger.error(f"Error preparing hedge levels: {e}")

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
                'current_hedge_level': self.current_hedge_level,
                'hedge_levels': self.hedge_levels,
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

                return True
            else:
                self.logger.error(f"Failed to update AH cycle {self.id}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating AH cycle {self.id}: {e}")
            return False

    async def close_cycle(self, sent_by_admin: bool = False, user_id: str = "", username: str = ""):
        """Close hedge cycle with real-time updates"""
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
                await self.send_event('AH_CYCLE_CLOSED', {
                    'cycle_id': self.id,
                    'symbol': self.symbol,
                    'final_profit': self.total_profit,
                    'closed_by': username,
                    'hedge_levels_used': self.current_hedge_level
                })

                self.logger.info(
                    f"Closed AH cycle {self.id} with profit {self.total_profit}")
                return True
            else:
                self.logger.error(f"Failed to close AH cycle {self.id}")
                return False

        except Exception as e:
            self.logger.error(f"Error closing AH cycle {self.id}: {e}")
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
            elif order_type == "max_recovery":
                self.max_recovery_orders.append(order_id)
                self.status = "max_recovery"

            # Update in Supabase
            update_data = {
                'initial_orders': self.initial_orders,
                'hedge_orders': self.hedge_orders,
                'recovery_orders': self.recovery_orders,
                'pending_orders': self.pending_orders,
                'max_recovery_orders': self.max_recovery_orders,
                'status': self.status,
                'updated_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.table('cycles').update(update_data).eq('id', self.id).execute()

            # Clear cache to force refresh
            self._orders_cache = {}

            self.logger.info(
                f"Added {order_type} order {order_id} to AH cycle {self.id}")

        except Exception as e:
            self.logger.error(f"Error adding order to AH cycle: {e}")

    async def execute_hedge_level(self, level: int, current_price: float) -> bool:
        """Execute a specific hedge level"""
        try:
            if level > len(self.hedge_levels) or level < 1:
                self.logger.warning(f"Invalid hedge level {level}")
                return False

            hedge_data = self.hedge_levels[level - 1]

            if hedge_data['activated']:
                self.logger.warning(f"Hedge level {level} already activated")
                return False

            # Create hedge order
            order_data = {
                'type': hedge_data['type'],
                'price': current_price,  # Use current price for market order
                'volume': hedge_data['volume'],
                'magic': self.bot.magic,
                'sl': 0,
                'tp': 0,
                'slippage': 3,
                'status': 'EXECUTED',
                'order_type': 'hedge',
                'hedge_level': level
            }

            # Execute order in MetaTrader
            if hedge_data['type'] == 'BUY':
                mt_order = self.meta_trader.buy(
                    self.symbol, hedge_data['volume'], self.bot.magic,
                    0, 0, "PIPS", 3, f"hedge_level_{level}"
                )
            else:
                mt_order = self.meta_trader.sell(
                    self.symbol, hedge_data['volume'], self.bot.magic,
                    0, 0, "PIPS", 3, f"hedge_level_{level}"
                )

            if mt_order:
                order_data['ticket'] = mt_order.get('ticket')
                order_data['price'] = mt_order.get('price', current_price)

                # Create order in database
                order_result = await self.supabase_client.table('orders').insert({
                    'cycle': self.id,
                    'account': self.account,
                    'bot': self.bot_id,
                    'order_data': order_data,
                    'status': 'EXECUTED',
                    'type': hedge_data['type'],
                    'price': order_data['price'],
                    'volume': hedge_data['volume'],
                    'symbol': self.symbol,
                    'profit': 0,
                    'created_at': datetime.utcnow().isoformat()
                }).execute()

                if order_result.data:
                    order_id = order_result.data[0]['id']

                    # Mark hedge level as activated
                    hedge_data['activated'] = True
                    hedge_data['order_id'] = order_id
                    self.current_hedge_level = level

                    # Add to hedge orders
                    await self.add_order(order_id, "hedge")

                    # Update hedge levels in database
                    await self.supabase_client.table('cycles').update({
                        'hedge_levels': self.hedge_levels,
                        'current_hedge_level': self.current_hedge_level,
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('id', self.id).execute()

                    # Send real-time event
                    await self.send_event('HEDGE_LEVEL_EXECUTED', {
                        'cycle_id': self.id,
                        'hedge_level': level,
                        'order_id': order_id,
                        'price': order_data['price'],
                        'volume': hedge_data['volume'],
                        'type': hedge_data['type']
                    })

                    self.logger.info(
                        f"Executed hedge level {level} for cycle {self.id}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error executing hedge level {level}: {e}")
            return False

    async def check_hedge_triggers(self, current_price: float):
        """Check if any hedge levels should be triggered"""
        try:
            # Calculate current loss
            await self.calculate_metrics()

            # Check if loss threshold reached for automatic hedging
            if self.total_profit <= self.hedge_activation_loss:
                # Find next unactivated hedge level
                for hedge_data in self.hedge_levels:
                    if not hedge_data['activated']:
                        # Check if current price has reached hedge trigger
                        if self.initial_direction == 'BUY':
                            # For BUY positions, hedge when price drops
                            if current_price <= hedge_data['price']:
                                await self.execute_hedge_level(hedge_data['level'], current_price)
                                break
                        else:
                            # For SELL positions, hedge when price rises
                            if current_price >= hedge_data['price']:
                                await self.execute_hedge_level(hedge_data['level'], current_price)
                                break

            # Check for emergency closure
            if self.total_profit <= self.max_drawdown:
                await self.emergency_close()

        except Exception as e:
            self.logger.error(f"Error checking hedge triggers: {e}")

    async def emergency_close(self):
        """Emergency close cycle due to maximum drawdown"""
        try:
            await self.close_cycle(sent_by_admin=False, user_id="system", username="emergency_system")

            # Send emergency event
            await self.send_event('EMERGENCY_CYCLE_CLOSED', {
                'cycle_id': self.id,
                'reason': 'maximum_drawdown',
                'final_profit': self.total_profit,
                'hedge_levels_used': self.current_hedge_level
            }, 'ERROR')

            self.logger.warning(
                f"Emergency closed cycle {self.id} due to maximum drawdown")

        except Exception as e:
            self.logger.error(f"Error in emergency close: {e}")

    async def manage_cycle_orders(self):
        """Main order management logic for AH strategy"""
        try:
            # Check if cycle is closed
            if self.is_closed:
                return

            # Get current price
            current_price = self.meta_trader.get_ask(self.symbol)

            # Update metrics
            await self.calculate_metrics()

            # Check hedge triggers
            await self.check_hedge_triggers(current_price)

            # Check if cycle is profitable enough to close
            if self.total_profit >= self.hedge_profit_target:
                await self.close_cycle(sent_by_admin=False, user_id="system", username="auto_profit_target")

            # Update cycle
            await self.update_cycle()

        except Exception as e:
            self.logger.error(f"Error managing AH cycle orders: {e}")

    async def get_all_orders(self, include_closed: bool = False) -> List[str]:
        """Get all order IDs for this cycle"""
        orders = (self.initial_orders + self.hedge_orders + self.recovery_orders +
                  self.pending_orders + self.max_recovery_orders)

        if include_closed:
            orders.extend(self.closed_orders)

        return orders

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
            self.logger.error(f"Error calculating AH metrics: {e}")
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
                            if order_id not in self.closed_orders:
                                self.closed_orders.append(order_id)

                            # Remove from active lists
                            for order_list in [self.initial_orders, self.hedge_orders,
                                               self.recovery_orders, self.pending_orders,
                                               self.max_recovery_orders]:
                                if order_id in order_list:
                                    order_list.remove(order_id)

        except Exception as e:
            self.logger.error(f"Error closing all AH orders: {e}")

    async def check_take_profit(self, take_profit_amount: float) -> bool:
        """Check if cycle should be closed due to take profit"""
        try:
            await self.calculate_metrics()

            if self.total_profit >= take_profit_amount:
                await self.close_cycle(sent_by_admin=False, user_id="system", username="system")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking AH take profit: {e}")
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
            'max_recovery_orders': self.max_recovery_orders,
            'closed_orders': self.closed_orders,
            'hedge_distance': self.hedge_distance,
            'hedge_levels': self.hedge_levels,
            'current_hedge_level': self.current_hedge_level,
            'max_hedge_levels': self.max_hedge_levels,
            'hedge_profit_target': self.hedge_profit_target,
            'hedge_activation_loss': self.hedge_activation_loss,
            'max_drawdown': self.max_drawdown,
            'entry_price': self.entry_price,
            'initial_direction': self.initial_direction,
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
            self.logger.error(f"Error sending AH event: {e}")

    def __str__(self):
        return f"AHCycle({self.id}, {self.symbol}, {self.initial_direction}, Hedge Level: {self.current_hedge_level}, P&L: {self.total_profit})"

    def __repr__(self):
        return self.__str__()
