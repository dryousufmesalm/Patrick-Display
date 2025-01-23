import threading
import time
from Bots.bot import Bot
from DB.db_engine import engine
from DB.ah_strategy.repositories.ah_repo import AHRepo
from DB.ct_strategy.repositories.ct_repo import CTRepo
class Account:
    """ The account class """
    def __init__(self,client,meta_trader):
        """_summary_

        Args:
            client (_type_): _description_
            meta_trader (_type_): _description_
        """
        self.id = None
        self.name = None
        self.meta_trader_id = None
        self.status = None
        self.expire_date = None
        self.balance = None
        self.equity = None
        self.margin = None
        self.total_pnl = None
        self.config = None
        self.symbols = None
        self.client = client
        self.meta_trader = meta_trader
        self.mt5_accounts_info=None
        self.bots=[]
        self.stop=False
        self.ah_repo= AHRepo(engine=engine)
        self.ct_repo= CTRepo(engine=engine)
    
    def on_init(self):
        """ Initialize the account """
        validated=self.validate()
        if validated:
            self.init_bots()
            self.update_symbols()
            
    def    validate(self):
        """ Validate the account """
        self.mt5_accounts_info=self.meta_trader.get_account_info()
        self.meta_trader_id = self.mt5_accounts_info["login"]
        accounts= self.client.get_accounts_by_metatrader_id(self.meta_trader_id)
        for acc in accounts:
            if acc.meta_trader_id==str(self.meta_trader_id):
                self.id = acc.id
                self.name = acc.name
                self.meta_trader_id = acc.meta_trader_id
                self.status = acc.status
                self.expire_date = acc.expire_date
                self.balance = acc.balance
                self.equity = acc.equity
                self.margin = acc.margin
                self.total_pnl = acc.total_pnl
                self.config = acc.config
                print(f"Account {self.name} validated!")
                
                return True
    
    def update_account(self):
        ''' Update the account '''
        while True:
            """ Update the account """
            self.mt5_accounts_info=self.meta_trader.get_account_info()
            # check if the data is changed before updating
            if self.balance == self.mt5_accounts_info["balance"] and self.equity == self.mt5_accounts_info["equity"] and self.margin == self.mt5_accounts_info["margin"] and self.total_pnl == self.mt5_accounts_info["profit"]:
                continue
            #free margin
            # self.mt5_accounts_info["free_margin"] = self.mt5_accounts_info["equity"] - self.mt5_accounts_info["margin"]
            # Update the account balance,equity ,margin and total_pnl
            self.balance = self.mt5_accounts_info["balance"]
            self.equity = self.mt5_accounts_info["equity"]
            self.margin = self.mt5_accounts_info["margin_free"]
            self.total_pnl = self.mt5_accounts_info["profit"]
            
            # Update the account
            data = {
                "balance": round(self.balance, 2),
                "equity": round(self.equity,2),
                "margin": round(self.margin,2),
                "total_pnl": round(self.total_pnl,2)
            }
            #  run the update in the background thread
            try:
                account_id = self.id
                self.client.update_account(account_id, data)    
            except Exception as e:
                print(f"Failed to update account: {e}")   
        
            time.sleep(1)
        
    def run_in_thread(self):
        """ Run the account in a background thread """
        # Create a thread to run the account
        Updater_thread = threading.Thread(target=self.update_account, daemon=True)
        # Start the thread
        Updater_thread.start()
        
        """Run the subscription in a separate thread."""
        evens_thread = threading.Thread(target=self.subscribe, daemon=True)
        evens_thread.start()
        print("Subscription thread started!")
        
        refresh_token= threading.Timer(3600, self.Refresh_token)
        refresh_token.start()
    def Refresh_token(self):
        """ Refresh the token for the account """
        try:
            self.client.refresh_token()
            print(f"Token refreshed for account {self.name}!")
        except (ConnectionError, TimeoutError) as e:
            print(f"Failed to refresh token due to connection issue: {e}")
        except KeyError as e:
            print(f"Failed to refresh token due to missing key: {e}")
        except ValueError as e:
            print(f"Failed to refresh token due to value error: {e}")
        except Exception as e:
            print(f"Failed to refresh token due to an unexpected error: {e}")
        
    def init_bots(self):
        """ Initialize the bots for the account """
        try:
            bots = self.client.get_account_bots(self.id)
            for bot in bots:
                bot = Bot(self.client, self, self.meta_trader, bot.id)
                bot.initialize()
                bot.run()  # Run the bot in a background thread
                self.bots.append(bot)
            return True
        except (ConnectionError, TimeoutError) as e:
            print(f"Failed to initialize bots due to connection issue: {e}")
        except KeyError as e:
            print(f"Failed to initialize bots due to missing key: {e}")
        except ValueError as e:
            print(f"Failed to initialize bots due to value error: {e}")
        except Exception as e:
            print(f"Failed to initialize bots due to an unexpected error: {e}")
            return False
    def route_event_to_bot(self, event,bot_id):
        """ Route the event to the specified bot """
        for bot in self.bots:           
            if bot.id == bot_id:
                try:
                    bot.handle_event(event)
                except Exception as e:
                    print(f"Failed to route event to bot: {e}")
                
    def handle_events(self, event):
        """ Handle the incoming event """
        account = event.account
        bot_id = event.bot
        #  skip if account is not the current account
        if account != self.id:
            return
        # only route action create
        content=event.content
        message = content["message"]
        if message=="create_bot":
            bot = Bot(self.client, self, self.meta_trader, content["id"])
            if bot.initialize():
            # run the bot in the background thread
                bot.run()
                self.bots.append(bot)
                # delete the event
                self.client.delete_event(event.id)
        elif message=="update_bot":                              
            # update bot configurations
            bot_id = content["id"]
            for bot in self.bots:
                if bot.id == bot_id:
                    bot.get_bot_settings()
                    bot.update_configs()
                    # delete the event
                    self.client.delete_event(event.id)
                    
                    break
        elif message=="delete_bot":
            bot_id = content["id"]
            for bot in self.bots:
                if bot.id == bot_id:
                    self.bots.remove(bot)
                    self.client.delete_event(event.id)
                    break
        else:
            try : 
                print(message)
                self.route_event_to_bot(event,bot_id)
                self.client.delete_event(event.id)
            except Exception as e:
                print(f"Failed to route event to bot: {e}")
                    
        # route the event to the specified bot
       
        
    def subscribe(self):
        """ Subscribe to the events """
        while True:
            try:
                # check  if the event is already subscribed
              events=  self.client.get_all_events()
              if len(events) >0:
                    for event in events:
                        if event.account== self.id:
                            self.handle_events(event)
            except (ConnectionError, TimeoutError) as e:
                print(f"Failed to subscribe to events due to connection issue: {e}")
            except RuntimeError as e:
                print(f"Failed to subscribe to events due to runtime error: {e}")
            except Exception as e:
                print(f"Failed to subscribe to events due to an unexpected error: {e}")
            time.sleep(1)
    def update_symbols(self):
        """ Update the symbols """
        # get symbols from Trading platform 
        symbols = self.meta_trader.get_symbols_from_watch()
        # only add symbols names
        symbols = [symbol.name for symbol in symbols] 
        data = {
            "symbols": {"symbols": symbols},
        }
        # update the database
        self.client.update_account_symbols(self.id, data)
    def  run_bots(self):
        """ Run the bots """
        for bot in self.bots:
            bot.run()