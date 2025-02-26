import threading
import time
from Bots.bot import Bot
from DB.db_engine import engine
from DB.ah_strategy.repositories.ah_repo import AHRepo
from DB.ct_strategy.repositories.ct_repo import CTRepo
import asyncio
from Views.globals.app_logger import app_logger as logger


class Account:
    """ The account class """

    def __init__(self, client, meta_trader):
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
        self.mt5_accounts_info = None
        self.bots = []
        self.stop = False
        self.symbol_price = None
        self.ah_repo = AHRepo(engine=engine)
        self.ct_repo = CTRepo(engine=engine)

    async def on_init(self):
        """ Initialize the account """
        validated = self.validate()
        if validated:
            await self.init_bots()
            await self.update_symbols()

    def validate(self):
        """ Validate the account """
        self.mt5_accounts_info = self.meta_trader.get_account_info()
        self.meta_trader_id = self.mt5_accounts_info["login"]
        accounts = self.client.get_accounts_by_metatrader_id(
            self.meta_trader_id)
        for acc in accounts:
            if acc.meta_trader_id == str(self.meta_trader_id):
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
                logger.info(f"Account {self.name} validated!")
                return True
        return False

    async def update_account(self):
        ''' Update the account '''
        while True:
            try:
                self.mt5_accounts_info = self.meta_trader.get_account_info()
                if self.balance == self.mt5_accounts_info["balance"] and self.equity == self.mt5_accounts_info["equity"] and self.margin == self.mt5_accounts_info["margin"] and self.total_pnl == self.mt5_accounts_info["profit"]:
                    await asyncio.sleep(1)
                    continue

                self.balance = self.mt5_accounts_info["balance"]
                self.equity = self.mt5_accounts_info["equity"]
                self.margin = self.mt5_accounts_info["margin_free"]
                self.total_pnl = self.mt5_accounts_info["profit"]

                data = {
                    "balance": round(self.balance, 2),
                    "equity": round(self.equity, 2),
                    "margin": round(self.margin, 2),
                    "total_pnl": round(self.total_pnl, 2)
                }
                account_id = self.id
                self.client.update_account(account_id, data)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error in update_account: {e}")
                await asyncio.sleep(1)

    async def run_in_background(self):
        """ Run the account in the background """
        try:
            tasks = [
                asyncio.create_task(self.update_account()),
                asyncio.create_task(self.subscribe()),
                asyncio.create_task(self.refresh_token()),
                asyncio.create_task(self.update_symbols_price()),
            ]
            await asyncio.gather(*tasks)
            logger.info("Background tasks started!")
        except Exception as e:
            logger.error(f"Error running background tasks: {e}")

    async def refresh_token(self):
        """ Refresh the token for the account """
        while True:
            try:
                self.client.Refresh_token()
                logger.info(f"Token refreshed for account {self.name}!")
            except (ConnectionError, TimeoutError) as e:
                logger.error(
                    f"Failed to refresh token due to connection issue: {e}")
            except KeyError as e:
                logger.error(
                    f"Failed to refresh token due to missing key: {e}")
            except ValueError as e:
                logger.error(
                    f"Failed to refresh token due to value error: {e}")
            except Exception as e:
                logger.error(
                    f"Failed to refresh token due to an unexpected error: {e}")
            await asyncio.sleep(604800)

    async def init_bots(self):
        """ Initialize the bots for the account """
        try:
            bots = self.client.get_account_bots(self.id)
            for bot in bots:
                bot = Bot(self.client, self, self.meta_trader, bot.id)
                bot.initialize()
                await bot.run()  # Run the bot in a background thread
                self.bots.append(bot)
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                f"Failed to initialize bots due to connection issue: {e}")
        except KeyError as e:
            logger.error(f"Failed to initialize bots due to missing key: {e}")
        except ValueError as e:
            logger.error(f"Failed to initialize bots due to value error: {e}")
        except Exception as e:
            logger.error(
                f"Failed to initialize bots due to an unexpected error: {e}")
            return False

    async def route_event_to_bot(self, event, bot_id):
        """ Route the event to the specified bot """
        for bot in self.bots:
            if bot.id == bot_id:
                try:
                    await bot.handle_event(event)
                except Exception as e:
                    logger.error(f"Failed to route event to bot: {e}")

    async def handle_events(self, event):
        """ Handle the incoming event """
        account = event.account
        bot_id = event.bot
        if account != self.id:
            return
        content = event.content
        message = content["message"]
        try:
            if message == "create_bot":
                bot = Bot(self.client, self, self.meta_trader, content["id"])
                if bot.initialize():
                    await bot.run()
                    self.bots.append(bot)
                    self.client.delete_event(event.id)
            elif message == "update_bot":
                bot_id = content["id"]
                for bot in self.bots:
                    if bot.id == bot_id:
                        bot.get_bot_settings()
                        bot.update_configs()
                        self.client.delete_event(event.id)
                        break
            elif message == "delete_bot":
                bot_id = content["id"]
                for bot in self.bots:
                    if bot.id == bot_id:
                        self.bots.remove(bot)
                        self.client.delete_event(event.id)
                        break
            else:
                logger.info(message)
                await self.route_event_to_bot(event, bot_id)
                try:
                    self.client.delete_event(event.id)
                except Exception as e:
                    logger.error(f"Failed to delete event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle event: {e}")

    async def subscribe(self):
        """ Subscribe to the events """
        while True:
            try:
                events = self.client.get_all_events()
                if len(events) > 0:
                    tasks = []
                    for event in events:
                        if event.account == self.id:
                            tasks.append(asyncio.create_task(
                                self.handle_events(event)))
                    if len(tasks) > 0:
                        await asyncio.gather(*tasks)
            except (ConnectionError, TimeoutError) as e:
                logger.error(
                    f"Failed to subscribe to events due to connection issue: {e}")
            except RuntimeError as e:
                logger.error(
                    f"Failed to subscribe to events due to runtime error: {e}")
            except Exception as e:
                logger.error(
                    f"Failed to subscribe to events due to an unexpected error: {e}")
            await asyncio.sleep(1)

    async def update_symbols(self):
        """ Update the symbols """
        symbols = self.meta_trader.get_symbols_from_watch()
        symbols = [symbol.name for symbol in symbols]
        data = {
            "symbols": {"symbols": symbols},
        }
        self.client.update_account_symbols(self.id, data)
        database_symbols = self.client.get_symbols_by_account(self.id)

        # create a symbols
        async def update_symbols_task():
            database_symbol_names = [
                db_symbol.name for db_symbol in database_symbols]
            for symbol in symbols:
                if symbol not in database_symbol_names:
                    symbol_data = {
                        "name": symbol,
                        "price": self.meta_trader.get_bid(symbol),
                        "account": self.id,
                    }
                    self.client.create_symbol(symbol_data)

        asyncio.create_task(update_symbols_task())

    def run_bots(self):
        """ Run the bots """
        for bot in self.bots:
            bot.run()

    async def update_symbols_price(self):
        while True:
            try:
                for bot in self.bots:
                    """ Update the symbol price """
                    symbol_data = {
                        "price": self.meta_trader.get_bid(bot.symbol_name),
                    }
                    self.client.update_symbol(bot.symbol, symbol_data)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to update symbol price: {e}")
                await asyncio.sleep(1)
