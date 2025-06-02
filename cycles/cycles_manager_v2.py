"""
Real-Time Cycles Manager - Supabase Integration
Manages all cycles across strategies with direct Supabase operations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from cycles.CT_cycle_v2 import CTCycleV2
from cycles.AH_cycle_v2 import AHCycleV2

logger = logging.getLogger(__name__)


class CyclesManagerV2:
    """
    Real-time cycles manager with direct Supabase integration
    Handles cycle synchronization, validation, and lifecycle management
    """

    def __init__(self, meta_trader, supabase_client, account_id: str, orders_manager, websocket_service=None):
        self.meta_trader = meta_trader
        self.supabase_client = supabase_client
        self.account_id = account_id
        self.orders_manager = orders_manager
        self.websocket_service = websocket_service
        self.logger = logger

        # Cycle tracking
        self.active_cycles = {}  # cycle_id -> cycle object
        self.ct_cycles = {}      # cycle_id -> CTCycleV2 object
        self.ah_cycles = {}      # cycle_id -> AHCycleV2 object
        self.closed_cycles_buffer = {}  # Recently closed cycles for validation

        # Performance optimization
        # 1 second for cycles (less frequent than orders)
        self.update_interval = 1.0
        self.last_sync_time = datetime.utcnow()
        self.validation_interval = 30  # Validate cycle integrity every 30 seconds
        self.last_validation_time = datetime.utcnow()

        # Statistics
        self.sync_count = 0
        self.error_count = 0
        self.fixed_cycles_count = 0
        self.cycles_created = 0
        self.cycles_closed = 0

    async def start(self):
        """Start the cycles manager"""
        self.logger.info(
            f"Starting CyclesManagerV2 for account {self.account_id}")
        await self.run_cycles_manager()

    async def run_cycles_manager(self):
        """Main cycles management loop"""
        while True:
            try:
                start_time = datetime.utcnow()

                # Load and sync cycles
                await asyncio.gather(
                    self.load_active_cycles(),
                    self.sync_cycle_profits(),
                    self.validate_cycle_integrity()
                )

                # Check for incorrectly closed cycles
                if (datetime.utcnow() - self.last_validation_time).seconds >= self.validation_interval:
                    await self.fix_incorrectly_closed_cycles()
                    self.last_validation_time = datetime.utcnow()

                # Performance tracking
                self.sync_count += 1
                sync_duration = (datetime.utcnow() -
                                 start_time).total_seconds()

                if self.sync_count % 30 == 0:  # Log every 30 cycles
                    self.logger.info(
                        f"Cycle sync #{self.sync_count}: {len(self.active_cycles)} active cycles "
                        f"({len(self.ct_cycles)} CT, {len(self.ah_cycles)} AH). "
                        f"Duration: {sync_duration:.3f}s"
                    )

                await asyncio.sleep(self.update_interval)

            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Error in cycles manager loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def load_active_cycles(self):
        """Load all active cycles from Supabase"""
        try:
            # Get all active cycles for this account
            result = await self.supabase_client.table('cycles').select(
                '*, orders(*)'
            ).eq('account', self.account_id).eq('is_closed', False).execute()

            # Clear previous data
            current_cycle_ids = set()

            for cycle_data in result.data:
                cycle_id = cycle_data['id']
                current_cycle_ids.add(cycle_id)

                # Determine cycle type and create appropriate object
                cycle_type = cycle_data.get('cycle_type', 'BUY')

                # Check if this is a hedge cycle (AdaptiveHedging)
                if ('hedge_levels' in cycle_data and cycle_data['hedge_levels']) or cycle_type == 'HEDGE':
                    # AdaptiveHedging cycle
                    if cycle_id not in self.ah_cycles:
                        ah_cycle = AHCycleV2(
                            self.supabase_client,
                            self.meta_trader,
                            self.create_mock_bot(cycle_data),
                            cycle_data
                        )
                        self.ah_cycles[cycle_id] = ah_cycle
                        self.active_cycles[cycle_id] = ah_cycle
                    else:
                        # Update existing cycle with latest data
                        await self.update_cycle_data(self.ah_cycles[cycle_id], cycle_data)
                else:
                    # CycleTrader cycle
                    if cycle_id not in self.ct_cycles:
                        ct_cycle = CTCycleV2(
                            self.supabase_client,
                            self.meta_trader,
                            self.create_mock_bot(cycle_data),
                            cycle_data
                        )
                        self.ct_cycles[cycle_id] = ct_cycle
                        self.active_cycles[cycle_id] = ct_cycle
                    else:
                        # Update existing cycle with latest data
                        await self.update_cycle_data(self.ct_cycles[cycle_id], cycle_data)

            # Remove cycles that are no longer active
            for cycle_id in list(self.active_cycles.keys()):
                if cycle_id not in current_cycle_ids:
                    self.remove_cycle(cycle_id)

        except Exception as e:
            self.logger.error(f"Error loading active cycles: {e}")

    def create_mock_bot(self, cycle_data: Dict) -> object:
        """Create a mock bot object from cycle data for compatibility"""
        class MockBot:
            def __init__(self, cycle_data):
                self.id = cycle_data.get('bot', '')
                self.account_id = cycle_data.get('account', '')
                self.magic = 123456  # Default magic number
                self.strategy_id = 'unknown'  # Will be set by strategy

        return MockBot(cycle_data)

    async def update_cycle_data(self, cycle_obj, latest_data: Dict):
        """Update cycle object with latest data from database"""
        try:
            # Update key properties
            cycle_obj.total_profit = latest_data.get('total_profit', 0)
            cycle_obj.total_volume = latest_data.get('total_volume', 0)
            cycle_obj.status = latest_data.get('status', 'initial')
            cycle_obj.updated_at = latest_data.get(
                'updated_at', datetime.utcnow().isoformat())

            # Update order arrays
            cycle_obj.initial_orders = latest_data.get('initial_orders', [])
            cycle_obj.hedge_orders = latest_data.get('hedge_orders', [])
            cycle_obj.recovery_orders = latest_data.get('recovery_orders', [])
            cycle_obj.pending_orders = latest_data.get('pending_orders', [])
            cycle_obj.closed_orders = latest_data.get('closed_orders', [])

            # Update strategy-specific properties
            if hasattr(cycle_obj, 'hedge_levels'):
                cycle_obj.hedge_levels = latest_data.get('hedge_levels', [])
                cycle_obj.current_hedge_level = latest_data.get(
                    'current_hedge_level', 0)

            if hasattr(cycle_obj, 'threshold_orders'):
                cycle_obj.threshold_orders = latest_data.get(
                    'threshold_orders', [])
                cycle_obj.done_price_levels = latest_data.get(
                    'done_price_levels', [])

        except Exception as e:
            self.logger.error(f"Error updating cycle data: {e}")

    def remove_cycle(self, cycle_id: str):
        """Remove cycle from tracking"""
        try:
            # Move to closed buffer for validation
            if cycle_id in self.active_cycles:
                self.closed_cycles_buffer[cycle_id] = self.active_cycles[cycle_id]
                del self.active_cycles[cycle_id]

            # Remove from specific type tracking
            if cycle_id in self.ct_cycles:
                del self.ct_cycles[cycle_id]
            if cycle_id in self.ah_cycles:
                del self.ah_cycles[cycle_id]

            # Clean buffer periodically (keep only last hour)
            current_time = datetime.utcnow()
            for buffered_id, cycle_obj in list(self.closed_cycles_buffer.items()):
                if hasattr(cycle_obj, 'updated_at'):
                    cycle_time = datetime.fromisoformat(
                        cycle_obj.updated_at.replace('Z', '+00:00'))
                    if (current_time - cycle_time).total_seconds() > 3600:  # 1 hour
                        del self.closed_cycles_buffer[buffered_id]

        except Exception as e:
            self.logger.error(f"Error removing cycle {cycle_id}: {e}")

    async def sync_cycle_profits(self):
        """Sync cycle profits with current order status"""
        try:
            update_tasks = []

            for cycle_id, cycle_obj in self.active_cycles.items():
                # Get orders for this cycle from orders manager
                cycle_orders = await self.orders_manager.get_orders_by_cycle(cycle_id)

                if cycle_orders:
                    # Calculate current profit
                    current_profit = sum(order.get('profit', 0)
                                         for order in cycle_orders)
                    current_volume = sum(order.get('volume', 0)
                                         for order in cycle_orders)

                    # Check if profit has changed significantly
                    if (abs(current_profit - cycle_obj.total_profit) >= 0.01 or
                            abs(current_volume - cycle_obj.total_volume) >= 0.01):

                        update_tasks.append(self.update_cycle_profit(
                            cycle_id, current_profit, current_volume
                        ))

            # Execute all updates concurrently
            if update_tasks:
                await asyncio.gather(*update_tasks, return_exceptions=True)

        except Exception as e:
            self.logger.error(f"Error syncing cycle profits: {e}")

    async def update_cycle_profit(self, cycle_id: str, profit: float, volume: float):
        """Update single cycle profit in database"""
        try:
            update_data = {
                'total_profit': round(profit, 2),
                'total_volume': round(volume, 2),
                'updated_at': datetime.utcnow().isoformat()
            }

            # Update in Supabase
            result = await self.supabase_client.table('cycles').update(update_data).eq('id', cycle_id).execute()

            if result.data and cycle_id in self.active_cycles:
                # Update local cache
                cycle_obj = self.active_cycles[cycle_id]
                cycle_obj.total_profit = profit
                cycle_obj.total_volume = volume
                cycle_obj.updated_at = update_data['updated_at']

                # Send real-time update via WebSocket
                if self.websocket_service:
                    try:
                        await self.websocket_service.send_cycle_update(self.account_id, {
                            'cycle_id': cycle_id,
                            'total_profit': profit,
                            'total_volume': volume,
                            'status': getattr(cycle_obj, 'status', 'active'),
                            'updated_at': update_data['updated_at']
                        })
                    except Exception as e:
                        self.logger.error(
                            f"Error sending WebSocket cycle update: {e}")

        except Exception as e:
            self.logger.error(f"Error updating cycle {cycle_id} profit: {e}")

    async def validate_cycle_integrity(self):
        """Validate cycle integrity and fix issues"""
        try:
            validation_tasks = []

            for cycle_id, cycle_obj in self.active_cycles.items():
                validation_tasks.append(
                    self.validate_single_cycle(cycle_id, cycle_obj))

            if validation_tasks:
                results = await asyncio.gather(*validation_tasks, return_exceptions=True)
                issues_found = sum(
                    1 for result in results if isinstance(result, Exception))

                if issues_found > 0:
                    self.logger.warning(
                        f"Found {issues_found} cycle integrity issues")

        except Exception as e:
            self.logger.error(f"Error validating cycle integrity: {e}")

    async def validate_single_cycle(self, cycle_id: str, cycle_obj):
        """Validate single cycle integrity"""
        try:
            # Get all orders that should belong to this cycle
            all_order_ids = await cycle_obj.get_all_orders(include_closed=True)

            # Check if all orders exist in database
            if all_order_ids:
                result = await self.supabase_client.table('orders').select('id, status').in_('id', all_order_ids).execute()

                existing_order_ids = {order['id'] for order in result.data}
                missing_order_ids = set(all_order_ids) - existing_order_ids

                if missing_order_ids:
                    self.logger.warning(
                        f"Cycle {cycle_id} references missing orders: {missing_order_ids}")
                    await self.fix_missing_orders(cycle_id, missing_order_ids)

                # Check for orphaned orders (orders that reference this cycle but aren't in cycle's order lists)
                orphaned_result = await self.supabase_client.table('orders').select('id').eq('cycle', cycle_id).execute()

                all_db_order_ids = {order['id']
                                    for order in orphaned_result.data}
                cycle_order_ids = set(all_order_ids)
                orphaned_order_ids = all_db_order_ids - cycle_order_ids

                if orphaned_order_ids:
                    self.logger.warning(
                        f"Found orphaned orders for cycle {cycle_id}: {orphaned_order_ids}")
                    await self.fix_orphaned_orders(cycle_id, orphaned_order_ids)

        except Exception as e:
            self.logger.error(f"Error validating cycle {cycle_id}: {e}")
            raise e

    async def fix_missing_orders(self, cycle_id: str, missing_order_ids: List[str]):
        """Fix cycle references to missing orders"""
        try:
            cycle_obj = self.active_cycles.get(cycle_id)
            if not cycle_obj:
                return

            # Remove missing order IDs from all order lists
            for order_list_name in ['initial_orders', 'hedge_orders', 'recovery_orders',
                                    'pending_orders', 'threshold_orders', 'closed_orders']:
                if hasattr(cycle_obj, order_list_name):
                    order_list = getattr(cycle_obj, order_list_name)
                    if isinstance(order_list, list):
                        original_length = len(order_list)
                        setattr(cycle_obj, order_list_name, [
                                oid for oid in order_list if oid not in missing_order_ids])
                        if len(getattr(cycle_obj, order_list_name)) != original_length:
                            self.logger.info(
                                f"Removed {original_length - len(getattr(cycle_obj, order_list_name))} missing orders from {order_list_name}")

            # Update cycle in database
            await cycle_obj.update_cycle()

        except Exception as e:
            self.logger.error(
                f"Error fixing missing orders for cycle {cycle_id}: {e}")

    async def fix_orphaned_orders(self, cycle_id: str, orphaned_order_ids: List[str]):
        """Fix orphaned orders by adding them to appropriate cycle lists"""
        try:
            cycle_obj = self.active_cycles.get(cycle_id)
            if not cycle_obj:
                return

            # Get order details to determine appropriate list
            result = await self.supabase_client.table('orders').select('*').in_('id', orphaned_order_ids).execute()

            for order in result.data:
                order_type = order.get('order_data', {}).get(
                    'order_type', 'initial')
                order_status = order.get('status', 'EXECUTED')

                # Add to appropriate list based on order type and status
                if order_status == 'CLOSED':
                    if order['id'] not in cycle_obj.closed_orders:
                        cycle_obj.closed_orders.append(order['id'])
                        self.logger.info(
                            f"Added orphaned closed order {order['id']} to cycle {cycle_id}")
                else:
                    # Add to appropriate active list
                    if order_type == 'hedge' and order['id'] not in cycle_obj.hedge_orders:
                        cycle_obj.hedge_orders.append(order['id'])
                        self.logger.info(
                            f"Added orphaned hedge order {order['id']} to cycle {cycle_id}")
                    elif order_type == 'recovery' and order['id'] not in cycle_obj.recovery_orders:
                        cycle_obj.recovery_orders.append(order['id'])
                        self.logger.info(
                            f"Added orphaned recovery order {order['id']} to cycle {cycle_id}")
                    elif order_type == 'pending' and order['id'] not in cycle_obj.pending_orders:
                        cycle_obj.pending_orders.append(order['id'])
                        self.logger.info(
                            f"Added orphaned pending order {order['id']} to cycle {cycle_id}")
                    elif order_type == 'threshold' and hasattr(cycle_obj, 'threshold_orders') and order['id'] not in cycle_obj.threshold_orders:
                        cycle_obj.threshold_orders.append(order['id'])
                        self.logger.info(
                            f"Added orphaned threshold order {order['id']} to cycle {cycle_id}")
                    elif order['id'] not in cycle_obj.initial_orders:
                        cycle_obj.initial_orders.append(order['id'])
                        self.logger.info(
                            f"Added orphaned order {order['id']} to initial orders for cycle {cycle_id}")

            # Update cycle in database
            await cycle_obj.update_cycle()

        except Exception as e:
            self.logger.error(
                f"Error fixing orphaned orders for cycle {cycle_id}: {e}")

    async def fix_incorrectly_closed_cycles(self):
        """Check for cycles marked as closed but still have open orders in MT5"""
        try:
            # Get recently closed cycles (last 24 hours)
            time_24h_ago = (datetime.utcnow() -
                            timedelta(hours=24)).isoformat()

            result = await self.supabase_client.table('cycles').select(
                '*, orders(*)'
            ).eq('account', self.account_id).eq('is_closed', True).gte('updated_at', time_24h_ago).execute()

            fix_tasks = []
            for cycle_data in result.data:
                fix_tasks.append(self.check_and_fix_closed_cycle(cycle_data))

            if fix_tasks:
                results = await asyncio.gather(*fix_tasks, return_exceptions=True)
                fixed_count = sum(1 for result in results if result is True)

                if fixed_count > 0:
                    self.fixed_cycles_count += fixed_count
                    self.logger.info(
                        f"Fixed {fixed_count} incorrectly closed cycles")

        except Exception as e:
            self.logger.error(f"Error fixing incorrectly closed cycles: {e}")

    async def check_and_fix_closed_cycle(self, cycle_data: Dict) -> bool:
        """Check if a closed cycle still has open orders and reopen if needed"""
        try:
            cycle_id = cycle_data['id']

            # Get all order tickets from this cycle
            all_order_tickets = []
            for order in cycle_data.get('orders', []):
                order_data = order.get('order_data', {})
                ticket = order_data.get('ticket')
                if ticket:
                    all_order_tickets.append(ticket)

            # Check if any orders are still open in MT5
            still_open_tickets = []
            for ticket in all_order_tickets:
                # Check current MT5 orders
                if ticket in self.orders_manager.mt5_orders:
                    still_open_tickets.append(ticket)

            # If we found open orders, reopen the cycle
            if still_open_tickets:
                self.logger.info(
                    f"Reopening cycle {cycle_id} - found {len(still_open_tickets)} open orders in MT5")

                # Update cycle status
                update_data = {
                    'is_closed': False,
                    'status': 'reopened',
                    'updated_at': datetime.utcnow().isoformat()
                }

                await self.supabase_client.table('cycles').update(update_data).eq('id', cycle_id).execute()

                # Send event
                await self.send_cycle_event('CYCLE_REOPENED', {
                    'cycle_id': cycle_id,
                    'reason': 'found_open_orders_in_mt5',
                    'open_tickets': still_open_tickets
                }, 'WARNING')

                return True

            return False

        except Exception as e:
            self.logger.error(
                f"Error checking closed cycle {cycle_data.get('id')}: {e}")
            return False

    async def send_cycle_event(self, event_type: str, content: Dict, severity: str = 'INFO'):
        """Send cycle-related event to Supabase"""
        try:
            event_data = {
                'uuid': f"{datetime.utcnow().timestamp()}_{self.account_id}_cycles",
                'account': self.account_id,
                'content': content,
                'event_type': event_type,
                'severity': severity,
                'created_at': datetime.utcnow().isoformat()
            }

            await self.supabase_client.table('events').insert(event_data).execute()

        except Exception as e:
            self.logger.error(f"Error sending cycle event: {e}")

    async def close_cycle_by_id(self, cycle_id: str, user_id: str = "system", username: str = "system") -> bool:
        """Close specific cycle by ID"""
        try:
            if cycle_id in self.active_cycles:
                cycle_obj = self.active_cycles[cycle_id]
                success = await cycle_obj.close_cycle(
                    sent_by_admin=True,
                    user_id=user_id,
                    username=username
                )

                if success:
                    self.cycles_closed += 1
                    self.remove_cycle(cycle_id)

                return success
            else:
                self.logger.warning(
                    f"Cycle {cycle_id} not found in active cycles")
                return False

        except Exception as e:
            self.logger.error(f"Error closing cycle {cycle_id}: {e}")
            return False

    async def close_all_cycles(self, user_id: str = "system", username: str = "system") -> int:
        """Close all active cycles"""
        try:
            close_tasks = []
            cycle_ids = list(self.active_cycles.keys())

            for cycle_id in cycle_ids:
                close_tasks.append(self.close_cycle_by_id(
                    cycle_id, user_id, username))

            if close_tasks:
                results = await asyncio.gather(*close_tasks, return_exceptions=True)
                closed_count = sum(1 for result in results if result is True)

                self.logger.info(
                    f"Closed {closed_count} out of {len(cycle_ids)} cycles")
                return closed_count

            return 0

        except Exception as e:
            self.logger.error(f"Error closing all cycles: {e}")
            return 0

    async def get_cycle_statistics(self) -> Dict:
        """Get cycles manager statistics"""
        ct_profits = sum(
            cycle.total_profit for cycle in self.ct_cycles.values())
        ah_profits = sum(
            cycle.total_profit for cycle in self.ah_cycles.values())

        return {
            'total_active_cycles': len(self.active_cycles),
            'ct_cycles_count': len(self.ct_cycles),
            'ah_cycles_count': len(self.ah_cycles),
            'ct_total_profit': round(ct_profits, 2),
            'ah_total_profit': round(ah_profits, 2),
            'total_profit': round(ct_profits + ah_profits, 2),
            'cycles_created': self.cycles_created,
            'cycles_closed': self.cycles_closed,
            'total_syncs': self.sync_count,
            'total_errors': self.error_count,
            'fixed_cycles': self.fixed_cycles_count,
            'last_sync': self.last_sync_time.isoformat()
        }

    async def get_cycles_by_symbol(self, symbol: str) -> List[object]:
        """Get all cycles for a specific symbol"""
        symbol_cycles = []
        for cycle_obj in self.active_cycles.values():
            if cycle_obj.symbol == symbol:
                symbol_cycles.append(cycle_obj)
        return symbol_cycles

    async def get_cycles_by_strategy(self, strategy_type: str) -> List[object]:
        """Get cycles by strategy type (CT or AH)"""
        if strategy_type.upper() == 'CT':
            return list(self.ct_cycles.values())
        elif strategy_type.upper() == 'AH':
            return list(self.ah_cycles.values())
        else:
            return []

    def __str__(self):
        return f"CyclesManagerV2(account={self.account_id}, active={len(self.active_cycles)}, ct={len(self.ct_cycles)}, ah={len(self.ah_cycles)})"

    def __repr__(self):
        return self.__str__()
