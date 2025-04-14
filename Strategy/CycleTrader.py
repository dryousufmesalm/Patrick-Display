from Strategy.strategy import Strategy
import threading
from Orders.order import order
from cycles.CT_cycle import cycle
from DB.db_engine import engine
from DB.ct_strategy.repositories.ct_repo import CTRepo
import asyncio
from Views.globals.app_logger import app_logger as logger


class CycleTrader(Strategy):
    """ CycleTrader strategy """

    def __init__(self, meta_trader, config, client, symbol, bot):
        self.meta_trader = meta_trader
        self.config = config
        self.client = client
        self.positions = {}
        self.orders = {}
        self.symbol = symbol
        self.bot = bot
        self.enable_recovery = False
        self.lot_sizes = [0.01, 0.02, 0.03, 0.04,
                          0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
        self.margin = 10.8
        self.pips_step = 0
        self.slippage = 3
        self.sltp = "money"
        self.take_profit = 5
        self.zones = 500
        self.zone_forward = 1
        self.zone_forward2 = 1
        self.stop = False
        self.autotrade = False
        self.autotrade_threshold = 0
        self.max_cycles = 1
        self.local_api = CTRepo(engine=engine)
        self.settings = None
        self.last_cycle_price = self.meta_trader.get_ask(self.symbol)
        self.logger = logger
        self.hedges_numbers = None
        self.ADD_All_to_PNL = True
        self.autotrade_pips_restriction = 100
        self.init_settings()

    def initialize(self, config, settings):
        """ Initialize the CycleTrader strategy """
        self.update_configs(config, settings)

    def init_settings(self):
        """ Initialize the settings for the CycleTrader strategy """
        try:
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
            self.symbol = self.config.get('symbol', self.symbol)
            self.max_cycles = self.config.get("max_cycles", 1)
            self.autotrade = self.config.get("autotrade", False)
            self.autotrade_threshold = self.config.get(
                "autotrade_threshold", 0)
            self.hedges_numbers = self.config.get("hedges_numbers", 0)
            self.ADD_All_to_PNL = self.config.get(
                "buy_and_sell_add_to_pnl", True)
            self.autotrade_pips_restriction = self.config.get(
                "autotrade_pips_restriction", 100)

            if self.settings and hasattr(self.settings, 'stopped'):
                self.stop = self.settings.stopped
            else:
                self.stop = False

            self.last_cycle_price = self.meta_trader.get_ask(self.symbol)
            logger.info(
                f"CycleTrader settings initialized for {self.symbol} with zone_forward2={self.zone_forward2}")
        except Exception as e:
            logger.error(f"Error initializing CycleTrader settings: {e}")
            # Set default values for critical parameters
            if not hasattr(self, 'zone_forward2') or self.zone_forward2 is None:
                self.zone_forward2 = 1

    def update_configs(self, config, settings):
        """
        This function updates the settings for the adaptive hedging strategy.

        Parameters:
        config (dict): The new configuration settings for the strategy.

        Returns:
        None
        """
        try:
            if config is not None:
                self.config = config
            if settings is not None:
                self.settings = settings

            self.init_settings()
            logger.info(f"CycleTrader configs updated for {self.symbol}")
        except Exception as e:
            logger.error(f"Error updating CycleTrader configs: {e}")
            # Ensure critical parameters have default values if update fails
            if not hasattr(self, 'zone_forward2') or self.zone_forward2 is None:
                self.zone_forward2 = 1

    async def handle_event(self, event):
        """
        This function handles incoming events for the adaptive hedging strategy.

        Parameters:
        event (dict): The event data.

        Returns:
        None
        """
        try:
            print(f"Got event: {event}")
            content = event.content
            message = content["message"]
            if (message == "open_order"):
                username = content["user_name"]
                sent_by_admin = content["sent_by_admin"]
                user_id = content["user_id"]
                cycle_type = content['type']
                price = content['price']
                # wait_for_candle = content['wait_for_candle_to_close']
                # username= content['user_name']

                if (self.stop == False):
                    if (cycle_type == 0):
                        if (price == 0):
                            order1 = self.meta_trader.buy(
                                self.symbol, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "initial")
                            await self.create_cycle(
                                order1, None, False, sent_by_admin, user_id, username, "BUY")
                        elif (price > 0):
                            ask = self.meta_trader.get_ask(self.symbol)
                            if (price > ask):
                                # buy stop
                                order1 = self.meta_trader.buy_stop(
                                    self.symbol, price, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "pending")
                                await self.create_cycle(order1, None, True, sent_by_admin, user_id, username, "BUY")
                            else:
                                order1 = self.meta_trader.buy_limit(
                                    self.symbol, price, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "pending")
                                await self.create_cycle(order1, None, True, sent_by_admin, user_id, username, "BUY")
                    elif cycle_type == 1:
                        if (price == 0):
                            order1 = self.meta_trader.sell(
                                self.symbol, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "initial")
                            await self.create_cycle(
                                order1, None, False, sent_by_admin, user_id, username, "SELL")
                        elif (price > 0):
                            bid = self.meta_trader.get_bid(self.symbol)
                            if (price < bid):
                                # sell stop
                                order1 = self.meta_trader.sell_stop(
                                    self.symbol, price, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "pending")
                                await self.create_cycle(
                                    order1, None, True, sent_by_admin, user_id, username, "SELL")
                            else:
                                order1 = self.meta_trader.sell_limit(
                                    self.symbol, price, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "pending")
                                await self.create_cycle(
                                    order1, None, True, sent_by_admin, user_id, username, "SELL")
                    elif cycle_type == 2:
                        if (price == 0):
                            order1 = self.meta_trader.buy(
                                self.symbol, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "initial")
                            order2 = self.meta_trader.sell(
                                self.symbol, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "initial")
                            await self.create_cycle(order1, order2, False, sent_by_admin, user_id, username, "BUY&SELL")
                        elif (price > 0):
                            ask = self.meta_trader.get_ask(self.symbol)
                            bid = self.meta_trader.get_bid(self.symbol)
                            if (price > ask):
                                # buy stop
                                order1 = self.meta_trader.buy_stop(
                                    self.symbol, price, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "pending")
                                # order2= self.meta_trader.sell_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0, 0,"PIPS",self.slippage,"pending")
                                await self.create_cycle(order1, None, True, sent_by_admin, user_id, username, "BUY&SELL")
                            elif price < bid:
                                order1 = self.meta_trader.buy_limit(
                                    self.symbol, price, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "pending")
                                # order2= self.meta_trader.sell_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"pending")
                                await self.create_cycle(order1, None, True, sent_by_admin, user_id, username, "BUY&SELL")
                # close cycle
            elif message == "close_cycle":
                username = content["user_name"]
                sent_by_admin = content["sent_by_admin"]
                user_id = content["user_id"]
                cycle_id = content['id']
                cycle_data = self.local_api.get_cycle_by_remote_id(cycle_id)
                seleced_cycle = cycle(
                    cycle_data, self.meta_trader, self.meta_trader, "db")
                seleced_cycle.close_cycle(sent_by_admin, user_id, username)
                self.client.update_CT_cycle_by_id(
                    seleced_cycle.cycle_id, seleced_cycle.to_remote_dict())
            elif message == "update_order_configs":
                order_ticket = content["ticket"]
                sl = content['updated']['sl']
                tp = content['updated']['tp']
                ts = content['updated']['trailing_steps']
                order_data = self.local_api.get_order_by_ticket(order_ticket)
                order_obj = order(order_data, order_data.is_pending,
                                  self.meta_trader, self.local_api, "db")
                order_obj.update_order_configs(sl, tp, ts)
                order_obj.update_order()
            elif message == "close_order":
                order_ticket = content["ticket"]
                order_data = self.local_api.get_order_by_ticket(order_ticket)
                order_obj = order(order_data, order_data.is_pending,
                                  self.meta_trader, self.local_api, "db")
                order_obj.close_order()
            elif message == "close_all_cycles":
                active_cycles = await self.get_all_active_cycles()
                for cycle_data in active_cycles:
                    cycle_obj = cycle(cycle_data, self.meta_trader, self, "db")
                    cycle_obj.close_cycle(
                        content["sent_by_admin"], content["user_id"], content["user_name"])
                    self.client.update_CT_cycle_by_id(
                        cycle_obj.cycle_id, cycle_obj.to_remote_dict())
            elif message == "stop_bot":
                self.stop = True
                self.client.set_bot_stopped(event.bot)
            elif message == "start_bot":
                self.stop = False
                self.client.set_bot_running(event.bot)
            elif message == "close_all_pending_orders":
                orders = self.local_api.get_open_pending_orders()
                for order_data in orders:
                    if order_data.is_pending == False:
                        continue
                    order_obj = order(
                        order_data, order_data.is_pending, self.meta_trader, self.local_api, "db")
                    order_obj.close_order()
            elif message == "close_pending_order":
                order_ticket = content["ticket"]
                order_data = self.local_api.get_order_by_ticket(order_ticket)
                order_obj = order(order_data, order_data.is_pending,
                                  self.meta_trader, self.local_api, "db")
                order_obj.close_order()
        except Exception as e:
            self.logger.error(f"Error handling event: {e}")
            data = {
                "title":  "Error handling event",
                "body":     "Error handling event {} for bot {} ({})".format(
                    e, self.bot.name, self.bot.id),
                "data":     {
                    "bot": self.bot.id,
                    "event": self.event.name,
                    "message": str(e),

                },
                "bot": self.bot.id,
                "level": "error",
                "subject": "test",
                "group": "test"
            }

            self.client.send_log(data)

    def string_to_array(self, string):
        """
        This function converts a string to an array.

        Parameters:
        string (str): The string to convert.

        Returns:
        list: The converted array.
        """
        if string == "":
            return []
        float_array = [float(value.strip()) for value in string.split(",")]
        return float_array

    async def create_cycle(self, order1, order2, is_pending, sent_by_admin, user_id, username, cycle_type):
        """
        This function creates a cycle.

        Parameters:
        data (dict): The cycle data.

        Returns:
        None
        """
        try:
            lower_bound = float(order1[0].price_open) - float(
                self.zones[0]) * float(self.meta_trader.get_pips(self.symbol))
            upper_bound = float(order1[0].price_open) + float(
                self.zones[0]) * float(self.meta_trader.get_pips(self.symbol))
            upper_threshold = float(upper_bound) + float(
                self.zone_forward2 * float(self.meta_trader.get_pips(self.symbol)))
            lower_threshold = float(lower_bound) - float(
                self.zone_forward2 * float(self.meta_trader.get_pips(self.symbol)))
            data = {
                "account": self.bot.account.id,
                "bot": self.bot.id,
                "is_closed": False,
                "symbol": order1[0].symbol,
                "closing_method": {},
                "opened_by": {
                    "sent_by_admin": sent_by_admin,
                    "status": "Opened by User",
                    "user_id": user_id,
                    "user_name": username,
                },
                "lot_idx": 0,
                "status": "initial",
                "cycle_type": cycle_type,
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "is_pending": is_pending,
                "type": "initial",
                "total_volume": round(0, 2),
                "total_profit": round(0, 2),
                "initial": [],
                "hedge": [],
                "pending": [],
                "closed": [],
                "recovery": [],
                "threshold": [],
                "cycle_id": "",
                "zone_index": 0,
                "threshold_upper": upper_threshold,
                "threshold_lower": lower_threshold,
            }
            New_cycle = cycle(data, self.meta_trader, self.bot)
            New_cycle.open_price = order1[0].price_open
            if order1:
                order_obj = order(
                    order1[0], is_pending, self.meta_trader, self.local_api, "mt5", "")
                order_obj.create_order()
                if is_pending:
                    New_cycle.add_pending_order(order1[0].ticket)
                else:
                    New_cycle.add_initial_order(order1[0].ticket)
            if order2 and order2 != -2:
                order_obj = order(
                    order2[0], is_pending, self.meta_trader, self.local_api, "mt5", "")
                order_obj.create_order()
                if is_pending:
                    New_cycle.add_pending_order(order2[0].ticket)
                else:
                    New_cycle.add_initial_order(order2[0].ticket)
            res = self.client.create_CT_cycle(New_cycle.to_remote_dict())
            New_cycle.cycle_id = str(res.id)
            New_cycle.create_cycle()
        except Exception as e:
            self.logger.error(f"Error creating cycle: {e}")

    async def get_all_active_cycles(self):
        """
        Get all active cycles.
        """
        try:
            cycles = self.local_api.get_active_cycles(self.bot.id)
            active_cycles = [
                cycle for cycle in cycles if cycle.is_closed is False]

            return active_cycles
        except Exception as e:
            self.logger.error(f"Error getting active cycles: {e}")

    async def open_new_cycle(self, active_cycles, cycles_Restrition):
        """
        Open new cycle automatically every threshold pips from the last cycle with limit max cycles.
        """
        try:
            if len(active_cycles) < self.max_cycles:
                ask = self.meta_trader.get_ask(self.symbol)
                bid = self.meta_trader.get_bid(self.symbol)
                pips = self.meta_trader.get_pips(self.symbol)
                up_price = self.last_cycle_price+self.autotrade_threshold*pips
                down_price = self.last_cycle_price-self.autotrade_threshold*pips
                if ask >= up_price or bid <= down_price:
                    self.last_cycle_price = ask if ask >= up_price else bid if bid <= down_price else 0
                    # Check if autotrade is enabled AND either restrictions are disabled (value = 0) OR passed the check
                    if self.autotrade and (self.autotrade_pips_restriction == 0 or cycles_Restrition == False):
                        if self.stop is False:
                            order1 = self.meta_trader.buy(
                                self.symbol, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "initial")
                            order2 = self.meta_trader.sell(
                                self.symbol, self.lot_sizes[0], self.bot.magic, 0, 0, "PIPS", self.slippage, "initial")
                            await self.create_cycle(order1, order2, False,
                                                    False, 0, "MetaTrader5", "BUY&SELL")
        except Exception as e:
            self.logger.error(f"Error opening new cycle: {e}")

    async def run(self):
        """
        This function runs the adaptive hedging strategy.

        Parameters:
        None

        Returns:
        None
        """
        while True:
            try:
                active_cycles = await self.get_all_active_cycles()
                New_cycles_Restrition = False

                # Only calculate restrictions if autotrade_pips_restriction is not 0
                if self.autotrade_pips_restriction != 0:
                    ask = self.meta_trader.get_ask(self.symbol)
                    bid = self.meta_trader.get_bid(self.symbol)
                    pips = self.meta_trader.get_pips(self.symbol)
                    up_price = bid+(self.autotrade_pips_restriction/2)*pips
                    down_price = bid-(self.autotrade_pips_restriction/2)*pips

                    for cycle_data in active_cycles:
                        cycle_obj = cycle(
                            cycle_data, self.meta_trader, self, "db")
                        if len(cycle_obj.orders) <= 2 and len(cycle_obj.closed) == 0 and len(cycle_obj.hedge) == 0:
                            if cycle_obj.open_price > 0:
                                if cycle_obj.open_price > down_price and cycle_obj.open_price < up_price:
                                    New_cycles_Restrition = True

                tasks = []
                for cycle_data in active_cycles:
                    cycle_obj = cycle(cycle_data, self.meta_trader, self, "db")
                    if not self.stop:
                        tasks.append(cycle_obj.manage_cycle_orders(
                            self.zone_forward, self.zone_forward2))
                    tasks.append(cycle_obj.update_cycle(self.client))
                    tasks.append(cycle_obj.close_cycle_on_takeprofit(
                        self.take_profit, self.client))
                tasks.append(self.open_new_cycle(
                    active_cycles, New_cycles_Restrition))
                await asyncio.gather(*tasks)
            except Exception as e:
                self.logger.error(f"Error in run loop: {e}")
            await asyncio.sleep(1)

    async def run_in_thread(self):
        """
        This function runs the adaptive hedging strategy in a separate thread.
        """
        try:
            def run_coroutine_in_thread(loop, coro):
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coro)

            loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=run_coroutine_in_thread, args=(loop, self.run()), daemon=True)
            thread.start()
            self.logger.info("CycleTrader strategy running in thread")
        except Exception as e:
            self.logger.error(f"Error running in thread: {e}")
