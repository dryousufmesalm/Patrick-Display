from Strategy.strategy import Strategy
import  threading
from Orders.order import order
from cycles.CT_cycle  import cycle
from DB.db_engine import engine
from DB.ct_strategy.repositories.ct_repo import CTRepo
class CycleTrader(Strategy):
    """ CycleTrader strategy """
    def __init__(self, meta_trader, config, client,symbol,bot):
        self.meta_trader = meta_trader
        self.config = config
        self.client = client
        self.positions = {}
        self.orders = {}
        self.symbol = symbol
        self.bot = bot
        self.enable_recovery = False
        self.lot_sizes = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
        self.margin = 10.8
        self.pips_step = 0
        self.slippage = 3
        self.sltp = "money"
        self.take_profit = 5
        self.zones = 500
        self.zone_forward = 1
        self.stop=False
        self.autotrade=False
        self.autotrade_threshold=0
        self.max_cycles=1
        self.local_api=CTRepo(engine=engine)
        self.settings=None
        self.last_cycle_price=None
        self.init_settings()
    def initialize(self,config,settings):
        """ Initialize the CycleTrader strategy """
        self.update_configs(config,settings)
    def init_settings(self):
        """ Initialize the settings for the CycleTrader strategy """
        self.enable_recovery = self.config["enabel_recovery"]
        self.lot_sizes = self.string_to_array( self.config["lot_sizes"])
        self.pips_step = self.config["pips_step"]
        self.slippage = self.config["slippage"]
        self.sltp = self.config["sltp"]
        self.take_profit = self.config["take_profit"]
        self.zones = self.string_to_array(self.config['zone_array'])
        self.zone_forward = self.config["zone_forward"]
        self.symbol = self.config['symbol']
        self.max_cycles = self.config["max_cycles"]
        self.autotrade = self.config["autotrade"]
        self.autotrade_threshold = self.config["autotrade_threshold"]
        if self.settings and hasattr(self.settings, 'stopped'):
            self.stop = self.settings.stopped
        else:
            self.stop = False
        self.last_cycle_price= self.meta_trader.get_ask(self.symbol)
    def update_configs(self, config,settings):
        """
        This function updates the settings for the adaptive hedging strategy.

        Parameters:
        config (dict): The new configuration settings for the strategy.

        Returns:
        None
        """
        self.config = config
        self.settings = settings
        self.init_settings()
    
    def handle_event(self, event):                                                                                                      
        """
        This function handles incoming events for the adaptive hedging strategy.

        Parameters:
        event (dict): The event data.

        Returns:
        None
        """
        print(f"Got event: {event}")
        content=event.content
        message = content["message"]
        if(message== "open_order"):
            username = content["user_name"]
            sent_by_admin=content["sent_by_admin"]
            user_id=content["user_id"]
            cycle_type = content['type']
            price = content['price']
            # wait_for_candle = content['wait_for_candle_to_close']
            # username= content['user_name']
            
            if(self.stop==False):
                if(cycle_type==0):
                    if(price==0):
                        order1=self.meta_trader.buy(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                        self.create_cycle(
                            order1, None, False, sent_by_admin, user_id, username, "BUY")
                    elif(price>0):
                        ask=    self.meta_trader.get_ask(self.symbol)
                        if(price>ask):
                            #buy stop
                            order1= self.meta_trader.buy_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"pending")
                            self.create_cycle(order1, None, True, sent_by_admin, user_id, username,"BUY")
                        else:
                            order1=self.meta_trader.buy_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"pending")        
                            self.create_cycle(order1, None, True, sent_by_admin, user_id, username,"BUY")
                elif cycle_type==1:
                    if(price==0):
                        order1=self.meta_trader.sell(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                        self.create_cycle(
                            order1, None, False, sent_by_admin, user_id, username, "SELL")
                    elif(price>0):
                        bid=    self.meta_trader.get_bid(self.symbol)
                        if(price<bid):
                            #sell stop
                            order1= self.meta_trader.sell_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"pending")
                            self.create_cycle(
                                order1, None, True, sent_by_admin, user_id, username, "SELL")
                        else:
                            order1=self.meta_trader.sell_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"pending")        
                            self.create_cycle(
                                order1, None, True, sent_by_admin, user_id, username, "SELL")
                elif cycle_type==2:
                    if(price==0):
                        order1=self.meta_trader.buy(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                        order2=self.meta_trader.sell(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                        self.create_cycle(order1,order2,False,sent_by_admin,user_id,username,"BUY&SELL")
                    elif(price>0):
                        ask=    self.meta_trader.get_ask(self.symbol)
                        bid=    self.meta_trader.get_bid(self.symbol)
                        if(price>ask):
                            #buy stop
                            order1= self.meta_trader.buy_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"pending")
                            # order2= self.meta_trader.sell_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0, 0,"PIPS",self.slippage,"pending")
                            self.create_cycle(order1,None,True,sent_by_admin,user_id,username,"BUY&SELL")
                        elif price<bid:
                            order1= self.meta_trader.buy_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"pending")        
                            # order2= self.meta_trader.sell_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"pending")        
                            self.create_cycle(order1,None,True,sent_by_admin,user_id,username,"BUY&SELL")
            # close cycle
        elif message=="close_cycle":
            username = content["user_name"]
            sent_by_admin=content["sent_by_admin"]
            user_id=content["user_id"]
            cycle_id = content['id']
            cycle_data= self.local_api.get_cycle_by_remote_id(cycle_id)
            seleced_cycle= cycle(cycle_data,self.meta_trader,self.meta_trader,"db")
            seleced_cycle.close_cycle(sent_by_admin,user_id,username)
            self.client.update_CT_cycle_by_id(seleced_cycle.cycle_id,seleced_cycle.to_remote_dict())
        elif message=="update_order_configs":
            order_ticket=content["ticket"]
            sl=content['updated']['sl']
            tp=content['updated']['tp']
            ts=content['updated']['trailing_steps']
            order_data=self.local_api.get_order_by_ticket(order_ticket)
            order_obj = order(order_data,order_data.is_pending,self.meta_trader,self.local_api,"db")
            order_obj.update_order_configs(sl,tp,ts)
            order_obj.update_order()
        elif message=="close_order":
            order_ticket=content["ticket"]
            order_data=self.local_api.get_order_by_ticket(order_ticket)
            order_obj = order(order_data,order_data.is_pending,self.meta_trader,self.local_api,"db")
            order_obj.close_order()
        elif message=="close_all_cycles":
            active_cycles = self.get_all_active_cycles()
            for cycle_data in active_cycles:
                cycle_obj = cycle(cycle_data, self.meta_trader, self,"db")
                cycle_obj.close_cycle(content["sent_by_admin"],content["user_id"],content["user_name"])
                self.client.update_CT_cycle_by_id(cycle_obj.cycle_id,cycle_obj.to_remote_dict())
        elif message=="stop_bot":
            self.stop=True
            self.client.set_bot_stopped(event.bot)
        elif message=="start_bot":
            self.stop=False
            self.client.set_bot_running(event.bot)
        elif message=="close_all_pending_orders":
            orders=self.local_api.get_open_pending_orders()
            for order_data in orders:
                order_obj = order(order_data,order_data.is_pending,self.meta_trader,self.local_api,"db")
                order_obj.close_order()
        elif message=="close_pending_order":
            order_ticket=content["ticket"]
            order_data=self.local_api.get_order_by_ticket(order_ticket)
            order_obj = order(order_data,order_data.is_pending,self.meta_trader,self.local_api,"db")
            order_obj.close_order()
            
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

    def create_cycle(self, order1, order2, is_pending, sent_by_admin, user_id, username, cycle_type):
        """
        This function creates a cycle.

        Parameters:
        data (dict): The cycle data.

        Returns:
        None
        """
        lower_bound = float(order1[0].price_open) - float(self.zones[0]) * float(self.meta_trader.get_pips(self.symbol))
        upper_bound = float(order1[0].price_open) + float(self.zones[0]) * float(self.meta_trader.get_pips(self.symbol))
        upper_threshold = float(upper_bound) +  float(self.autotrade_threshold  * float(self.meta_trader.get_pips(self.symbol)))
        lower_threshold = float(lower_bound) -  float(self.autotrade_threshold  * float(self.meta_trader.get_pips(self.symbol)))
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
            "cycle_id" :"",
            "zone_index"   : 0,
             "threshold_upper": upper_threshold,
            "threshold_lower": lower_threshold,
            
            
            
        }
        New_cycle = cycle(data,self.meta_trader,self.bot)
         
        if order1:
            order_obj = order( order1[0], is_pending,self.meta_trader,self.local_api,"mt5","")
            order_obj.create_order()
            if is_pending:
                New_cycle.add_pending_order(order1[0].ticket)
            else:
                New_cycle.add_initial_order(order1[0].ticket)
        if order2 and order2 != -2:
            order_obj = order( order2[0], is_pending,self.meta_trader,self.local_api,"mt5","")
            order_obj.create_order()
            if is_pending:
                New_cycle.add_pending_order(order2[0].ticket)
            else:
                New_cycle.add_initial_order(order2[0].ticket)
        res=self.client.create_CT_cycle(New_cycle.to_remote_dict())
        New_cycle.cycle_id =  str( res.id)
        New_cycle.create_cycle()
       
    # get all active  cycles
    def get_all_active_cycles(self):
        cycles = self.local_api.get_active_cycles(self.bot.account.id)
        active_cycles = [cycle for cycle in cycles if cycle.is_closed is False]
        return active_cycles
    # open new cycle automatically every threshold pips from the last cycle with limit max cycles 
    def open_new_cycle(self,active_cycles):
        if len(active_cycles)<self.max_cycles:
            ask =self.meta_trader.get_ask(self.symbol)
            bid =self.meta_trader.get_bid(self.symbol)
            pips = self.meta_trader.get_pips(self.symbol)
            up_price=self.last_cycle_price+self.autotrade_threshold*pips
            down_price=self.last_cycle_price-self.autotrade_threshold*pips
            if ask>=up_price or bid<=down_price:
                if self.stop is False:
                    order1=self.meta_trader.buy(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                    order2=self.meta_trader.sell(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                    self.create_cycle(order1, order2, False,
                                      False, 0, "MetaTrader5", "BUY&SELL")
                    self.last_cycle_price=ask if ask>=up_price else bid if bid<=down_price else 0
    def  run(self):
        """
        This function runs the adaptive hedging strategy.

        Parameters:
        None

        Returns:
        None
        """
        while True:
            active_cycles = self.get_all_active_cycles()
            if self.autotrade is True:
                self.open_new_cycle(active_cycles)
            for cycle_data in active_cycles:
                cycle_obj = cycle(cycle_data, self.meta_trader, self,"db")
                if self.stop is False:
                    cycle_obj.manage_cycle_orders(self.autotrade_threshold)
                cycle_obj.update_cycle(self.client)
                cycle_obj.close_cycle_on_takeprofit(self.take_profit,self.client)
                
                

    def run_in_thread(self):
        """
        This function runs the adaptive hedging strategy in a separate thread.
        """
        thread = threading.Thread(target=self.run,daemon=True)
        thread.start()
        
       
        