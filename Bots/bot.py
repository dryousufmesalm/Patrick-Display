import threading
import time
import logging
from Strategy.AdaptiveHedging import AdaptiveHedging
from Strategy.CycleTrader import CycleTrader
from Strategy.StockTrader import StockTrader
import asyncio


class Bot:
    def __init__(self, client, account, meta_trader, bot_id):
        self.id = bot_id
        self.account = None
        self.strategy_name = None
        self.symbol = None
        self.symbol_name = None
        self.magic = None
        self.configs = None
        self.client = client
        self.account = account
        self.meta_trader = meta_trader
        self.strategy = None
        self.settings = None

    def initialize(self):
        """ Initialize the bot """
        # get bot from the API
        try:
            bot_started = self.get_bot_settings()
            if bot_started is None:
                print(f"Failed to initialize bot {bot_started.name}")
                return False
            if bot_started:
                # Initialize the strategy
                self.init_strategy()
                self.update_configs()

            return True
        except (ConnectionError, TimeoutError) as e:
            print(f"Failed to initialize bot due to network issue: {e}")
            return False
        except ValueError as e:
            print(f"Failed to initialize bot due to value error: {e}")
            return False
        except KeyError as e:
            print(f"Failed to initialize bot due to missing key: {e}")
            return False
        except Exception as e:
            print(f"Failed to initialize bot: {e}")
            return False

    def init_strategy(self):
        """ Initialize the strategy """
        try:
            if self.strategy_name == "Tony AH Recovery":
                self.strategy = AdaptiveHedging(
                    self.meta_trader, self.configs, self.client, self.symbol_name, self)
                self.strategy.initialize(self.configs, self.settings)
            elif self.strategy_name == "Cycles Trader":
                self.strategy = CycleTrader(
                    self.meta_trader, self.configs, self.client, self.symbol_name, self)
                self.strategy.initialize(self.configs, self.settings)
            elif self.strategy_name == "Stock rader":
                self.strategy = StockTrader(
                    self.meta_trader, self.configs, self.client)
                self.strategy.initialize(self.configs, self.settings)
            else:
                print(f"Unknown strategy: {self.strategy_name}")
        except Exception as e:
            print(f"Failed to initialize strategy: {e}")

    def update_configs(self):
        """ Update the bot's settings """

        try:
            if self.strategy_name == "Tony AH Recovery":
                self.strategy.update_configs(self.configs, self.settings)
            elif self.strategy_name == "Cycles Trader":
                self.strategy.update_configs(self.configs, self.settings)
            elif self.strategy_name == "StockTrader":
                self.strategy.update_configs(self.configs, self.settings)
            else:
                print(f"Unknown strategy: {self.strategy_name}")
        except Exception as e:
            print(f"Failed to update configs: {e}")

    def get_bot_settings(self):
        """ Get the bot's settings """
        bot = self.client.get_account_bots_by_id(self.id)[0]
        if not bot:
            print(f"Bot {self.id} not found.")
            return False
        # Initialize the bot
        strategy = self.client.get_strategy_by_id(bot.strategy)[0]
        self.strategy_name = strategy.name
        self.magic = bot.magic_number
        self.configs = bot.bot_configs
        self.settings = bot.settings
        self.symbol_name = bot.bot_configs["symbol"]
        self.symbol = bot.symbol
        
        return bot

    async def handle_event(self, event):
        """ Handle the incoming event """
        if self.strategy:
            await self.route_to_strategy(event)
            logging.info("Got event: %s", event)
        else:
            logging.error("Strategy not initialized for bot %s", self.id)

    async def route_to_strategy(self, event):
        """ Route the event to the strategy """
        if self.strategy:
            logging.info("Route to strategy")
            await self.strategy.handle_event(event)
        else:
            logging.error("Strategy not initialized for bot %s", self.id)

    async def run(self):
        """ Run the bot """
        if self.strategy is not None:
            # Run the strategy
            await self.strategy.run_in_thread()
