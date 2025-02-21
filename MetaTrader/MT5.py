""" MetaTrader 5 expert advisor class to manage the MetaTrader 5 expert advisor. """
# from aiomql import MetaTrader as MT5
from Views.globals.app_state import store
import MetaTrader5 as Mt5
# Mt5=MT5()


class MetaTrader:
    """Trader class to manage the MetaTrader 5 expert advisor."""

    def __init__(self, username, password, server):
        self.username = int(username)
        self.password = password
        self.server = server
        self.authorized = False
        self.account_id = username

    def initialize(self, path):
        launched = False
        if path == "":
            launched = Mt5.initialize()
        else:
            launched = Mt5.initialize(path)
        if launched == False:
            print(
                'Initialization failed, check internet connection. You must have Meta Trader 5 installed.')
            Mt5.shutdown()
        else:
            print('You are connected to your MetaTrader account.')
            return self.connect()

    def connect(self):
        """ Connect to the MetaTrader 5 account """
        if self.server == "" or self.password == "":
            if self.username != "":
                self.authorized = Mt5.login(self.username)
                store.Mt5_authorized = self.authorized
                self.account_id = self.username
                return self.authorized
            else:
                print('Please provide your MetaTrader 5 account number and password.')
                return False
        else:
            self.authorized = Mt5.login(
                self.username, self.password, self.server)
            store.Mt5_authorized = self.authorized
        if not self.authorized:
            print('Login failed, check your account number and password.')
            Mt5.shutdown()
            return self.authorized
        else:
            print('You are connected to your MetaTrader account.')
            return self.authorized

    def get_account_info(self):
        # The `get_account_info` method in the `MetaTrader` class is a function that retrieves and
        # returns information about the MetaTrader 5 account. It calls the `account_info()` function
        # from the MetaTrader5 library, which provides details such as the account balance, equity,
        # margin, free margin, and other account-related information. This method allows you to access
        # and display important account information within your MetaTrader 5 expert advisor.
        """ Get account information """
        account = Mt5.account_info()
        if account is None:
            print("Failed to get account information")
            return False
        return account._asdict()

    def get_points(self, symbol):
        """ Get the point value of a symbol """
        return Mt5.symbol_info(symbol).point

    def get_symbol_spread(self, symbol):
        """ Get the spread of a symbol """
        return Mt5.symbol_info(symbol).spread

    def get_pips(self, symbol):
        """ Get the pips of a symbol """
        return Mt5.symbol_info(symbol).point * 10

    def get_ask(self, symbol):
        """ Get the ask price of a symbol """
        return Mt5.symbol_info(symbol).ask

    def get_bid(self, symbol):
        """ Get the bid price of a symbol """
        return Mt5.symbol_info(symbol).bid

    def get_symbol_info(self, symbol):
        """ Get the symbol information """
        return Mt5.symbol_info(symbol)

    def get_symbols_from_watch(self):
        """ Get the symbols from a market """
        symbols = Mt5.symbols_get()
        return symbols

    def buy(self, symbol, volume, magic, sl, tp, sltp_type, slippage, comment=None):
        """ Buy a symbol """
        symbol_info = Mt5.symbol_info(symbol)
        ask = symbol_info.ask
        bid = symbol_info.bid
        point = symbol_info.point
        pip = symbol_info.point*10

        # only if tp is not None and sl is not None

        # if sltp_type is "POINTS" convert sl and tp to points
        if (sltp_type == "POINTS"):
            if sl > 0:
                sl = bid - (point * sl)
            if tp > 0:
                tp = ask + (point * tp)

        elif (sltp_type == "PIPS"):
            if sl > 0:
                sl = bid - (pip * sl)
            if tp > 0:
                tp = ask + (pip * tp)

        request = {
            "action": Mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": Mt5.ORDER_TYPE_BUY,
            "price": ask,
            "magic": magic,
            "comment": comment,
            "type_time": Mt5.ORDER_TIME_GTC,
            "type_filling": Mt5.ORDER_FILLING_FOK,
            "deviation": slippage
        }
        if tp > 0:
            request["tp"] = tp
        if sl > 0:
            request["sl"] = sl

        result = Mt5.order_send(request)
        if result.retcode != Mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}".format(result.retcode))
            return []
        # request the result as a dictionary and display it element by element
        result_dict = result._asdict()
        ticket = result_dict["order"]
        order_data = []
        while len(order_data) == 0:
            order_data = self.get_position_by_ticket(ticket)
        return order_data

    def sell(self, symbol, volume, magic, sl, tp, sltp_type, slippage, comment=None):
        """ Sell a symbol """
        symbol_info = Mt5.symbol_info(symbol)
        ask = symbol_info.ask
        bid = symbol_info.bid
        point = symbol_info.point
        pip = symbol_info.point*10

        # only if tp is not None and sl is not None

        # if sltp_type is "POINTS" convert sl and tp to points
        if (sltp_type == "POINTS"):
            if sl > 0:
                sl = ask + (point * sl)
            if tp > 0:
                tp = bid - (point * tp)

        elif (sltp_type == "PIPS"):
            if sl > 0:
                sl = ask + (pip * sl)
            if tp > 0:
                tp = bid - (pip * tp)

        request = {
            "action": Mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": Mt5.ORDER_TYPE_SELL,
            "price": bid,
            "magic": magic,
            "comment": comment,
            "type_time": Mt5.ORDER_TIME_GTC,
            "type_filling": Mt5.ORDER_FILLING_FOK,
            "deviation": slippage
        }
        if tp > 0:
            request["tp"] = tp

        if sl > 0:
            request["sl"] = sl

        result = Mt5.order_send(request)
        if result.retcode != Mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}".format(result.retcode))
            return []

        # request the result as a dictionary and display it element by element
        result_dict = result._asdict()
        ticket = result_dict["order"]
        order_data = []
        while len(order_data) == 0:
            order_data = self.get_position_by_ticket(ticket)
        return order_data

    def get_position_by_ticket(self, ticket):
        """ Get a position by its ticket """
        return Mt5.positions_get(ticket=ticket)

    def get_all_positions(self):
        """ Get all positions """
        return Mt5.positions_get()
    # get order by ticket

    def get_order_by_ticket(self, ticket):
        """ Get an order by its ticket """
        return Mt5.orders_get(ticket=ticket)
    # get all orders

    def get_all_orders(self):
        """ Get all order open orders """
        return Mt5.orders_get()
    # buy stop

    def buy_stop(self, symbol, price, volume, magic, sl, tp, sltp_type, slippage, comment=None):
        """ Buy a symbol with stop loss """
        symbol_info = Mt5.symbol_info(symbol)
        point = symbol_info.point
        pip = symbol_info.point*10

        # only if tp is not None and sl is not None

        # if sltp_type is "POINTS" convert sl and tp to points
        if (sltp_type == "POINTS"):
            if sl > 0:
                sl = price - (point * sl)
            if tp > 0:
                tp = price + (point * tp)

        elif (sltp_type == "PIPS"):
            if sl > 0:
                sl = price - (pip * sl)
            if tp > 0:
                tp = price + (pip * tp)

        request = {
            "action": Mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(volume),
            "type": Mt5.ORDER_TYPE_BUY_STOP,
            "price": float(price),
            "magic": magic,
            "comment": comment,
            "type_time": Mt5.ORDER_TIME_GTC,
            "type_filling": Mt5.ORDER_FILLING_FOK,
            "deviation": slippage
        }
        if tp > 0:
            request["tp"] = tp

        if sl > 0:
            request["sl"] = sl

        result = Mt5.order_send(request)
        if result.retcode != Mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}".format(result.retcode))
            return []
        # request the result as a dictionary and display it element by element
        result_dict = result._asdict()
        ticket = result_dict["order"]
        order_data = []
        while len(order_data) == 0:
            order_data = self.get_order_by_ticket(ticket)
        return order_data

    # sell stop

    def sell_stop(self, symbol, price, volume, magic, sl, tp, sltp_type, slippage, comment=None):
        """ Sell a symbol with stop loss """
        symbol_info = Mt5.symbol_info(symbol)
        point = symbol_info.point
        pip = symbol_info.point*10

        # only if tp is not None and sl is not None

        # if sltp_type is "POINTS" convert sl and tp to points
        if (sltp_type == "POINTS"):
            if sl > 0:
                sl = price + (point * sl)
            if tp > 0:
                tp = price - (point * tp)

        elif (sltp_type == "PIPS"):
            if sl > 0:
                sl = price + (pip * sl)
            if tp > 0:
                tp = price - (pip * tp)

        request = {
            "action": Mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(volume),
            "type": Mt5.ORDER_TYPE_SELL_STOP,
            "price": float(price),
            "magic": magic,
            "comment": comment,
            "type_time": Mt5.ORDER_TIME_GTC,
            "type_filling": Mt5.ORDER_FILLING_FOK,
            "deviation": slippage
        }
        if tp > 0:
            request["tp"] = tp

        if sl > 0:
            request["sl"] = sl

        result = Mt5.order_send(request)
        if result.retcode != Mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}".format(result.retcode))
            return []
        # request the result as a dictionary and display it element by element
        result_dict = result._asdict()
        ticket = result_dict["order"]
        order_data = []
        while len(order_data) == 0:
            order_data = self.get_order_by_ticket(ticket)
        return order_data

    # buy limit

    def buy_limit(self, symbol, price, volume, magic, sl, tp, sltp_type, slippage, comment=None):
        """ Buy a symbol with limit price """
        symbol_info = Mt5.symbol_info(symbol)
        point = symbol_info.point
        pip = symbol_info.point * 10

        # only if tp is not None and sl is not None

        # if sltp_type is "POINTS" convert sl and tp to points
        if sltp_type == "POINTS":
            if sl > 0:
                sl = price - (point * sl)
            if tp > 0:
                tp = price + (point * tp)

        elif sltp_type == "PIPS":
            if sl > 0:
                sl = price - (pip * sl)
            if tp > 0:
                tp = price + (pip * tp)

        request = {
            "action": Mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(volume),
            "type": Mt5.ORDER_TYPE_BUY_LIMIT,
            "price": float(price),
            "magic": magic,
            "comment": comment,
            "type_time": Mt5.ORDER_TIME_GTC,
            "type_filling": Mt5.ORDER_FILLING_RETURN,
            "deviation": slippage
        }
        if tp > 0:
            request["tp"] = tp

        if sl > 0:
            request["sl"] = sl

        result = Mt5.order_send(request)
        if result.retcode != Mt5.TRADE_RETCODE_DONE:
            print(f"2. order_send failed, retcode={result.retcode}")
            return []
        # request the result as a dictionary and display it element by element
        result_dict = result._asdict()
        ticket = result_dict["order"]
        order_data = []
        while len(order_data) == 0:
            order_data = self.get_order_by_ticket(ticket)
        return order_data

    # sell limit

    def sell_limit(self, symbol, price, volume, magic, sl, tp, sltp_type, slippage, comment=None):
        """ Sell a symbol with limit price """
        symbol_info = Mt5.symbol_info(symbol)
        point = symbol_info.point
        pip = symbol_info.point*10

        # only if tp is not None and sl is not None

        # if sltp_type is "POINTS" convert sl and tp to points
        if (sltp_type == "POINTS"):
            if sl > 0:
                sl = price + (point * sl)
            if tp > 0:
                tp = price - (point * tp)

        elif (sltp_type == "PIPS"):
            if sl > 0:
                sl = price + (pip * sl)
            if tp > 0:
                tp = price - (pip * tp)

        request = {
            "action": Mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(volume),
            "type": Mt5.ORDER_TYPE_SELL_LIMIT,
            "price": float(price),
            "magic": magic,
            "comment": comment,
            "type_time": Mt5.ORDER_TIME_GTC,
            "type_filling": Mt5.ORDER_FILLING_FOK,
            "deviation": slippage
        }
        if tp > 0:
            request["tp"] = tp

        if sl > 0:
            request["sl"] = sl

        result = Mt5.order_send(request)
        if result.retcode != Mt5.TRADE_RETCODE_DONE:
            print("2. order_send failed, retcode={}".format(result.retcode))
            return []
        # request the result as a dictionary and display it element by element
        result_dict = result._asdict()
        ticket = result_dict["order"]
        order_data = []
        while len(order_data) == 0:
            order_data = self.get_order_by_ticket(ticket)
        return order_data

    # close position
    def close_position(self, order, deviation):
        '''https://www.mql5.com/en/docs/integration/python_metatrader5/mt5ordersend_py
        '''
        # create a close request
        symbol = order['symbol']
        action = order['type']
        price = 0.0
        trade_type = order['type']
        if action == Mt5.ORDER_TYPE_BUY:
            trade_type = Mt5.ORDER_TYPE_SELL
            price = Mt5.symbol_info_tick(symbol).bid
        elif action == Mt5.ORDER_TYPE_SELL:
            trade_type = Mt5.ORDER_TYPE_BUY
            price = Mt5.symbol_info_tick(symbol).ask
        position_id = order['ticket']
        lot = order['volume']
        ea_magic_number = order['magic_number']

        close_request = {
            "action": Mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": trade_type,
            "position": position_id,
            "price": float(price),
            "deviation": deviation,
            "magic": ea_magic_number,
            "comment": "python script close",
            "type_time": Mt5.ORDER_TIME_GTC,  # good till cancelled
            "type_filling": Mt5.ORDER_FILLING_FOK,
        }
        # send a close request
        result = Mt5.order_send(close_request)
        return result
    # def  close order

    def close_order(self, order, deviation):
        '''https://www.mql5.com/en/docs/integration/python_metatrader5/mt5ordersend_py
        '''
        # create a close request
        symbol = order['symbol']
        action = order['type']
        price = 0.0
        trade_type = order['type']
        order_id = order['ticket']
        lot = order['volume']
        ea_magic_number = order['magic_number']

        close_request = {
            "action": Mt5.TRADE_ACTION_REMOVE,
            "symbol": symbol,
            "volume": float(lot),
            "type": trade_type,
            "order": order_id,
            "price": float(price),
            "deviation": deviation,
            "magic": ea_magic_number,
            "comment": "python script close",
            "type_time": Mt5.ORDER_TIME_GTC,  # good till cancelled
            "type_filling": Mt5.ORDER_FILLING_FOK,
        }
        # send a close request
        result = Mt5.order_send(close_request)
        return result
    # check if order is pending

    def check_order_is_pending(self, ticket):
        """
                #    Example usage:
        # ticket = 12345678  # replace with your order ticket
        # if is_order_pending(ticket):
        #     print(f"Order {ticket} is pending")
        # else:
        #     print(f"Order {ticket} is not pending")
            """
        order = self.get_order_by_ticket(ticket=ticket)
        if len(order) > 0:
            return True
        order = self.get_position_by_ticket(ticket=ticket)
        if len(order) > 0:
            return False
        return False

    # check if order is closed
    def check_order_is_closed(self, ticket):
        """
                #    Example usage:
        # ticket = 12345678  # replace with your order ticket
        # if is_order_closed(ticket):
        #     print(f"Order {ticket} is closed")
        # else:
        #     print(f"Order {ticket} is not closed")
            """
        order = self.get_order_by_ticket(ticket=ticket)
        if len(order) > 0:
            return False
        order = self.get_position_by_ticket(ticket=ticket)
        if len(order) > 0:
            return False

        return True
