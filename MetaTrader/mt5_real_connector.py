"""
Complete MetaTrader 5 Connector with Real Integration
Implements actual MT5 API calls for production trading
"""

import asyncio
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import MetaTrader5 as mt5
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PositionInfo:
    """Position information structure"""
    ticket: int
    symbol: str
    type: int
    volume: float
    price_open: float
    price_current: float
    profit: float
    swap: float
    commission: float
    comment: str
    magic: int


class MT5RealConnector:
    """
    Production MetaTrader 5 connector with real API integration
    Thread-safe operations with connection management
    """

    def __init__(self):
        self.is_initialized = False
        self.account_id = None
        self.password = None
        self.server = None
        self.login_info = None

        # Thread safety
        self.mt5_lock = threading.Lock()

        # Connection tracking
        self.last_connection_check = datetime.utcnow()
        self.connection_check_interval = 30  # seconds

        # Performance tracking
        self.request_count = 0
        self.error_count = 0

    async def initialize(self) -> bool:
        """Initialize MT5 terminal"""
        try:
            with self.mt5_lock:
                # Initialize MT5 connection
                if not mt5.initialize():
                    error_code = mt5.last_error()
                    logger.error(f"MT5 initialize failed: {error_code}")
                    return False

                self.is_initialized = True
                terminal_info = mt5.terminal_info()
                logger.info(
                    f"MT5 terminal initialized: {terminal_info.name} {terminal_info.build}")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize MT5: {e}")
            return False

    async def login(self, account_id: str, password: str = None, server: str = None) -> bool:
        """Login to MT5 account"""
        try:
            if not self.is_initialized:
                if not await self.initialize():
                    return False

            with self.mt5_lock:
                # Convert account_id to integer if it's a string
                account_num = int(account_id) if isinstance(
                    account_id, str) else account_id

                # Attempt login
                if password and server:
                    authorized = mt5.login(
                        account_num, password=password, server=server)
                else:
                    authorized = mt5.login(account_num)

                if not authorized:
                    error_code = mt5.last_error()
                    logger.error(
                        f"MT5 login failed for account {account_id}: {error_code}")
                    return False

                # Store login info
                self.account_id = account_id
                self.password = password
                self.server = server
                self.login_info = mt5.account_info()

                logger.info(f"MT5 login successful for account {account_id}")
                logger.info(
                    f"Account info: Balance={self.login_info.balance}, Equity={self.login_info.equity}")
                return True

        except Exception as e:
            logger.error(f"Failed to login to MT5: {e}")
            return False

    async def close(self):
        """Close MT5 connection"""
        try:
            with self.mt5_lock:
                mt5.shutdown()

            self.is_initialized = False
            self.account_id = None
            self.password = None
            self.server = None
            self.login_info = None

            logger.info("MT5 connection closed")

        except Exception as e:
            logger.error(f"Error closing MT5 connection: {e}")

    def is_connected(self) -> bool:
        """Check if MT5 is connected"""
        try:
            with self.mt5_lock:
                terminal_info = mt5.terminal_info()
                account_info = mt5.account_info()

                return (self.is_initialized and
                        terminal_info is not None and
                        account_info is not None and
                        terminal_info.connected)

        except Exception as e:
            logger.error(f"Error checking connection: {e}")
            return False

    async def reconnect(self) -> bool:
        """Reconnect to MT5"""
        try:
            logger.info("Attempting to reconnect to MT5...")

            # Close existing connection
            await self.close()

            # Re-initialize and login
            if await self.initialize():
                if self.account_id:
                    return await self.login(self.account_id, self.password, self.server)
                return True

            return False

        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            return False

    async def ensure_connected(self) -> bool:
        """Ensure connection is active"""
        current_time = datetime.utcnow()

        # Check connection periodically
        if (current_time - self.last_connection_check).seconds > self.connection_check_interval:
            self.last_connection_check = current_time

            if not self.is_connected():
                logger.warning(
                    "MT5 connection lost, attempting reconnection...")
                return await self.reconnect()

        return True

    # Market Data Methods
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information"""
        try:
            with self.mt5_lock:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    return None

                return {
                    'symbol': symbol_info.name,
                    'bid': symbol_info.bid,
                    'ask': symbol_info.ask,
                    'point': symbol_info.point,
                    'digits': symbol_info.digits,
                    'spread': symbol_info.spread,
                    'volume_min': symbol_info.volume_min,
                    'volume_max': symbol_info.volume_max,
                    'volume_step': symbol_info.volume_step
                }

        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            self.error_count += 1
            return None

    def get_ask(self, symbol: str) -> float:
        """Get ask price for symbol"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            return symbol_info['ask'] if symbol_info else 0.0
        except Exception as e:
            logger.error(f"Error getting ask price for {symbol}: {e}")
            return 0.0

    def get_bid(self, symbol: str) -> float:
        """Get bid price for symbol"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            return symbol_info['bid'] if symbol_info else 0.0
        except Exception as e:
            logger.error(f"Error getting bid price for {symbol}: {e}")
            return 0.0

    def get_pips(self, symbol: str) -> float:
        """Get pip value for symbol"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info:
                point = symbol_info['point']
                digits = symbol_info['digits']
                # For most forex pairs, pip = point * 10 if 5 digits, point if 4 digits
                return point * 10 if digits == 5 else point
            return 0.0001  # Default pip value
        except Exception as e:
            logger.error(f"Error getting pip value for {symbol}: {e}")
            return 0.0001

    def get_point(self, symbol: str) -> float:
        """Get point value for symbol"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            return symbol_info['point'] if symbol_info else 0.00001
        except Exception as e:
            logger.error(f"Error getting point value for {symbol}: {e}")
            return 0.00001

    # Position Management Methods
    def get_all_positions(self) -> List[PositionInfo]:
        """Get all open positions"""
        try:
            with self.mt5_lock:
                positions = mt5.positions_get()
                if positions is None:
                    return []

                position_list = []
                for pos in positions:
                    position_info = PositionInfo(
                        ticket=pos.ticket,
                        symbol=pos.symbol,
                        type=pos.type,
                        volume=pos.volume,
                        price_open=pos.price_open,
                        price_current=pos.price_current,
                        profit=pos.profit,
                        swap=pos.swap,
                        commission=pos.commission,
                        comment=pos.comment,
                        magic=pos.magic
                    )
                    position_list.append(position_info)

                return position_list

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            self.error_count += 1
            return []

    def check_order_is_closed(self, ticket: int) -> bool:
        """Check if order is closed"""
        try:
            with self.mt5_lock:
                # Check if position still exists
                position = mt5.positions_get(ticket=ticket)
                if position:
                    return False  # Position still open

                # Check in history
                history = mt5.history_deals_get(ticket=ticket)
                return history is not None and len(history) > 0

        except Exception as e:
            logger.error(f"Error checking order status for {ticket}: {e}")
            return False

    def get_deals_by_ticket(self, ticket: int) -> List[Dict]:
        """Get deal history for a ticket"""
        try:
            with self.mt5_lock:
                # Get deals for the specific position
                deals = mt5.history_deals_get(position=ticket)
                if deals is None:
                    return []

                deal_list = []
                for deal in deals:
                    deal_info = {
                        'ticket': deal.ticket,
                        'position': deal.position,
                        'type': deal.type,
                        'volume': deal.volume,
                        'price': deal.price,
                        'profit': deal.profit,
                        'swap': deal.swap,
                        'commission': deal.commission,
                        'time': deal.time,
                        'comment': deal.comment
                    }
                    deal_list.append(deal_info)

                return deal_list

        except Exception as e:
            logger.error(f"Error getting deals for ticket {ticket}: {e}")
            return []

    # Trading Operations
    def buy(self, symbol: str, volume: float, magic: int, sl: float = 0, tp: float = 0,
            deviation: int = 20, comment: str = "") -> Optional[Dict]:
        """Execute buy order"""
        try:
            with self.mt5_lock:
                price = mt5.symbol_info_tick(symbol).ask

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": volume,
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "deviation": deviation,
                    "magic": magic,
                    "comment": comment,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                result = mt5.order_send(request)

                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(
                        f"Buy order failed: {result.retcode} - {result.comment}")
                    return None

                self.request_count += 1
                logger.info(
                    f"Buy order executed: {symbol} {volume} lots at {price}")

                return {
                    'ticket': result.order,
                    'price': price,
                    'volume': volume,
                    'retcode': result.retcode
                }

        except Exception as e:
            logger.error(f"Error executing buy order: {e}")
            self.error_count += 1
            return None

    def sell(self, symbol: str, volume: float, magic: int, sl: float = 0, tp: float = 0,
             deviation: int = 20, comment: str = "") -> Optional[Dict]:
        """Execute sell order"""
        try:
            with self.mt5_lock:
                price = mt5.symbol_info_tick(symbol).bid

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": volume,
                    "type": mt5.ORDER_TYPE_SELL,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "deviation": deviation,
                    "magic": magic,
                    "comment": comment,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                result = mt5.order_send(request)

                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(
                        f"Sell order failed: {result.retcode} - {result.comment}")
                    return None

                self.request_count += 1
                logger.info(
                    f"Sell order executed: {symbol} {volume} lots at {price}")

                return {
                    'ticket': result.order,
                    'price': price,
                    'volume': volume,
                    'retcode': result.retcode
                }

        except Exception as e:
            logger.error(f"Error executing sell order: {e}")
            self.error_count += 1
            return None

    def close_order(self, ticket: int) -> bool:
        """Close order by ticket"""
        try:
            with self.mt5_lock:
                # Get position info
                position = mt5.positions_get(ticket=ticket)
                if not position:
                    logger.warning(f"Position {ticket} not found")
                    return False

                pos = position[0]

                # Determine close type and price
                close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
                close_price = mt5.symbol_info_tick(
                    pos.symbol).bid if pos.type == 0 else mt5.symbol_info_tick(pos.symbol).ask

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "type": close_type,
                    "position": ticket,
                    "price": close_price,
                    "deviation": 20,
                    "magic": pos.magic,
                    "comment": f"Close #{ticket}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                result = mt5.order_send(request)

                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(
                        f"Close order failed: {result.retcode} - {result.comment}")
                    return False

                self.request_count += 1
                logger.info(f"Order {ticket} closed successfully")
                return True

        except Exception as e:
            logger.error(f"Error closing order {ticket}: {e}")
            self.error_count += 1
            return False

    def modify_order(self, ticket: int, sl: float, tp: float) -> bool:
        """Modify order SL/TP"""
        try:
            with self.mt5_lock:
                # Get position info
                position = mt5.positions_get(ticket=ticket)
                if not position:
                    logger.warning(f"Position {ticket} not found")
                    return False

                pos = position[0]

                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": pos.symbol,
                    "position": ticket,
                    "sl": sl,
                    "tp": tp,
                }

                result = mt5.order_send(request)

                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(
                        f"Modify order failed: {result.retcode} - {result.comment}")
                    return False

                self.request_count += 1
                logger.info(f"Order {ticket} modified: SL={sl}, TP={tp}")
                return True

        except Exception as e:
            logger.error(f"Error modifying order {ticket}: {e}")
            self.error_count += 1
            return False

    # Candle Data Methods
    def get_last_candle(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get last candle data"""
        try:
            with self.mt5_lock:
                # Convert timeframe string to MT5 constant
                tf_map = {
                    'M1': mt5.TIMEFRAME_M1,
                    'M5': mt5.TIMEFRAME_M5,
                    'M15': mt5.TIMEFRAME_M15,
                    'M30': mt5.TIMEFRAME_M30,
                    'H1': mt5.TIMEFRAME_H1,
                    'H4': mt5.TIMEFRAME_H4,
                    'D1': mt5.TIMEFRAME_D1
                }

                tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)

                # Get last candle
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 1)
                if rates is None or len(rates) == 0:
                    return None

                candle = rates[0]
                return {
                    'time': candle['time'],
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['tick_volume']
                }

        except Exception as e:
            logger.error(f"Error getting last candle for {symbol}: {e}")
            return None

    def check_candle_direction(self, symbol: str, timeframe: str) -> Optional[str]:
        """Check candle direction"""
        candle = self.get_last_candle(symbol, timeframe)
        if candle:
            if candle['close'] > candle['open']:
                return "UP"
            elif candle['close'] < candle['open']:
                return "DOWN"
            else:
                return "NEUTRAL"
        return None

    def get_current_candle_time(self, symbol: str, timeframe: str) -> float:
        """Get current candle time"""
        candle = self.get_last_candle(symbol, timeframe)
        return candle['time'] if candle else datetime.utcnow().timestamp()

    # Performance and Status Methods
    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        try:
            with self.mt5_lock:
                account_info = mt5.account_info()
                if account_info is None:
                    return None

                return {
                    'login': account_info.login,
                    'trade_mode': account_info.trade_mode,
                    'name': account_info.name,
                    'server': account_info.server,
                    'currency': account_info.currency,
                    'leverage': account_info.leverage,
                    'limit_orders': account_info.limit_orders,
                    'margin_so_mode': account_info.margin_so_mode,
                    'trade_allowed': account_info.trade_allowed,
                    'trade_expert': account_info.trade_expert,
                    'margin_mode': account_info.margin_mode,
                    'currency_digits': account_info.currency_digits,
                    'balance': account_info.balance,
                    'credit': account_info.credit,
                    'profit': account_info.profit,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'margin_free': account_info.margin_free,
                    'margin_level': account_info.margin_level
                }

        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            'is_connected': self.is_connected(),
            'is_initialized': self.is_initialized,
            'account_id': self.account_id,
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'last_connection_check': self.last_connection_check.isoformat()
        }
