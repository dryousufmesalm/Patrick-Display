"""
CycleTrader Strategy - Real-Time Supabase Integration
Optimized for sub-second performance with direct database operations
"""

from cycles.CT_cycle_v2 import CTCycleV2
from Strategy.base_strategy import BaseStrategy
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


logger = logging.getLogger(__name__)


class CycleTraderV2(BaseStrategy):
    """
    CycleTrader strategy with real-time Supabase integration
    Optimized for high-frequency trading with sub-second updates
    """

    def __init__(self, meta_trader, config: Dict, supabase_client, symbol: str, bot):
        super().__init__(meta_trader, config, supabase_client, symbol, bot)

        # CycleTrader specific properties
        self.enable_recovery = False
        self.lot_sizes = [0.01, 0.02, 0.03, 0.04,
                          0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
        self.margin = 10.8
        self.pips_step = 0
        self.slippage = 3
        self.sltp = "money"
        self.take_profit = 5
        self.zones = [500]
        self.zone_forward = 1
        self.zone_forward2 = 1
        self.autotrade = False
        self.autotrade_threshold = 0
        self.max_cycles = 1
        self.hedges_numbers = None
        self.ADD_All_to_PNL = True
        self.autotrade_pips_restriction = 100

        # Auto candle close settings
        self.auto_candle_close = False
        self.candle_timeframe = "H1"
        self.hedge_sl = 100
        self.prevent_opposing_trades = True
        self.last_candle_time = None

        # Performance optimization
        self.last_cycle_price = 0
        self.update_interval = 0.1  # 100ms update interval for sub-second performance

    async def init_strategy_settings(self):
        """Initialize CycleTrader specific settings"""
        try:
            # Set all configuration values with defaults
            self.enable_recovery = self.config.get("enable_recovery", False)
            self.lot_sizes = self.string_to_array(
                self.config.get("lot_sizes", "0.01"))
            self.pips_step = self.config.get("pips_step", 0)
            self.slippage = self.config.get("slippage", 3)
            self.sltp = self.config.get("sltp", "money")
            self.take_profit = self.config.get("take_profit", 5)
            self.zones = self.string_to_array(
                self.config.get('zone_array', "500"))
            self.zone_forward = self.config.get("zone_forward", 1)
            self.zone_forward2 = self.config.get("zone_forward2", 1)
            self.max_cycles = self.config.get("max_cycles", 1)
            self.autotrade = self.config.get("autotrade", False)
            self.autotrade_threshold = self.config.get(
                "autotrade_threshold", 0)
            self.hedges_numbers = self.config.get("hedges_numbers", 0)
            self.ADD_All_to_PNL = self.config.get(
                "buy_and_sell_add_to_pnl", True)
            self.autotrade_pips_restriction = self.config.get(
                "autotrade_pips_restriction", 100)

            # Auto candle close settings
            self.auto_candle_close = self.config.get(
                "auto_candle_close", False)
            self.candle_timeframe = self.config.get("candle_timeframe", "H1")
            self.hedge_sl = self.config.get("hedge_sl", 100)
            self.prevent_opposing_trades = self.config.get(
                "prevent_opposing_trades", True)

            # Get initial price
            self.last_cycle_price = self.meta_trader.get_ask(self.symbol)

            # Log initialization
            self.logger.info(f"CycleTrader initialized for {self.symbol}:")
            self.logger.info(f"- auto_candle_close: {self.auto_candle_close}")
            self.logger.info(f"- max_cycles: {self.max_cycles}")
            self.logger.info(f"- autotrade: {self.autotrade}")

        except Exception as e:
            self.logger.error(f"Error initializing CycleTrader settings: {e}")
            # Set safe defaults
            self.zone_forward2 = 1 if not hasattr(
                self, 'zone_forward2') else self.zone_forward2

    def string_to_array(self, string: str) -> List[float]:
        """Convert string to array of floats"""
        try:
            if isinstance(string, list):
                return string

            # Handle comma-separated values
            if ',' in string:
                return [float(x.strip()) for x in string.split(',')]

            # Handle single value
            return [float(string)]
        except (ValueError, TypeError):
            self.logger.warning(
                f"Invalid array string: {string}, using default")
            return [0.01]

    async def handle_event(self, event: Dict):
        """Handle incoming events with real-time processing"""
        try:
            content = event.get('content', {})
            message = content.get("message", "")

            if message == "open_order":
                await self.handle_open_order_event(content)
            elif message == "close_cycle":
                await self.handle_close_cycle_event(content)
            elif message == "update_order_configs":
                await self.handle_update_order_event(content)
            elif message == "close_order":
                await self.handle_close_order_event(content)
            elif message == "close_all_cycles":
                await self.handle_close_all_cycles_event(content)
            elif message == "stop_bot":
                await self.handle_stop_bot_event()
            elif message == "start_bot":
                await self.handle_start_bot_event()
            else:
                self.logger.warning(f"Unknown event message: {message}")

        except Exception as e:
            self.logger.error(f"Error handling event: {e}")

    async def handle_open_order_event(self, content: Dict):
        """Handle order opening with real-time updates"""
        if self.stop_requested:
            return

        try:
            username = content.get("user_name", "system")
            sent_by_admin = content.get("sent_by_admin", False)
            user_id = content.get("user_id", "")
            cycle_type = content.get('type', 0)
            price = content.get('price', 0)

            # Check cycle limits
            if len(self.active_cycles) >= self.max_cycles:
                self.logger.warning(
                    f"Maximum cycles ({self.max_cycles}) reached for {self.symbol}")
                return

            # Execute order based on type
            if cycle_type == 0:  # BUY
                await self.create_buy_cycle(price, sent_by_admin, user_id, username)
            elif cycle_type == 1:  # SELL
                await self.create_sell_cycle(price, sent_by_admin, user_id, username)
            elif cycle_type == 2:  # BUY & SELL
                await self.create_buy_sell_cycle(price, sent_by_admin, user_id, username)

        except Exception as e:
            self.logger.error(f"Error handling open order event: {e}")

    async def create_buy_cycle(self, price: float, sent_by_admin: bool, user_id: str, username: str):
        """Create a BUY cycle with real-time updates using CTCycleV2"""
        try:
            if price == 0:
                # Market order
                current_price = self.meta_trader.get_ask(self.symbol)

                # Create new CT cycle
                cycle_data = {
                    'symbol': self.symbol,
                    'cycle_type': 'BUY',
                    'entry_price': current_price,
                    'initial_threshold_price': current_price,
                    'opened_by': {
                        'sent_by_admin': sent_by_admin,
                        'user_id': user_id,
                        'username': username
                    }
                }

                ct_cycle = CTCycleV2(self.supabase_client,
                                     self.meta_trader, self.bot, cycle_data)
                cycle_id = await ct_cycle.create_cycle()

                if cycle_id:
                    # Execute market order
                    order_data = {
                        'type': 'BUY',
                        'price': current_price,
                        'volume': self.lot_sizes[0],
                        'magic': self.bot.magic,
                        'sl': 0,
                        'tp': 0,
                        'slippage': self.slippage,
                        'status': 'EXECUTED',
                        'order_type': 'market'
                    }

                    mt_order = self.meta_trader.buy(
                        self.symbol, self.lot_sizes[0], self.bot.magic,
                        0, 0, "PIPS", self.slippage, "initial"
                    )

                    if mt_order:
                        order_data['ticket'] = mt_order.get('ticket')
                        order_data['price'] = mt_order.get(
                            'price', current_price)

                        # Create order in database and add to cycle
                        order_id = await self.create_order(cycle_id, order_data)
                        if order_id:
                            await ct_cycle.add_order(order_id, "initial")

                            # Store cycle reference
                            self.active_cycles[cycle_id] = ct_cycle

                            await self.send_event('BUY_CYCLE_CREATED', {
                                'cycle_id': cycle_id,
                                'symbol': self.symbol,
                                'price': order_data['price'],
                                'volume': order_data['volume'],
                                'username': username
                            })
            else:
                # Pending order
                ask = self.meta_trader.get_ask(self.symbol)

                if price > ask:
                    # Buy stop
                    order_data = {
                        'type': 'BUY_STOP',
                        'price': price,
                        'volume': self.lot_sizes[0],
                        'magic': self.bot.magic,
                        'sl': 0,
                        'tp': 0,
                        'slippage': self.slippage,
                        'status': 'PENDING',
                        'order_type': 'pending'
                    }

                    mt_order = self.meta_trader.buy_stop(
                        self.symbol, price, self.lot_sizes[0], self.bot.magic,
                        0, 0, "PIPS", self.slippage, "pending"
                    )
                else:
                    # Buy limit
                    order_data = {
                        'type': 'BUY_LIMIT',
                        'price': price,
                        'volume': self.lot_sizes[0],
                        'magic': self.bot.magic,
                        'sl': 0,
                        'tp': 0,
                        'slippage': self.slippage,
                        'status': 'PENDING',
                        'order_type': 'pending'
                    }

                    mt_order = self.meta_trader.buy_limit(
                        self.symbol, price, self.lot_sizes[0], self.bot.magic,
                        0, 0, "PIPS", self.slippage, "pending"
                    )

                if mt_order:
                    order_data['ticket'] = mt_order.get('ticket')
                    cycle_id = await self.create_cycle(order_data, None, "BUY", True)

                    if cycle_id:
                        await self.send_event('PENDING_BUY_CYCLE_CREATED', {
                            'cycle_id': cycle_id,
                            'symbol': self.symbol,
                            'price': price,
                            'volume': order_data['volume'],
                            'username': username
                        })

        except Exception as e:
            self.logger.error(f"Error creating buy cycle: {e}")

    async def create_sell_cycle(self, price: float, sent_by_admin: bool, user_id: str, username: str):
        """Create a SELL cycle with real-time updates"""
        try:
            if price == 0:
                # Market order
                order_data = {
                    'type': 'SELL',
                    'price': self.meta_trader.get_bid(self.symbol),
                    'volume': self.lot_sizes[0],
                    'magic': self.bot.magic,
                    'sl': 0,
                    'tp': 0,
                    'slippage': self.slippage,
                    'status': 'EXECUTED',
                    'order_type': 'market'
                }

                # Execute market order
                mt_order = self.meta_trader.sell(
                    self.symbol, self.lot_sizes[0], self.bot.magic,
                    0, 0, "PIPS", self.slippage, "initial"
                )

                if mt_order:
                    order_data['ticket'] = mt_order.get('ticket')
                    order_data['price'] = mt_order.get(
                        'price', order_data['price'])

                    # Create cycle
                    cycle_id = await self.create_cycle(order_data, None, "SELL", False)

                    if cycle_id:
                        await self.send_event('SELL_CYCLE_CREATED', {
                            'cycle_id': cycle_id,
                            'symbol': self.symbol,
                            'price': order_data['price'],
                            'volume': order_data['volume'],
                            'username': username
                        })
            else:
                # Pending order logic (similar to buy but for sell)
                bid = self.meta_trader.get_bid(self.symbol)

                if price < bid:
                    # Sell stop
                    order_data = {
                        'type': 'SELL_STOP',
                        'price': price,
                        'volume': self.lot_sizes[0],
                        'magic': self.bot.magic,
                        'sl': 0,
                        'tp': 0,
                        'slippage': self.slippage,
                        'status': 'PENDING',
                        'order_type': 'pending'
                    }

                    mt_order = self.meta_trader.sell_stop(
                        self.symbol, price, self.lot_sizes[0], self.bot.magic,
                        0, 0, "PIPS", self.slippage, "pending"
                    )
                else:
                    # Sell limit
                    order_data = {
                        'type': 'SELL_LIMIT',
                        'price': price,
                        'volume': self.lot_sizes[0],
                        'magic': self.bot.magic,
                        'sl': 0,
                        'tp': 0,
                        'slippage': self.slippage,
                        'status': 'PENDING',
                        'order_type': 'pending'
                    }

                    mt_order = self.meta_trader.sell_limit(
                        self.symbol, price, self.lot_sizes[0], self.bot.magic,
                        0, 0, "PIPS", self.slippage, "pending"
                    )

                if mt_order:
                    order_data['ticket'] = mt_order.get('ticket')
                    cycle_id = await self.create_cycle(order_data, None, "SELL", True)

                    if cycle_id:
                        await self.send_event('PENDING_SELL_CYCLE_CREATED', {
                            'cycle_id': cycle_id,
                            'symbol': self.symbol,
                            'price': price,
                            'volume': order_data['volume'],
                            'username': username
                        })

        except Exception as e:
            self.logger.error(f"Error creating sell cycle: {e}")

    async def create_buy_sell_cycle(self, price: float, sent_by_admin: bool, user_id: str, username: str):
        """Create a BUY & SELL cycle with real-time updates"""
        try:
            if price == 0:
                # Market orders for both buy and sell
                buy_order_data = {
                    'type': 'BUY',
                    'price': self.meta_trader.get_ask(self.symbol),
                    'volume': self.lot_sizes[0],
                    'magic': self.bot.magic,
                    'sl': 0,
                    'tp': 0,
                    'slippage': self.slippage,
                    'status': 'EXECUTED',
                    'order_type': 'market'
                }

                sell_order_data = {
                    'type': 'SELL',
                    'price': self.meta_trader.get_bid(self.symbol),
                    'volume': self.lot_sizes[0],
                    'magic': self.bot.magic,
                    'sl': 0,
                    'tp': 0,
                    'slippage': self.slippage,
                    'status': 'EXECUTED',
                    'order_type': 'market'
                }

                # Execute both orders
                buy_mt_order = self.meta_trader.buy(
                    self.symbol, self.lot_sizes[0], self.bot.magic,
                    0, 0, "PIPS", self.slippage, "initial"
                )

                sell_mt_order = self.meta_trader.sell(
                    self.symbol, self.lot_sizes[0], self.bot.magic,
                    0, 0, "PIPS", self.slippage, "initial"
                )

                if buy_mt_order and sell_mt_order:
                    buy_order_data['ticket'] = buy_mt_order.get('ticket')
                    sell_order_data['ticket'] = sell_mt_order.get('ticket')

                    # Create cycle with both orders
                    cycle_id = await self.create_cycle(buy_order_data, sell_order_data, "BUY&SELL", False)

                    if cycle_id:
                        await self.send_event('BUY_SELL_CYCLE_CREATED', {
                            'cycle_id': cycle_id,
                            'symbol': self.symbol,
                            'buy_price': buy_order_data['price'],
                            'sell_price': sell_order_data['price'],
                            'volume': self.lot_sizes[0],
                            'username': username
                        })
            else:
                # Pending order logic for buy&sell
                # Implementation would be similar but more complex
                self.logger.info(
                    f"Pending buy&sell cycle creation not implemented yet for price {price}")

        except Exception as e:
            self.logger.error(f"Error creating buy&sell cycle: {e}")

    async def handle_close_cycle_event(self, content: Dict):
        """Handle cycle closing with real-time updates"""
        try:
            cycle_id = content.get('id')
            if cycle_id in self.active_cycles:
                # Calculate final profit
                cycle_data = self.active_cycles[cycle_id]
                profit = await self.calculate_cycle_profit(cycle_id)

                # Close cycle
                await self.close_cycle(cycle_id, profit)

        except Exception as e:
            self.logger.error(f"Error closing cycle: {e}")

    async def calculate_cycle_profit(self, cycle_id: str) -> float:
        """Calculate total profit for a cycle"""
        try:
            total_profit = 0.0

            # Get all orders for this cycle
            orders_result = await self.supabase_client.table('orders').select('*').eq('cycle', cycle_id).execute()

            for order in orders_result.data:
                total_profit += order.get('profit', 0)

            return total_profit

        except Exception as e:
            self.logger.error(f"Error calculating cycle profit: {e}")
            return 0.0

    async def run(self):
        """Main strategy loop with sub-second updates"""
        self.logger.info(f"Starting CycleTrader main loop for {self.symbol}")

        # Initialize performance tracking
        self.update_count = 0
        self.last_update = datetime.utcnow()

        while self.is_running and not self.stop_requested:
            try:
                # Get all active cycles (like the old implementation)
                await self.load_active_state()

                # Check autotrade restrictions (from old implementation)
                new_cycles_restriction = await self.check_autotrade_restrictions()

                # Process each active cycle (from old implementation)
                tasks = []
                for cycle_id, cycle_data in self.active_cycles.items():
                    if not self.stop and not self.stop_requested:
                        # Manage cycle orders (equivalent to old manage_cycle_orders)
                        tasks.append(self.manage_cycle_orders(cycle_id))

                        # Update cycle profit
                        tasks.append(self.update_cycle_profit(cycle_id))

                        # Check take profit conditions
                        tasks.append(self.check_cycle_take_profit(cycle_id))

                # Check for new trading opportunities (opening new cycles)
                if not self.stop and not self.stop_requested:
                    tasks.append(self.open_new_cycle_if_needed(
                        new_cycles_restriction))

                # Auto candle close check
                if self.auto_candle_close and not self.stop and not self.stop_requested:
                    tasks.append(self.check_candle_close())

                # Execute all tasks concurrently
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Performance tracking
                self.update_count += 1
                current_time = datetime.utcnow()

                if (current_time - self.last_update).seconds >= 30:
                    # Log performance every 30 seconds
                    updates_per_second = self.update_count / 30
                    self.logger.info(
                        f"CycleTrader performance: {updates_per_second:.2f} updates/sec")
                    self.update_count = 0
                    self.last_update = current_time

                # Sub-second update interval
                await asyncio.sleep(self.update_interval)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

                # Handle connection failures
                if "connection" in str(e).lower():
                    if not await self.handle_connection_failure("main_loop"):
                        break

                await asyncio.sleep(1)  # Wait before retrying

        self.logger.info(f"CycleTrader main loop stopped for {self.symbol}")

    async def check_trading_opportunities(self):
        """Check for new trading opportunities based on zones and thresholds"""
        try:
            if not self.autotrade or len(self.active_cycles) >= self.max_cycles:
                return

            current_price = self.meta_trader.get_ask(self.symbol)
            price_diff = abs(current_price - self.last_cycle_price)

            # Check if price moved enough to trigger new cycle
            for zone in self.zones:
                if price_diff >= zone * self.meta_trader.get_point(self.symbol):
                    # Check autotrade restrictions
                    if price_diff <= self.autotrade_pips_restriction * self.meta_trader.get_point(self.symbol):
                        # Trigger new cycle based on direction
                        if current_price > self.last_cycle_price:
                            await self.create_auto_sell_cycle(current_price)
                        else:
                            await self.create_auto_buy_cycle(current_price)

                        self.last_cycle_price = current_price
                        break

        except Exception as e:
            self.logger.error(f"Error checking trading opportunities: {e}")

    async def create_auto_buy_cycle(self, price: float):
        """Create automatic buy cycle"""
        try:
            order_data = {
                'type': 'BUY',
                'price': price,
                'volume': self.lot_sizes[0],
                'magic': self.bot.magic,
                'sl': 0,
                'tp': 0,
                'slippage': self.slippage,
                'status': 'EXECUTED',
                'order_type': 'auto'
            }

            mt_order = self.meta_trader.buy(
                self.symbol, self.lot_sizes[0], self.bot.magic,
                0, 0, "PIPS", self.slippage, "auto"
            )

            if mt_order:
                order_data['ticket'] = mt_order.get('ticket')
                cycle_id = await self.create_cycle(order_data, None, "BUY", False)

                if cycle_id:
                    await self.send_event('AUTO_BUY_CYCLE_CREATED', {
                        'cycle_id': cycle_id,
                        'symbol': self.symbol,
                        'price': price,
                        'volume': order_data['volume']
                    })

        except Exception as e:
            self.logger.error(f"Error creating auto buy cycle: {e}")

    async def create_auto_sell_cycle(self, price: float):
        """Create automatic sell cycle"""
        try:
            order_data = {
                'type': 'SELL',
                'price': price,
                'volume': self.lot_sizes[0],
                'magic': self.bot.magic,
                'sl': 0,
                'tp': 0,
                'slippage': self.slippage,
                'status': 'EXECUTED',
                'order_type': 'auto'
            }

            mt_order = self.meta_trader.sell(
                self.symbol, self.lot_sizes[0], self.bot.magic,
                0, 0, "PIPS", self.slippage, "auto"
            )

            if mt_order:
                order_data['ticket'] = mt_order.get('ticket')
                cycle_id = await self.create_cycle(order_data, None, "SELL", False)

                if cycle_id:
                    await self.send_event('AUTO_SELL_CYCLE_CREATED', {
                        'cycle_id': cycle_id,
                        'symbol': self.symbol,
                        'price': price,
                        'volume': order_data['volume']
                    })

        except Exception as e:
            self.logger.error(f"Error creating auto sell cycle: {e}")

    async def update_active_cycles(self):
        """Update active cycles with current profit/loss"""
        try:
            for cycle_id, cycle_data in self.active_cycles.items():
                # Calculate current profit
                current_profit = await self.calculate_cycle_profit(cycle_id)

                # Check take profit conditions
                if current_profit >= self.take_profit:
                    await self.close_cycle(cycle_id, current_profit)
                    continue

                # Update cycle profit if changed significantly
                last_profit = cycle_data.get('total_profit', 0)
                if abs(current_profit - last_profit) >= 0.01:  # Update if change > 1 cent
                    await self.update_cycle(cycle_id, {'total_profit': current_profit})

        except Exception as e:
            self.logger.error(f"Error updating active cycles: {e}")

    async def check_candle_close(self):
        """Check for candle close conditions"""
        try:
            if not self.auto_candle_close:
                return

            # Get current candle time
            current_candle = self.meta_trader.get_current_candle_time(
                self.symbol, self.candle_timeframe)

            if self.last_candle_time and current_candle != self.last_candle_time:
                # New candle detected - close profitable cycles
                await self.close_profitable_cycles()

            self.last_candle_time = current_candle

        except Exception as e:
            self.logger.error(f"Error checking candle close: {e}")

    async def close_profitable_cycles(self):
        """Close all profitable cycles on candle close"""
        try:
            for cycle_id, cycle_data in list(self.active_cycles.items()):
                profit = await self.calculate_cycle_profit(cycle_id)
                if profit > 0:
                    await self.close_cycle(cycle_id, profit)

        except Exception as e:
            self.logger.error(f"Error closing profitable cycles: {e}")

    async def handle_close_all_cycles_event(self, content: Dict):
        """Handle close all cycles event"""
        try:
            for cycle_id in list(self.active_cycles.keys()):
                profit = await self.calculate_cycle_profit(cycle_id)
                await self.close_cycle(cycle_id, profit)

        except Exception as e:
            self.logger.error(f"Error closing all cycles: {e}")

    async def handle_stop_bot_event(self):
        """Handle stop bot event"""
        self.stop_requested = True
        self.logger.info(f"Stop signal received for {self.symbol}")

    async def handle_start_bot_event(self):
        """Handle start bot event"""
        self.stop_requested = False
        self.logger.info(f"Start signal received for {self.symbol}")

    async def handle_update_order_event(self, content: Dict):
        """Handle order update event"""
        try:
            order_ticket = content.get("ticket")
            updates = content.get('updated', {})

            # Find order by ticket
            for order_id, order_data in self.active_orders.items():
                if order_data.get('ticket') == order_ticket:
                    # Update order in MetaTrader
                    success = self.meta_trader.modify_order(
                        order_ticket,
                        updates.get('sl', 0),
                        updates.get('tp', 0)
                    )

                    if success:
                        # Update database
                        order_updates = {
                            'order_data': {**order_data.get('order_data', {}), **updates},
                            'updated_at': datetime.utcnow().isoformat()
                        }

                        await self.supabase_client.table('orders').update(order_updates).eq('id', order_id).execute()

                        # Update local state
                        self.active_orders[order_id].update(order_updates)
                    break

        except Exception as e:
            self.logger.error(f"Error updating order: {e}")

    async def handle_close_order_event(self, content: Dict):
        """Handle close order event"""
        try:
            order_ticket = content.get("ticket")

            # Find and close order
            for order_id, order_data in self.active_orders.items():
                if order_data.get('ticket') == order_ticket:
                    # Close order in MetaTrader
                    success = self.meta_trader.close_order(order_ticket)

                    if success:
                        # Update database
                        order_updates = {
                            'status': 'CLOSED',
                            'updated_at': datetime.utcnow().isoformat()
                        }

                        await self.supabase_client.table('orders').update(order_updates).eq('id', order_id).execute()

                        # Remove from active orders
                        del self.active_orders[order_id]
                    break

        except Exception as e:
            self.logger.error(f"Error closing order: {e}")

    async def check_autotrade_restrictions(self) -> bool:
        """Check autotrade restrictions based on price movement"""
        try:
            new_cycles_restriction = False

            # Only calculate restrictions if autotrade_pips_restriction is not 0
            if self.autotrade_pips_restriction != 0:
                ask = self.meta_trader.get_ask(self.symbol)
                bid = self.meta_trader.get_bid(self.symbol)
                pips = self.meta_trader.get_pips(self.symbol)
                up_price = bid + (self.autotrade_pips_restriction / 2) * pips
                down_price = bid - (self.autotrade_pips_restriction / 2) * pips

                for cycle_id, cycle_data in self.active_cycles.items():
                    # Check if cycle has minimal orders and is at restricted price level
                    orders_count = len(
                        [o for o in self.active_orders.values() if o.get('cycle') == cycle_id])

                    if orders_count <= 2:
                        cycle_price = cycle_data.get('entry_price', 0)
                        if cycle_price > 0:
                            if down_price < cycle_price < up_price:
                                new_cycles_restriction = True
                                break

            return new_cycles_restriction
        except Exception as e:
            self.logger.error(f"Error checking autotrade restrictions: {e}")
            return False

    async def manage_cycle_orders(self, cycle_id: str):
        """Manage orders for a specific cycle (equivalent to old manage_cycle_orders)"""
        try:
            cycle_data = self.active_cycles.get(cycle_id)
            if not cycle_data:
                return

            # Get cycle orders
            cycle_orders = [
                o for o in self.active_orders.values() if o.get('cycle') == cycle_id]

            # Implement zone forward logic from old implementation
            if len(cycle_orders) > 0 and not cycle_data.get('is_closed', False):
                # Check if we need to add more orders based on zone_forward and zone_forward2
                await self.check_zone_forward_orders(cycle_id, cycle_orders)

        except Exception as e:
            self.logger.error(
                f"Error managing cycle orders for {cycle_id}: {e}")

    async def check_zone_forward_orders(self, cycle_id: str, cycle_orders: List[Dict]):
        """Check if new orders need to be added based on zone forward settings"""
        try:
            cycle_data = self.active_cycles.get(cycle_id)
            if not cycle_data:
                return

            # Get current price
            current_price = self.meta_trader.get_ask(self.symbol) if cycle_data.get(
                'cycle_type') == 'BUY' else self.meta_trader.get_bid(self.symbol)
            pip_value = self.meta_trader.get_pips(self.symbol)

            # Implement zone forward logic (simplified from old implementation)
            if len(cycle_orders) < len(self.lot_sizes):
                last_order = max(
                    cycle_orders, key=lambda x: x.get('created_at', ''))
                last_price = last_order.get('price', 0)

                # Calculate zone distance
                zone_distance = self.zones[0] * \
                    pip_value if self.zones else 50 * pip_value

                # Check if price has moved enough to trigger new order
                price_diff = abs(current_price - last_price)
                if price_diff >= zone_distance:
                    await self.add_zone_forward_order(cycle_id, current_price, len(cycle_orders))

        except Exception as e:
            self.logger.error(f"Error checking zone forward orders: {e}")

    async def add_zone_forward_order(self, cycle_id: str, price: float, order_index: int):
        """Add a new order based on zone forward logic"""
        try:
            cycle_data = self.active_cycles.get(cycle_id)
            if not cycle_data or order_index >= len(self.lot_sizes):
                return

            lot_size = self.lot_sizes[order_index]
            cycle_type = cycle_data.get('cycle_type', 'BUY')

            # Create new order
            if cycle_type == 'BUY':
                mt_order = self.meta_trader.buy(
                    self.symbol, lot_size, self.bot.magic,
                    0, 0, "PIPS", self.slippage, f"zone_forward_{order_index}"
                )
            else:
                mt_order = self.meta_trader.sell(
                    self.symbol, lot_size, self.bot.magic,
                    0, 0, "PIPS", self.slippage, f"zone_forward_{order_index}"
                )

            if mt_order:
                order_data = {
                    'type': cycle_type,
                    'price': mt_order.get('price', price),
                    'volume': lot_size,
                    'magic': self.bot.magic,
                    'sl': 0,
                    'tp': 0,
                    'slippage': self.slippage,
                    'status': 'EXECUTED',
                    'order_type': 'zone_forward',
                    'ticket': mt_order.get('ticket')
                }

                await self.create_order(cycle_id, order_data)

        except Exception as e:
            self.logger.error(f"Error adding zone forward order: {e}")

    async def update_cycle_profit(self, cycle_id: str):
        """Update cycle profit (equivalent to old update_cycle)"""
        try:
            current_profit = await self.calculate_cycle_profit(cycle_id)
            cycle_data = self.active_cycles.get(cycle_id)

            if cycle_data:
                last_profit = cycle_data.get('total_profit', 0)
                if abs(current_profit - last_profit) >= 0.01:  # Update if change > 1 cent
                    await self.update_cycle(cycle_id, {'total_profit': current_profit})

        except Exception as e:
            self.logger.error(
                f"Error updating cycle profit for {cycle_id}: {e}")

    async def check_cycle_take_profit(self, cycle_id: str):
        """Check take profit conditions for a cycle"""
        try:
            current_profit = await self.calculate_cycle_profit(cycle_id)

            if current_profit >= self.take_profit:
                await self.close_cycle(cycle_id, current_profit)

        except Exception as e:
            self.logger.error(
                f"Error checking take profit for {cycle_id}: {e}")

    async def open_new_cycle_if_needed(self, cycles_restriction: bool):
        """Open new cycle if conditions are met (equivalent to old open_new_cycle)"""
        try:
            if len(self.active_cycles) >= self.max_cycles:
                return

            if not self.autotrade:
                return

            ask = self.meta_trader.get_ask(self.symbol)
            bid = self.meta_trader.get_bid(self.symbol)
            pips = self.meta_trader.get_pips(self.symbol)

            # Calculate zone prices
            for zone in self.zones:
                up_price = self.last_cycle_price + zone * pips
                down_price = self.last_cycle_price - zone * pips

                # Check if we can open new cycles
                if ask >= up_price and not cycles_restriction:
                    # Check if cycle doesn't already exist at this level
                    if not await self.cycle_exists_at_level(up_price, 'BUY'):
                        self.last_cycle_price = ask
                        await self.create_auto_buy_cycle(ask)

                elif bid <= down_price and not cycles_restriction:
                    # Check if cycle doesn't already exist at this level
                    if not await self.cycle_exists_at_level(down_price, 'SELL'):
                        self.last_cycle_price = bid
                        await self.create_auto_sell_cycle(bid)

        except Exception as e:
            self.logger.error(f"Error opening new cycle: {e}")

    async def cycle_exists_at_level(self, price: float, cycle_type: str) -> bool:
        """Check if a cycle already exists at a specific price level"""
        try:
            # 10 pip tolerance
            tolerance = 10 * self.meta_trader.get_pips(self.symbol)

            for cycle_data in self.active_cycles.values():
                if cycle_data.get('cycle_type') == cycle_type:
                    cycle_price = cycle_data.get('entry_price', 0)
                    if abs(cycle_price - price) <= tolerance:
                        return True

            return False
        except Exception as e:
            self.logger.error(f"Error checking cycle exists at level: {e}")
            return False
