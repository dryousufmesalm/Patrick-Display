"""
AdaptiveHedging Strategy - Real-Time Supabase Integration
Optimized for sub-second performance with direct database operations
"""

from cycles.AH_cycle_v2 import AHCycleV2
from Strategy.base_strategy import BaseStrategy
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


logger = logging.getLogger(__name__)


class AdaptiveHedgingV2(BaseStrategy):
    """
    AdaptiveHedging strategy with real-time Supabase integration
    Optimized for high-frequency hedging with sub-second updates
    """

    def __init__(self, meta_trader, config: Dict, supabase_client, symbol: str, bot):
        super().__init__(meta_trader, config, supabase_client, symbol, bot)

        # AdaptiveHedging specific properties
        self.hedge_distance = 50  # Pips between hedge orders
        self.lot_progression = [0.01, 0.02, 0.04, 0.08, 0.16, 0.32]
        self.max_hedge_levels = 6
        self.hedge_profit_target = 10  # USD
        self.martingale_multiplier = 2.0
        self.hedge_activation_loss = -5  # USD - when to start hedging
        self.max_drawdown = -100  # USD - emergency stop
        self.auto_hedge = True
        self.hedge_all_symbols = False
        self.correlation_threshold = 0.8

        # Risk management
        self.daily_profit_target = 50  # USD
        self.daily_loss_limit = -50  # USD
        self.daily_pnl = 0

        # Performance optimization
        self.price_monitoring_interval = 0.05  # 50ms for ultra-fast hedging
        self.hedge_opportunities = {}  # Track hedge opportunities by price level

    async def init_strategy_settings(self):
        """Initialize AdaptiveHedging specific settings"""
        try:
            # Load configuration with defaults
            self.hedge_distance = self.config.get("hedge_distance", 50)
            self.lot_progression = self.config.get(
                "lot_progression", [0.01, 0.02, 0.04, 0.08, 0.16, 0.32])
            self.max_hedge_levels = self.config.get("max_hedge_levels", 6)
            self.hedge_profit_target = self.config.get(
                "hedge_profit_target", 10)
            self.martingale_multiplier = self.config.get(
                "martingale_multiplier", 2.0)
            self.hedge_activation_loss = self.config.get(
                "hedge_activation_loss", -5)
            self.max_drawdown = self.config.get("max_drawdown", -100)
            self.auto_hedge = self.config.get("auto_hedge", True)
            self.hedge_all_symbols = self.config.get(
                "hedge_all_symbols", False)
            self.correlation_threshold = self.config.get(
                "correlation_threshold", 0.8)

            # Risk management settings
            self.daily_profit_target = self.config.get(
                "daily_profit_target", 50)
            self.daily_loss_limit = self.config.get("daily_loss_limit", -50)

            # Initialize hedge opportunities tracking
            self.hedge_opportunities = {}

            # Load daily PnL
            await self.load_daily_pnl()

            self.logger.info(f"AdaptiveHedging initialized for {self.symbol}:")
            self.logger.info(f"- hedge_distance: {self.hedge_distance} pips")
            self.logger.info(f"- max_hedge_levels: {self.max_hedge_levels}")
            self.logger.info(f"- auto_hedge: {self.auto_hedge}")

        except Exception as e:
            self.logger.error(
                f"Error initializing AdaptiveHedging settings: {e}")

    async def load_daily_pnl(self):
        """Load daily PnL from database"""
        try:
            today = datetime.utcnow().date().isoformat()

            # Get today's closed cycles
            cycles_result = await self.supabase_client.table('cycles').select(
                'total_profit'
            ).eq('account', self.bot.account_id).eq('bot', self.bot.id).eq(
                'is_closed', True
            ).gte('created_at', f"{today}T00:00:00").execute()

            self.daily_pnl = sum(cycle.get('total_profit', 0)
                                 for cycle in cycles_result.data)
            self.logger.info(f"Daily PnL loaded: ${self.daily_pnl:.2f}")

        except Exception as e:
            self.logger.error(f"Error loading daily PnL: {e}")
            self.daily_pnl = 0

    async def handle_event(self, event: Dict):
        """Handle incoming events with real-time processing"""
        try:
            content = event.get('content', {})
            message = content.get("message", "")

            if message == "open_order":
                await self.handle_open_order_event(content)
            elif message == "hedge_order":
                await self.handle_hedge_order_event(content)
            elif message == "close_cycle":
                await self.handle_close_cycle_event(content)
            elif message == "emergency_close":
                await self.handle_emergency_close_event(content)
            elif message == "adjust_hedge_levels":
                await self.handle_adjust_hedge_levels_event(content)
            elif message == "stop_bot":
                await self.handle_stop_bot_event()
            elif message == "start_bot":
                await self.handle_start_bot_event()
            else:
                self.logger.warning(f"Unknown event message: {message}")

        except Exception as e:
            self.logger.error(f"Error handling event: {e}")

    async def handle_open_order_event(self, content: Dict):
        """Handle initial order opening with hedge preparation"""
        if self.stop_requested:
            return

        try:
            username = content.get("user_name", "system")
            sent_by_admin = content.get("sent_by_admin", False)
            user_id = content.get("user_id", "")
            order_type = content.get('type', 0)
            price = content.get('price', 0)
            volume = content.get('volume', self.lot_progression[0])

            # Check daily limits
            if self.daily_pnl >= self.daily_profit_target:
                self.logger.info(
                    f"Daily profit target reached: ${self.daily_pnl:.2f}")
                return

            if self.daily_pnl <= self.daily_loss_limit:
                self.logger.warning(
                    f"Daily loss limit reached: ${self.daily_pnl:.2f}")
                return

            # Create initial order based on type
            if order_type == 0:  # BUY
                await self.create_initial_buy_order(price, volume, sent_by_admin, user_id, username)
            elif order_type == 1:  # SELL
                await self.create_initial_sell_order(price, volume, sent_by_admin, user_id, username)

        except Exception as e:
            self.logger.error(f"Error handling open order event: {e}")

    async def create_initial_buy_order(self, price: float, volume: float, sent_by_admin: bool, user_id: str, username: str):
        """Create initial BUY order with hedge levels prepared"""
        try:
            if price == 0:
                # Market order
                current_price = self.meta_trader.get_ask(self.symbol)
                order_data = {
                    'type': 'BUY',
                    'price': current_price,
                    'volume': volume,
                    'magic': self.bot.magic,
                    'sl': 0,
                    'tp': 0,
                    'slippage': 3,
                    'status': 'EXECUTED',
                    'order_type': 'initial',
                    'hedge_level': 0
                }

                # Execute market order
                mt_order = self.meta_trader.buy(
                    self.symbol, volume, self.bot.magic,
                    0, 0, "PIPS", 3, "initial"
                )

                if mt_order:
                    order_data['ticket'] = mt_order.get('ticket')
                    order_data['price'] = mt_order.get(
                        'price', order_data['price'])

                    # Create cycle
                    cycle_id = await self.create_cycle(order_data, None, "BUY", False)

                    if cycle_id:
                        # Prepare hedge levels
                        await self.prepare_hedge_levels(cycle_id, order_data['price'], 'BUY')

                        await self.send_event('INITIAL_BUY_ORDER_CREATED', {
                            'cycle_id': cycle_id,
                            'symbol': self.symbol,
                            'price': order_data['price'],
                            'volume': volume,
                            'username': username
                        })
            else:
                # Pending order implementation
                await self.create_pending_buy_order(price, volume, sent_by_admin, user_id, username)

        except Exception as e:
            self.logger.error(f"Error creating initial buy order: {e}")

    async def create_initial_sell_order(self, price: float, volume: float, sent_by_admin: bool, user_id: str, username: str):
        """Create initial SELL order with hedge levels prepared"""
        try:
            if price == 0:
                # Market order
                current_price = self.meta_trader.get_bid(self.symbol)
                order_data = {
                    'type': 'SELL',
                    'price': current_price,
                    'volume': volume,
                    'magic': self.bot.magic,
                    'sl': 0,
                    'tp': 0,
                    'slippage': 3,
                    'status': 'EXECUTED',
                    'order_type': 'initial',
                    'hedge_level': 0
                }

                # Execute market order
                mt_order = self.meta_trader.sell(
                    self.symbol, volume, self.bot.magic,
                    0, 0, "PIPS", 3, "initial"
                )

                if mt_order:
                    order_data['ticket'] = mt_order.get('ticket')
                    order_data['price'] = mt_order.get(
                        'price', order_data['price'])

                    # Create cycle
                    cycle_id = await self.create_cycle(order_data, None, "SELL", False)

                    if cycle_id:
                        # Prepare hedge levels
                        await self.prepare_hedge_levels(cycle_id, order_data['price'], 'SELL')

                        await self.send_event('INITIAL_SELL_ORDER_CREATED', {
                            'cycle_id': cycle_id,
                            'symbol': self.symbol,
                            'price': order_data['price'],
                            'volume': volume,
                            'username': username
                        })
            else:
                # Pending order implementation
                await self.create_pending_sell_order(price, volume, sent_by_admin, user_id, username)

        except Exception as e:
            self.logger.error(f"Error creating initial sell order: {e}")

    async def prepare_hedge_levels(self, cycle_id: str, entry_price: float, initial_direction: str):
        """Prepare hedge levels for the cycle"""
        try:
            point = self.meta_trader.get_point(self.symbol)
            hedge_distance_price = self.hedge_distance * point

            # Store hedge levels for this cycle
            self.hedge_opportunities[cycle_id] = {
                'entry_price': entry_price,
                'initial_direction': initial_direction,
                'hedge_levels': [],
                'current_hedge_level': 0,
                'total_volume': 0
            }

            # Calculate hedge levels
            for level in range(1, self.max_hedge_levels + 1):
                if initial_direction == 'BUY':
                    # For BUY, hedges are SELL orders below entry price
                    hedge_price = entry_price - (hedge_distance_price * level)
                    hedge_type = 'SELL'
                else:
                    # For SELL, hedges are BUY orders above entry price
                    hedge_price = entry_price + (hedge_distance_price * level)
                    hedge_type = 'BUY'

                hedge_volume = self.lot_progression[min(
                    level - 1, len(self.lot_progression) - 1)]

                self.hedge_opportunities[cycle_id]['hedge_levels'].append({
                    'level': level,
                    'price': hedge_price,
                    'type': hedge_type,
                    'volume': hedge_volume,
                    'activated': False
                })

            self.logger.info(
                f"Prepared {len(self.hedge_opportunities[cycle_id]['hedge_levels'])} hedge levels for cycle {cycle_id}")

        except Exception as e:
            self.logger.error(f"Error preparing hedge levels: {e}")

    async def handle_hedge_order_event(self, content: Dict):
        """Handle manual hedge order creation"""
        try:
            cycle_id = content.get('cycle_id')
            hedge_level = content.get('hedge_level', 1)

            if cycle_id in self.hedge_opportunities:
                await self.execute_hedge_order(cycle_id, hedge_level)
            else:
                self.logger.warning(
                    f"No hedge opportunities found for cycle {cycle_id}")

        except Exception as e:
            self.logger.error(f"Error handling hedge order event: {e}")

    async def execute_hedge_order(self, cycle_id: str, hedge_level: int):
        """Execute a hedge order at specified level"""
        try:
            hedge_info = self.hedge_opportunities.get(cycle_id)
            if not hedge_info:
                return

            # Find the hedge level
            hedge_data = None
            for level_data in hedge_info['hedge_levels']:
                if level_data['level'] == hedge_level and not level_data['activated']:
                    hedge_data = level_data
                    break

            if not hedge_data:
                self.logger.warning(
                    f"Hedge level {hedge_level} not found or already activated for cycle {cycle_id}")
                return

            # Execute hedge order
            order_data = {
                'type': hedge_data['type'],
                'price': hedge_data['price'],
                'volume': hedge_data['volume'],
                'magic': self.bot.magic,
                'sl': 0,
                'tp': 0,
                'slippage': 3,
                'status': 'EXECUTED',
                'order_type': 'hedge',
                'hedge_level': hedge_level
            }

            if hedge_data['type'] == 'BUY':
                mt_order = self.meta_trader.buy(
                    self.symbol, hedge_data['volume'], self.bot.magic,
                    0, 0, "PIPS", 3, f"hedge_level_{hedge_level}"
                )
            else:
                mt_order = self.meta_trader.sell(
                    self.symbol, hedge_data['volume'], self.bot.magic,
                    0, 0, "PIPS", 3, f"hedge_level_{hedge_level}"
                )

            if mt_order:
                order_data['ticket'] = mt_order.get('ticket')
                order_data['price'] = mt_order.get(
                    'price', order_data['price'])

                # Create order in database
                await self.create_order(cycle_id, order_data)

                # Mark hedge level as activated
                hedge_data['activated'] = True
                hedge_info['current_hedge_level'] = hedge_level
                hedge_info['total_volume'] += hedge_data['volume']

                # Check if cycle is now profitable for closing
                await self.check_hedge_cycle_profitability(cycle_id)

                await self.send_event('HEDGE_ORDER_EXECUTED', {
                    'cycle_id': cycle_id,
                    'hedge_level': hedge_level,
                    'symbol': self.symbol,
                    'price': order_data['price'],
                    'volume': hedge_data['volume'],
                    'type': hedge_data['type']
                })

        except Exception as e:
            self.logger.error(f"Error executing hedge order: {e}")

    async def check_hedge_cycle_profitability(self, cycle_id: str):
        """Check if hedged cycle is profitable and can be closed"""
        try:
            current_profit = await self.calculate_cycle_profit(cycle_id)

            if current_profit >= self.hedge_profit_target:
                await self.close_cycle(cycle_id, current_profit)

                # Clean up hedge opportunities
                if cycle_id in self.hedge_opportunities:
                    del self.hedge_opportunities[cycle_id]

                await self.send_event('HEDGE_CYCLE_CLOSED_PROFITABLE', {
                    'cycle_id': cycle_id,
                    'profit': current_profit
                })

        except Exception as e:
            self.logger.error(f"Error checking hedge cycle profitability: {e}")

    async def run(self):
        """Main strategy loop with ultra-fast price monitoring"""
        self.logger.info(
            f"Starting AdaptiveHedging main loop for {self.symbol}")

        # Initialize performance tracking
        self.update_count = 0
        self.last_update = datetime.utcnow()

        while self.is_running and not self.stop_requested:
            try:
                # Get all active cycles (like old implementation)
                await self.load_active_state()

                # Process each active cycle (like old implementation)
                tasks = []
                for cycle_id, cycle_data in self.active_cycles.items():
                    if not self.stop and not self.stop_requested:
                        # Manage cycle orders (equivalent to old manage_cycle_orders)
                        tasks.append(self.manage_hedge_cycle_orders(cycle_id))

                        # Update cycle profit
                        tasks.append(self.update_cycle_profit(cycle_id))

                        # Check take profit conditions
                        tasks.append(
                            self.check_hedge_cycle_profitability(cycle_id))

                # Ultra-fast price monitoring for hedge triggers
                if not self.stop and not self.stop_requested:
                    tasks.append(self.monitor_hedge_triggers())

                # Check daily limits
                tasks.append(self.check_daily_limits())

                # Risk management checks
                tasks.append(self.check_risk_management())

                # Execute all tasks concurrently (like old implementation)
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Performance tracking
                self.update_count += 1
                current_time = datetime.utcnow()

                if (current_time - self.last_update).seconds >= 30:
                    # Log performance every 30 seconds
                    updates_per_second = self.update_count / 30
                    self.logger.info(
                        f"AdaptiveHedging performance: {updates_per_second:.2f} updates/sec")
                    self.update_count = 0
                    self.last_update = current_time

                # Update interval (faster than old 1 second but not too fast)
                # 500ms for balance between performance and CPU usage
                await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

                # Handle connection failures
                if "connection" in str(e).lower():
                    if not await self.handle_connection_failure("main_loop"):
                        break

                await asyncio.sleep(1)  # Wait before retrying

        self.logger.info(
            f"AdaptiveHedging main loop stopped for {self.symbol}")

    async def monitor_hedge_triggers(self):
        """Monitor price movements for automatic hedge triggers"""
        try:
            if not self.auto_hedge:
                return

            current_price = self.meta_trader.get_ask(self.symbol)

            # Check each active cycle for hedge triggers
            for cycle_id, cycle_data in self.active_cycles.items():
                if cycle_id not in self.hedge_opportunities:
                    continue

                hedge_info = self.hedge_opportunities[cycle_id]
                current_profit = await self.calculate_cycle_profit(cycle_id)

                # Check if loss threshold reached
                if current_profit <= self.hedge_activation_loss:
                    await self.trigger_next_hedge_level(cycle_id, current_price)

                # Check for emergency closure
                if current_profit <= self.max_drawdown:
                    await self.emergency_close_cycle(cycle_id)

        except Exception as e:
            self.logger.error(f"Error monitoring hedge triggers: {e}")

    async def trigger_next_hedge_level(self, cycle_id: str, current_price: float):
        """Trigger the next hedge level based on price movement"""
        try:
            hedge_info = self.hedge_opportunities[cycle_id]

            # Find next unactivated hedge level
            for level_data in hedge_info['hedge_levels']:
                if not level_data['activated']:
                    # Check if current price has reached hedge trigger
                    if hedge_info['initial_direction'] == 'BUY':
                        # For BUY positions, hedge when price drops below hedge level
                        if current_price <= level_data['price']:
                            await self.execute_hedge_order(cycle_id, level_data['level'])
                            break
                    else:
                        # For SELL positions, hedge when price rises above hedge level
                        if current_price >= level_data['price']:
                            await self.execute_hedge_order(cycle_id, level_data['level'])
                            break

        except Exception as e:
            self.logger.error(f"Error triggering next hedge level: {e}")

    async def update_hedge_cycles(self):
        """Update hedge cycles with real-time profit calculations"""
        try:
            for cycle_id in list(self.active_cycles.keys()):
                if cycle_id in self.hedge_opportunities:
                    current_profit = await self.calculate_cycle_profit(cycle_id)

                    # Update cycle profit
                    await self.update_cycle(cycle_id, {'total_profit': current_profit})

                    # Check profitability
                    await self.check_hedge_cycle_profitability(cycle_id)

        except Exception as e:
            self.logger.error(f"Error updating hedge cycles: {e}")

    async def check_daily_limits(self):
        """Check daily profit/loss limits"""
        try:
            # Recalculate daily PnL
            await self.load_daily_pnl()

            if self.daily_pnl >= self.daily_profit_target:
                # Close all cycles and stop trading
                await self.close_all_cycles_for_day()

            elif self.daily_pnl <= self.daily_loss_limit:
                # Emergency close all and stop
                await self.emergency_close_all_cycles()

        except Exception as e:
            self.logger.error(f"Error checking daily limits: {e}")

    async def check_risk_management(self):
        """Perform risk management checks"""
        try:
            total_exposure = 0

            # Calculate total position exposure
            for cycle_id, hedge_info in self.hedge_opportunities.items():
                total_exposure += hedge_info.get('total_volume', 0)

            # Check if exposure is too high
            max_exposure = 1.0  # Maximum 1 lot total exposure
            if total_exposure > max_exposure:
                self.logger.warning(
                    f"High exposure detected: {total_exposure} lots")
                await self.send_event('HIGH_EXPOSURE_WARNING', {
                    'total_exposure': total_exposure,
                    'max_exposure': max_exposure
                }, 'WARNING')

        except Exception as e:
            self.logger.error(f"Error in risk management check: {e}")

    async def emergency_close_cycle(self, cycle_id: str):
        """Emergency close a cycle that has hit maximum drawdown"""
        try:
            current_profit = await self.calculate_cycle_profit(cycle_id)
            await self.close_cycle(cycle_id, current_profit)

            # Clean up hedge opportunities
            if cycle_id in self.hedge_opportunities:
                del self.hedge_opportunities[cycle_id]

            await self.send_event('EMERGENCY_CYCLE_CLOSED', {
                'cycle_id': cycle_id,
                'profit': current_profit,
                'reason': 'maximum_drawdown'
            }, 'ERROR')

        except Exception as e:
            self.logger.error(f"Error in emergency cycle closure: {e}")

    async def close_all_cycles_for_day(self):
        """Close all cycles when daily profit target is reached"""
        try:
            for cycle_id in list(self.active_cycles.keys()):
                profit = await self.calculate_cycle_profit(cycle_id)
                await self.close_cycle(cycle_id, profit)

            # Clear hedge opportunities
            self.hedge_opportunities.clear()

            await self.send_event('DAILY_TARGET_REACHED', {
                'daily_pnl': self.daily_pnl,
                'target': self.daily_profit_target
            })

        except Exception as e:
            self.logger.error(f"Error closing all cycles for day: {e}")

    async def emergency_close_all_cycles(self):
        """Emergency close all cycles when daily loss limit is reached"""
        try:
            for cycle_id in list(self.active_cycles.keys()):
                profit = await self.calculate_cycle_profit(cycle_id)
                await self.close_cycle(cycle_id, profit)

            # Clear hedge opportunities
            self.hedge_opportunities.clear()

            # Stop the bot
            self.stop_requested = True

            await self.send_event('DAILY_LOSS_LIMIT_REACHED', {
                'daily_pnl': self.daily_pnl,
                'limit': self.daily_loss_limit
            }, 'ERROR')

        except Exception as e:
            self.logger.error(f"Error in emergency close all cycles: {e}")

    async def handle_close_cycle_event(self, content: Dict):
        """Handle manual cycle closing"""
        try:
            cycle_id = content.get('id')
            if cycle_id in self.active_cycles:
                profit = await self.calculate_cycle_profit(cycle_id)
                await self.close_cycle(cycle_id, profit)

                # Clean up hedge opportunities
                if cycle_id in self.hedge_opportunities:
                    del self.hedge_opportunities[cycle_id]

        except Exception as e:
            self.logger.error(f"Error closing cycle: {e}")

    async def handle_emergency_close_event(self, content: Dict):
        """Handle emergency close event"""
        try:
            cycle_id = content.get('cycle_id')
            if cycle_id:
                await self.emergency_close_cycle(cycle_id)
            else:
                await self.emergency_close_all_cycles()

        except Exception as e:
            self.logger.error(f"Error handling emergency close: {e}")

    async def handle_adjust_hedge_levels_event(self, content: Dict):
        """Handle hedge level adjustment"""
        try:
            cycle_id = content.get('cycle_id')
            new_distance = content.get('new_distance', self.hedge_distance)

            if cycle_id in self.hedge_opportunities:
                # Recalculate hedge levels with new distance
                cycle_data = self.active_cycles[cycle_id]
                hedge_info = self.hedge_opportunities[cycle_id]

                # Update hedge distance
                self.hedge_distance = new_distance

                # Prepare new hedge levels
                await self.prepare_hedge_levels(
                    cycle_id,
                    hedge_info['entry_price'],
                    hedge_info['initial_direction']
                )

                await self.send_event('HEDGE_LEVELS_ADJUSTED', {
                    'cycle_id': cycle_id,
                    'new_distance': new_distance
                })

        except Exception as e:
            self.logger.error(f"Error adjusting hedge levels: {e}")

    async def handle_stop_bot_event(self):
        """Handle stop bot event"""
        self.stop_requested = True
        self.logger.info(f"Stop signal received for {self.symbol}")

    async def handle_start_bot_event(self):
        """Handle start bot event"""
        self.stop_requested = False
        await self.load_daily_pnl()  # Reload daily PnL on restart
        self.logger.info(f"Start signal received for {self.symbol}")

    async def create_pending_buy_order(self, price: float, volume: float, sent_by_admin: bool, user_id: str, username: str):
        """Create pending buy order (placeholder for pending order logic)"""
        self.logger.info(
            f"Pending buy order creation at {price} not fully implemented yet")

    async def create_pending_sell_order(self, price: float, volume: float, sent_by_admin: bool, user_id: str, username: str):
        """Create pending sell order (placeholder for pending order logic)"""
        self.logger.info(
            f"Pending sell order creation at {price} not fully implemented yet")

    async def manage_hedge_cycle_orders(self, cycle_id: str):
        """Manage hedge orders for a specific cycle (equivalent to old manage_cycle_orders)"""
        try:
            if cycle_id not in self.hedge_opportunities:
                return

            cycle_data = self.active_cycles.get(cycle_id)
            if not cycle_data:
                return

            # Get current profit to check hedge triggers
            current_profit = await self.calculate_cycle_profit(cycle_id)

            # Check if we need to trigger hedge levels based on loss
            if current_profit <= self.hedge_activation_loss:
                current_price = self.meta_trader.get_ask(self.symbol)
                await self.trigger_next_hedge_level(cycle_id, current_price)

        except Exception as e:
            self.logger.error(
                f"Error managing hedge cycle orders for {cycle_id}: {e}")

    async def update_cycle_profit(self, cycle_id: str):
        """Update cycle profit for hedge cycles"""
        try:
            current_profit = await self.calculate_cycle_profit(cycle_id)
            cycle_data = self.active_cycles.get(cycle_id)

            if cycle_data:
                last_profit = cycle_data.get('total_profit', 0)
                if abs(current_profit - last_profit) >= 0.01:  # Update if change > 1 cent
                    await self.update_cycle(cycle_id, {'total_profit': current_profit})

                    # Update daily PnL
                    self.daily_pnl += (current_profit - last_profit)

        except Exception as e:
            self.logger.error(
                f"Error updating cycle profit for {cycle_id}: {e}")
