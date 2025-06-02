"""
Real-Time Order Manager - Supabase Integration
Manages all orders across strategies with direct Supabase operations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
import time

logger = logging.getLogger(__name__)


class OrdersManagerV2:
    """
    Real-time order manager with direct Supabase integration
    Handles order synchronization, tracking, and validation
    """

    def __init__(self, meta_trader, supabase_client, account_id: str, websocket_service=None):
        self.meta_trader = meta_trader
        self.supabase_client = supabase_client
        self.account_id = account_id
        self.websocket_service = websocket_service
        self.logger = logger

        # Order tracking
        self.mt5_orders = {}  # ticket -> position data
        self.db_orders = {}   # order_id -> order data
        self.suspicious_orders = []  # Orders in DB but not in MT5
        self.false_closed_orders = []  # Orders marked closed but still open

        # Performance optimization
        self.mt5_lock = threading.Lock()
        self.update_interval = 0.5  # 500ms for balance between performance and accuracy
        self.last_sync_time = datetime.utcnow()

        # Statistics
        self.sync_count = 0
        self.error_count = 0
        self.fixed_orders_count = 0

    async def start(self):
        """Start the order manager"""
        self.logger.info(
            f"Starting OrdersManagerV2 for account {self.account_id}")
        await self.run_order_manager()

    async def run_order_manager(self):
        """Main order management loop"""
        while True:
            try:
                start_time = datetime.utcnow()

                # Get orders from MT5 and Supabase
                await asyncio.gather(
                    self.load_mt5_orders(),
                    self.load_db_orders()
                )

                # Analyze discrepancies
                await self.identify_suspicious_orders()

                # Synchronize orders
                await asyncio.gather(
                    self.sync_orders_to_db(),
                    self.fix_suspicious_orders()
                )

                # Performance tracking
                self.sync_count += 1
                sync_duration = (datetime.utcnow() -
                                 start_time).total_seconds()

                if self.sync_count % 60 == 0:  # Log every 60 cycles
                    self.logger.info(
                        f"Order sync #{self.sync_count}: {len(self.mt5_orders)} MT5 orders, "
                        f"{len(self.db_orders)} DB orders, {len(self.suspicious_orders)} suspicious. "
                        f"Duration: {sync_duration:.3f}s"
                    )

                await asyncio.sleep(self.update_interval)

            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Error in order manager loop: {e}")
                await asyncio.sleep(2)  # Wait longer on error

    async def load_mt5_orders(self):
        """Load all orders from MT5"""
        try:
            with self.mt5_lock:
                positions = self.meta_trader.get_all_positions()

            self.mt5_orders = {}
            for position in positions:
                if hasattr(position, 'ticket'):
                    self.mt5_orders[position.ticket] = {
                        'ticket': position.ticket,
                        'symbol': getattr(position, 'symbol', ''),
                        'type': getattr(position, 'type', 0),
                        'volume': getattr(position, 'volume', 0),
                        'price_open': getattr(position, 'price_open', 0),
                        'price_current': getattr(position, 'price_current', 0),
                        'profit': getattr(position, 'profit', 0),
                        'swap': getattr(position, 'swap', 0),
                        'commission': getattr(position, 'commission', 0)
                    }

        except Exception as e:
            self.logger.error(f"Error loading MT5 orders: {e}")
            self.mt5_orders = {}

    async def load_db_orders(self):
        """Load all open orders from Supabase"""
        try:
            # Get all open orders for this account
            result = await self.supabase_client.table('orders').select(
                '*, cycle!inner(*)'
            ).eq('account', self.account_id).eq('status', 'EXECUTED').execute()

            self.db_orders = {}
            for order in result.data:
                order_data = order.get('order_data', {})
                ticket = order_data.get('ticket')

                if ticket:
                    self.db_orders[order['id']] = {
                        'id': order['id'],
                        'ticket': ticket,
                        'cycle_id': order['cycle'],
                        'symbol': order['symbol'],
                        'type': order['type'],
                        'volume': order['volume'],
                        'price': order['price'],
                        'profit': order['profit'],
                        'status': order['status'],
                        'order_data': order_data,
                        'created_at': order['created_at'],
                        'updated_at': order['updated_at']
                    }

        except Exception as e:
            self.logger.error(f"Error loading DB orders: {e}")
            self.db_orders = {}

    async def identify_suspicious_orders(self):
        """Identify orders that exist in DB but not in MT5"""
        try:
            mt5_tickets = set(self.mt5_orders.keys())
            db_tickets = {}

            # Map DB order IDs to tickets
            for order_id, order_data in self.db_orders.items():
                ticket = order_data.get('ticket')
                if ticket:
                    db_tickets[order_id] = ticket

            # Find suspicious orders (in DB but not in MT5)
            self.suspicious_orders = []
            for order_id, ticket in db_tickets.items():
                if ticket not in mt5_tickets:
                    self.suspicious_orders.append(order_id)

            # Find false closed orders (potentially closed in MT5 but still open in DB)
            self.false_closed_orders = self.suspicious_orders.copy()

        except Exception as e:
            self.logger.error(f"Error identifying suspicious orders: {e}")

    async def sync_orders_to_db(self):
        """Sync order profits and status from MT5 to database"""
        try:
            update_tasks = []

            for order_id, order_data in self.db_orders.items():
                ticket = order_data.get('ticket')
                if ticket in self.mt5_orders:
                    mt5_data = self.mt5_orders[ticket]

                    # Calculate current profit
                    current_profit = mt5_data.get(
                        'profit', 0) + mt5_data.get('swap', 0) + mt5_data.get('commission', 0)

                    # Check if profit has changed significantly
                    db_profit = order_data.get('profit', 0)
                    if abs(current_profit - db_profit) >= 0.01:  # Update if change > 1 cent
                        update_tasks.append(self.update_order_profit(
                            order_id, current_profit, mt5_data))

            # Execute all updates concurrently
            if update_tasks:
                await asyncio.gather(*update_tasks, return_exceptions=True)

        except Exception as e:
            self.logger.error(f"Error syncing orders to DB: {e}")

    async def update_order_profit(self, order_id: str, profit: float, mt5_data: Dict):
        """Update single order profit in database"""
        try:
            update_data = {
                'profit': round(profit, 2),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Also update order_data with latest MT5 info
            order_data = self.db_orders[order_id]['order_data'].copy()
            order_data.update({
                'current_price': mt5_data.get('price_current', 0),
                'profit': profit,
                'swap': mt5_data.get('swap', 0),
                'commission': mt5_data.get('commission', 0)
            })
            update_data['order_data'] = order_data

            # Update in Supabase
            result = await self.supabase_client.table('orders').update(update_data).eq('id', order_id).execute()

            if result.data:
                # Update local cache
                self.db_orders[order_id]['profit'] = profit
                self.db_orders[order_id]['order_data'] = order_data

                # Send real-time update via WebSocket
                if self.websocket_service:
                    try:
                        await self.websocket_service.send_order_update(self.account_id, {
                            'order_id': order_id,
                            'ticket': mt5_data.get('ticket'),
                            'profit': profit,
                            'price_current': mt5_data.get('price_current', 0),
                            'updated_at': datetime.utcnow().isoformat()
                        })
                    except Exception as e:
                        self.logger.error(
                            f"Error sending WebSocket order update: {e}")

        except Exception as e:
            self.logger.error(f"Error updating order {order_id} profit: {e}")

    async def fix_suspicious_orders(self):
        """Fix orders that appear closed in MT5 but open in DB"""
        try:
            fix_tasks = []

            for order_id in self.suspicious_orders:
                if order_id in self.db_orders:
                    fix_tasks.append(self.verify_and_fix_order(order_id))

            # Process suspicious orders
            if fix_tasks:
                results = await asyncio.gather(*fix_tasks, return_exceptions=True)
                fixed_count = sum(1 for result in results if result is True)

                if fixed_count > 0:
                    self.fixed_orders_count += fixed_count
                    self.logger.info(f"Fixed {fixed_count} suspicious orders")

        except Exception as e:
            self.logger.error(f"Error fixing suspicious orders: {e}")

    async def verify_and_fix_order(self, order_id: str) -> bool:
        """Verify if order is truly closed and fix its status"""
        try:
            order_data = self.db_orders[order_id]
            ticket = order_data.get('ticket')

            if not ticket:
                return False

            # Double-check with MT5
            with self.mt5_lock:
                is_closed = self.meta_trader.check_order_is_closed(ticket)

            if is_closed:
                # Order is confirmed closed in MT5, update database
                await self.close_order_in_db(order_id, ticket)

                # Send event for order closure
                await self.send_order_event('ORDER_CLOSED_BY_MT5', {
                    'order_id': order_id,
                    'ticket': ticket,
                    'symbol': order_data.get('symbol'),
                    'profit': order_data.get('profit', 0)
                })

                return True
            else:
                # Order is not closed, might be a temporary MT5 API issue
                self.logger.warning(
                    f"Order {ticket} not found in MT5 but not confirmed closed")
                return False

        except Exception as e:
            self.logger.error(f"Error verifying order {order_id}: {e}")
            return False

    async def close_order_in_db(self, order_id: str, ticket: int):
        """Close order in database and update cycle"""
        try:
            order_data = self.db_orders[order_id]
            cycle_id = order_data.get('cycle_id')

            # Get final profit from MT5 history
            final_profit = await self.get_closed_order_profit(ticket)

            # Update order status
            update_data = {
                'status': 'CLOSED',
                'profit': final_profit,
                'updated_at': datetime.utcnow().isoformat()
            }

            result = await self.supabase_client.table('orders').update(update_data).eq('id', order_id).execute()

            if result.data:
                # Remove from local cache
                if order_id in self.db_orders:
                    del self.db_orders[order_id]

                # Trigger cycle recalculation
                if cycle_id:
                    await self.trigger_cycle_recalculation(cycle_id)

        except Exception as e:
            self.logger.error(f"Error closing order {order_id} in DB: {e}")

    async def get_closed_order_profit(self, ticket: int) -> float:
        """Get final profit for a closed order from MT5 history"""
        try:
            with self.mt5_lock:
                # Try to get deal history for this ticket
                deals = self.meta_trader.get_deals_by_ticket(ticket)

            if deals:
                total_profit = sum(deal.get(
                    'profit', 0) + deal.get('swap', 0) + deal.get('commission', 0) for deal in deals)
                return round(total_profit, 2)
            else:
                # Fallback to last known profit if no deal history
                order_data = self.db_orders.get(next(
                    (oid for oid, od in self.db_orders.items() if od.get('ticket') == ticket), None), {})
                return order_data.get('profit', 0)

        except Exception as e:
            self.logger.error(
                f"Error getting closed order profit for {ticket}: {e}")
            return 0

    async def trigger_cycle_recalculation(self, cycle_id: str):
        """Trigger cycle profit recalculation after order status change"""
        try:
            # Send event to trigger cycle update
            await self.send_cycle_event('CYCLE_RECALCULATE_PROFIT', {
                'cycle_id': cycle_id,
                'trigger': 'order_closed'
            })

        except Exception as e:
            self.logger.error(f"Error triggering cycle recalculation: {e}")

    async def send_order_event(self, event_type: str, content: Dict, severity: str = 'INFO'):
        """Send order-related event to Supabase"""
        try:
            event_data = {
                'uuid': f"{datetime.utcnow().timestamp()}_{self.account_id}_order",
                'account': self.account_id,
                'content': content,
                'event_type': event_type,
                'severity': severity,
                'created_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.table('events').insert(event_data).execute()

        except Exception as e:
            self.logger.error(f"Error sending order event: {e}")

    async def send_cycle_event(self, event_type: str, content: Dict, severity: str = 'INFO'):
        """Send cycle-related event to Supabase"""
        try:
            event_data = {
                'uuid': f"{datetime.utcnow().timestamp()}_{self.account_id}_cycle",
                'account': self.account_id,
                'content': content,
                'event_type': event_type,
                'severity': severity,
                'created_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.table('events').insert(event_data).execute()

        except Exception as e:
            self.logger.error(f"Error sending cycle event: {e}")

    async def get_order_statistics(self) -> Dict:
        """Get order manager statistics"""
        return {
            'mt5_orders_count': len(self.mt5_orders),
            'db_orders_count': len(self.db_orders),
            'suspicious_orders_count': len(self.suspicious_orders),
            'total_syncs': self.sync_count,
            'total_errors': self.error_count,
            'fixed_orders': self.fixed_orders_count,
            'last_sync': self.last_sync_time.isoformat()
        }

    async def force_order_sync(self):
        """Force immediate order synchronization"""
        try:
            self.logger.info("Forcing immediate order sync")

            await asyncio.gather(
                self.load_mt5_orders(),
                self.load_db_orders()
            )

            await self.identify_suspicious_orders()

            await asyncio.gather(
                self.sync_orders_to_db(),
                self.fix_suspicious_orders()
            )

            self.logger.info("Force sync completed")

        except Exception as e:
            self.logger.error(f"Error in force sync: {e}")

    async def close_order_by_ticket(self, ticket: int) -> bool:
        """Close specific order by ticket"""
        try:
            with self.mt5_lock:
                success = self.meta_trader.close_order(ticket)

            if success:
                # Find and update the order in database
                for order_id, order_data in self.db_orders.items():
                    if order_data.get('ticket') == ticket:
                        await self.close_order_in_db(order_id, ticket)
                        break

                await self.send_order_event('ORDER_MANUALLY_CLOSED', {
                    'ticket': ticket,
                    'success': True
                })

                return True
            else:
                await self.send_order_event('ORDER_CLOSE_FAILED', {
                    'ticket': ticket,
                    'success': False
                }, 'ERROR')

                return False

        except Exception as e:
            self.logger.error(f"Error closing order {ticket}: {e}")
            return False

    async def get_orders_by_cycle(self, cycle_id: str) -> List[Dict]:
        """Get all orders for a specific cycle"""
        cycle_orders = []
        for order_data in self.db_orders.values():
            if order_data.get('cycle_id') == cycle_id:
                cycle_orders.append(order_data)
        return cycle_orders

    async def get_orders_by_symbol(self, symbol: str) -> List[Dict]:
        """Get all orders for a specific symbol"""
        symbol_orders = []
        for order_data in self.db_orders.values():
            if order_data.get('symbol') == symbol:
                symbol_orders.append(order_data)
        return symbol_orders

    def __str__(self):
        return f"OrdersManagerV2(account={self.account_id}, mt5_orders={len(self.mt5_orders)}, db_orders={len(self.db_orders)})"

    def __repr__(self):
        return self.__str__()
