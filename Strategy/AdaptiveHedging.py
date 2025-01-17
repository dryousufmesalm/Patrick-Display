from Strategy.strategy import Strategy
from Orders.order import order
from cycles.AH_cycle import cycle
import threading
class AdaptiveHedging(Strategy):
    def __init__(self, meta_trader, config, client,symbol,bot,local_api):
        self.meta_trader = meta_trader
        self.config = config
        self.client = client
        self.positions = {}
        self.orders = {}
        self.symbol = symbol
        self.bot = bot
        self.disable_new_cycle_recovery = False
        self.enable_recovery = False
        self.lot_sizes = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
        self.margin = 10.8
        self.max_recovery = 2
        self.max_recovery_direction = "opposite"
        self.pips_step = 0
        self.slippage = 3
        self.sltp = "money"
        self.take_profit = 5
        self.zones = 500
        self.zone_forward = 1
        self.stop=False
        self.local_api=local_api
        self.settings=None
        self.init_settings()
 
    def init_settings(self):
        """
        This function initializes the settings for the adaptive hedging strategy."""
        self.disable_new_cycle_recovery = self.config["disable_new_cycle_recovery"]
        self.enable_recovery = self.config["enable_recovery"]
        self.lot_sizes = self.string_to_array( self.config["lot_sizes"])
        self.margin = self.config["margin"]
        self.max_recovery = self.config["max_recovery"]
        self.max_recovery_direction = self.config["max_recovery_direction"]
        self.pips_step = self.config["pips_step"]
        self.slippage = self.config["slippage"]
        self.sltp = self.config["sltp"]
        self.take_profit = self.config["take_profit"]
        self.zones = self.string_to_array(self.config['zone_array'])
        self.zone_forward = self.config["zone_forward"]
        self.symbol = self.config['symbol']
        
        if self.settings and hasattr(self.settings, 'stopped'):
            self.stop = self.settings.stopped
        else:
            self.stop = False
    
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
            wait_for_candle_to_close=content["wait_for_candle_to_close"]
            cycle_type = content['type']
            price = content['price']
            # wait_for_candle = content['wait_for_candle_to_close']
            # username= content['user_name']
            
            if(self.stop==False):
                if(cycle_type==0):
                    if(price==0):
                        order1=self.meta_trader.buy(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                        self.create_cycle(order1,None,False,sent_by_admin,user_id,username)
                    elif(price>0):
                        ask=    self.meta_trader.get_ask(self.symbol)
                        if(price>ask):
                            #buy stop
                            order1= self.meta_trader.buy_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                            self.create_cycle(order1,None,True,sent_by_admin,user_id,username)
                        else:
                            order1=self.meta_trader.buy_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")        
                            self.create_cycle(order1,None,True,sent_by_admin,user_id,username)
                elif cycle_type==1:
                    if(price==0):
                        order1=self.meta_trader.sell(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                        self.create_cycle(order1,None,False,sent_by_admin,user_id,username)
                    elif(price>0):
                        bid=    self.meta_trader.get_bid(self.symbol)
                        if(price<bid):
                            #sell stop
                            order1= self.meta_trader.sell_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                            self.create_cycle(order1,None,True,sent_by_admin,user_id,username)
                        else:
                            order1=self.meta_trader.sell_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")        
                            self.create_cycle(order1,None,True,sent_by_admin,user_id,username)
                elif cycle_type==2:
                    if(price==0):
                        order1=self.meta_trader.buy(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                        order2=self.meta_trader.sell(self.symbol,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                        self.create_cycle(order1,order2,False,sent_by_admin,user_id,username)
                    elif(price>0):
                        ask=    self.meta_trader.get_ask(self.symbol)
                        bid=    self.meta_trader.get_bid(self.symbol)
                        if(price>ask):
                            #buy stop
                            order1= self.meta_trader.buy_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                            order2= self.meta_trader.sell_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")
                            self.create_cycle(order1,order2,True,sent_by_admin,user_id,username)
                        elif price<bid:
                            order1= self.meta_trader.buy_limit(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")        
                            order2= self.meta_trader.sell_stop(self.symbol,price,self.lot_sizes[0],self.bot.magic,0,0,"PIPS",self.slippage,"initial")        
                            self.create_cycle(order1,order2,True,sent_by_admin,user_id,username)
            # close cycle
        elif message=="close_cycle":
            username = content["user_name"]
            sent_by_admin=content["sent_by_admin"]
            user_id=content["user_id"]
            cycle_id = content['id']
            cycle_data= self.local_api.get_AH_cycle_by_cycle_id(cycle_id)
            seleced_cycle= cycle(cycle_data[0],self.local_api,self.meta_trader,self.meta_trader,"db")
            seleced_cycle.close_cycle(sent_by_admin,user_id,username)
            self.client.update_AH_cycle_by_id(seleced_cycle.cycle_id,seleced_cycle.to_remote_dict())
        elif message=="update_order_configs":
            order_ticket=content["ticket"]
            sl=content['updated']['sl']
            tp=content['updated']['tp']
            ts=content['updated']['trailing_steps']
            order_data=self.local_api.get_order_by_ticket(order_ticket)
            order_obj = order(order_data[0],order_data[0].is_pending,self.meta_trader,self.local_api,"db")
            order_obj.update_order_configs(sl,tp,ts)
            order_obj.update_order()
        elif message=="close_order":
            order_ticket=content["ticket"]
            order_data=self.local_api.get_order_by_ticket(order_ticket)
            order_obj = order(order_data[0],order_data[0].is_pending,self.meta_trader,self.local_api,"db")
            order_obj.close_order()
        elif message=="close_all_cycles":
            active_cycles = self.get_all_active_cycles()
            for cycle_data in active_cycles:
                cycle_obj = cycle(cycle_data, self.local_api, self.meta_trader, self,"db")
                cycle_obj.close_cycle(content["sent_by_admin"],content["user_id"],content["user_name"])
                self.client.update_AH_cycle_by_id(cycle_obj.cycle_id,cycle_obj.to_remote_dict())
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
            order_obj = order(order_data[0],order_data[0].is_pending,self.meta_trader,self.local_api,"db")
            order_obj.close_order()
    def initialize(self,config,settings):
        """
        This function initializes the adaptive hedging strategy.

        Parameters:
        None

        Returns:
        None
        """
        self.update_configs(config,settings)
            
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
    def create_cycle(self,order1,order2,is_pending,sent_by_admin,user_id,username):
        """
        This function creates a cycle.

        Parameters:
        data (dict): The cycle data.

        Returns:
        None
        """
        lower_bound = float(order1[0].price_open) - float(self.zones[0]) * float(self.meta_trader.get_pips(self.symbol))
        upper_bound = float(order1[0].price_open) + float(self.zones[0]) * float(self.meta_trader.get_pips(self.symbol))
       
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
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
            "is_pending": is_pending,
            "type": "initial",
            "total_volume": round(123, 2),
            "total_profit": round(123, 2),
            "initial": [],
            "hedge": [],
            "pending": [],
            "closed": [],
            "recovery": [],
            "max_recovery":[],
            "cycle_id" :"",
            "zone_index"   : 0,
            
            
        }
        New_cycle = cycle(data, self.local_api,self.meta_trader,self)
         
        if order1:
            order_obj = order( order1[0], is_pending,self.meta_trader,self.local_api,"mt5")
            order_obj.create_order()
            New_cycle.add_initial_order(order1[0].ticket)
        if order2:
            order_obj = order( order2[0], is_pending,self.meta_trader,self.local_api,"mt5")
            order_obj.create_order()
            New_cycle.add_initial_order(order2[0].ticket)
        res=self.client.create_AH_cycle(New_cycle.to_remote_dict())
        New_cycle.cycle_id =  str( res.id)
        New_cycle.create_cycle()
       
    # get all active  cycles
    def get_all_active_cycles(self):
        cycles = self.local_api.get_AH_active_cycles()
        if cycles is None:
            return []
        active_cycles = [cycle for cycle in cycles if cycles[0].is_closed is False]
        return active_cycles
    # Cycles  Manager 
    
    
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
            for cycle_data in active_cycles:
                cycle_obj = cycle(cycle_data, self.local_api, self.meta_trader, self,"db")
                if self.stop is False:
                    cycle_obj.manage_cycle_orders()
                cycle_obj.update_cycle(self.client)
                cycle_obj.close_cycle_on_takeprofit(self.take_profit,self.client)
                
                

    def run_in_thread(self):
        """
        This function runs the adaptive hedging strategy in a separate thread.
        """
        thread = threading.Thread(target=self.run,daemon=True)
        thread.start()
        
       
        
         