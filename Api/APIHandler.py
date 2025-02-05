from pocketbase import PocketBase
import threading
import logging


class API:
    """ The base class for all the API handlers"""

    def __init__(self, base_url, token=None):
        self.base_url = base_url
        self.token = token
        self.authenticated = False
        self.user_name = None
        self.user_email = None
        self.is_active = False
        self.user_id = None
        self.client = PocketBase(self.base_url)

    def login(self, username, password):
        """Authenticate with the API using the provided username and password."""
        try:
            user_data = self.client.collection(
                "users").auth_with_password(username, password)
            self.token = user_data.token
            self.user_id = user_data.record.id
            self.authenticated = user_data.is_valid
            self.user_name = user_data.record.username
            self.user_email = user_data.record.email
            self.is_active = user_data.record.active
            return user_data
        except Exception as e:
            logging.error(f"Failed to login: {e}")
            return None

    def Refresh_token(self):
        """Refresh the token."""
        try:
            user_data = self.client.collection("users").authRefresh()
            self.token = user_data.token
            self.authenticated = user_data.is_valid
            print(f"Token refreshed for account {self.user_name}!")
            print(f"is authenticated: {self.authenticated}")
            return user_data
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            return None

    def logout(self):
        """Log out the current user."""
        try:
            self.token = None
            self.authenticated = False
            self.user_name = None
            self.user_email = None
            self.is_active = False
            self.user_id = None
            return True
        except Exception as e:
            logging.error(f"Failed to logout: {e}")
            return False

    def get_accounts(self, userid):
        """Get all accounts for the current user."""
        try:
            accounts = self.client.collection("accounts").get_full_list(200, {
                "filter": f"user = '{userid}'"
            })
            return accounts
        except Exception as e:
            logging.error(f"Failed to get accounts: {e}")
            return []

    def get_accounts_by_id(self, account_id):
        """Get an account by its ID."""
        try:
            return self.client.collection("accounts").get_full_list(200, {
                "filter": f"user = '{self.user_id}' && id = '{account_id}'"
            })
        except Exception as e:
            logging.error(f"Failed to get account by ID: {e}")
            return None

    def get_accounts_by_metatrader_id(self, account_id):
        """Get an account by its MetaTrader ID."""
        try:
            return self.client.collection("accounts").get_full_list(200, {
                "filter": f"user = '{self.user_id}' && meta_trader_id = '{account_id}'"
            })
        except Exception as e:
            logging.error(f"Failed to get account by MetaTrader ID: {e}")
            return None

    def update_account(self, account_id, data):
        """Update an account."""
        try:
            return self.client.collection("accounts").update(account_id, data)
        except Exception as e:
            logging.error(f"Failed to update account: {e}")
            return None

    def update_account_symbols(self, account_id, data):
        """Update an account."""
        try:
            return self.client.collection("accounts").update(account_id, data)
        except Exception as e:
            logging.error(f"Failed to update account symbols: {e}")
            return None

    def get_account_bots(self, account_id):
        """Get all bots for the current user."""
        try:
            return self.client.collection("bots").get_full_list(200, {"filter": f"account = '{account_id}'"})
        except Exception as e:
            logging.error(f"Failed to get account bots: {e}")
            return []

    def get_account_bots_by_id(self, bot_id):
        """Get a bot by its ID."""
        try:
            return self.client.collection("bots").get_full_list(200, {"filter": f"id = '{bot_id}'"})
        except Exception as e:
            logging.error(f"Failed to get bot by ID: {e}")
            return None

    def get_bots_by_magic(self, magic):
        """Get a bot by its magic numbers."""
        try:
            return self.client.collection("bots").get_full_list(200, {"filter": f"magic = '{magic}'"})
        except Exception as e:
            logging.error(f"Failed to get bots by magic: {e}")
            return None

    def get_strategy_by_id(self, strategy_id):
        """Get a strategy by its ID."""
        try:
            return self.client.collection("strategies").get_full_list(200, {"filter": f"id = '{strategy_id}'"})
        except Exception as e:
            logging.error(f"Failed to get strategy by ID: {e}")
            return None

    def delete_event(self, event_id):
        """Delete an event from the event collection."""
        try:
            self.client.collection("events").delete(event_id)
        except Exception as e:
            logging.error(f"Failed to delete event: {e}")

    def subscribe_events(self, handle_events):
        """Subscribe to the event collection."""
        try:
            print("Subscribing to events...")
            self.client.collection("events").subscribe(handle_events)
        except Exception as e:
            logging.error(f"Failed to subscribe to events: {e}")

    def get_all_events(self):
        """Get all events."""
        try:
            return self.client.collection("events").get_full_list(200)
        except Exception as e:
            logging.error(f"An error occurred while fetching events: {e}")
            return None

    def get_symbol_by_id(self, symbol_id):
        """Get a symbol by its ID."""
        try:
            return self.client.collection("symbols").get_full_list(200, {"filter": f"id = '{symbol_id}'"})
        except Exception as e:
            logging.error(f"Failed to get symbol by ID: {e}")
            return None

    def get_symbol(self, account_id):
        """Get a symbol by its name."""
        try:
            return self.client.collection("symbols").get_full_list(200, {"filter": f"account = '{account_id}'"})
        except Exception as e:
            logging.error(f"Failed to get symbol: {e}")
            return None

    def create_symbol(self, data):
        """Create a symbol."""
        try:
            return self.client.collection("symbols").create(data)
        except Exception as e:
            logging.error(f"Failed to create symbol: {e}")
            return None

    def create_AH_cycle(self, data):
        """Create a cycle."""
        try:
            return self.client.collection("adaptive_hedge_cycles").create(data)
        except Exception as e:
            logging.error(f"Failed to create AH cycle: {e}")
            return None

    def delete_AH_cycle(self, data):
        """Delete a cycle."""
        try:
            return self.client.collection("adaptive_hedge_cycles").delete(data)
        except Exception as e:
            logging.error(f"Failed to delete AH cycle: {e}")
            return None

    def get_AH_cycle_by_id(self, cycle_id):
        """Get a cycle by its ID."""
        try:
            return self.client.collection("adaptive_hedge_cycles").get_full_list(200, {"filter": f"id = '{cycle_id}'"})
        except Exception as e:
            logging.error(f"Failed to get AH cycle by ID: {e}")
            return None

    def get_all_AH_active_cycles(self):
        """Get all active cycles."""
        try:
            return self.client.collection("adaptive_hedge_cycles").get_full_list(200, {"filter": "is_closed = False"})
        except Exception as e:
            logging.error(f"An error occurred while fetching AH cycles: {e}")
            return []

    def get_all_AH_active_cycles_by_account(self, account_id):
        """Get all active cycles by account."""
        try:
            return self.client.collection("adaptive_hedge_cycles").get_full_list(200, {"filter": f"account = '{account_id}' && is_closed = False"})
        except Exception as e:
            logging.error(
                f"An error occurred while fetching AH cycles by account: {e}")
            return []

    def update_AH_cycle_by_id(self, cycle_id, data):
        """Update a cycle by its ID."""
        try:
            return self.client.collection("adaptive_hedge_cycles").update(cycle_id, data)
        except Exception as e:
            logging.error(f"Failed to update AH cycle by ID: {e}")
            return None

    def close_AH_cycle(self, cycle_id):
        """Close a cycle by its ID."""
        try:
            data = {"is_closed": True}
            return self.client.collection("adaptive_hedge_cycles").update(cycle_id, data)
        except Exception as e:
            logging.error(f"Failed to close AH cycle: {e}")
            return None

    def create_CT_cycle(self, data):
        """Create a cycle."""
        try:
            return self.client.collection("cycles_trader_cycles").create(data)
        except Exception as e:
            logging.error(f"Failed to create CT cycle: {e}")
            return None

    def delete_CT_cycle(self, data):
        """Delete a cycle."""
        try:
            return self.client.collection("cycles_trader_cycles").delete(data)
        except Exception as e:
            logging.error(f"Failed to delete CT cycle: {e}")
            return None

    def get_CT_cycle_by_id(self, cycle_id):
        """Get a cycle by its ID."""
        try:
            return self.client.collection("cycles_trader_cycles").get_full_list(200, {"filter": f"id = '{cycle_id}'"})
        except Exception as e:
            logging.error(f"Failed to get CT cycle by ID: {e}")
            return None

    def get_all_CT_active_cycles(self):
        """Get all active cycles."""
        try:
            return self.client.collection("cycles_trader_cycles").get_full_list(200, {"filter": "is_closed = false"})
        except Exception as e:
            logging.error(f"An error occurred while fetching CT cycles: {e}")
            return []

    def get_all_CT_active_cycles_by_account(self, account_id):
        """Get all active cycles by account."""
        try:
            return self.client.collection("cycles_trader_cycles").get_full_list(200, {"filter": f"account = '{account_id}' && is_closed = False"})
        except Exception as e:
            logging.error(
                f"An error occurred while fetching CT cycles by account: {e}")
            return []

    def update_CT_cycle_by_id(self, cycle_id, data):
        """Update a cycle by its ID."""
        try:
            return self.client.collection("cycles_trader_cycles").update(cycle_id, data)
        except Exception as e:
            logging.error(f"Failed to update CT cycle by ID: {e}")
            return None

    def close_CT_cycle(self, cycle_id):
        """Close a cycle by its ID."""
        try:
            data = {"is_closed": True}
            return self.client.collection("cycles_trader_cycles").update(cycle_id, data)
        except Exception as e:
            logging.error(f"Failed to close CT cycle: {e}")
            return None

    def set_bot_stopped(self, bot_id):
        """Set a bot as stopped."""
        try:
            data = {"settings": {"stopped": True}}
            return self.client.collection("bots").update(bot_id, data)
        except Exception as e:
            logging.error(f"Failed to set bot as stopped: {e}")
            return None

    def set_bot_running(self, bot_id):
        """Set a bot as running."""
        try:
            data = {"settings": {"stopped": False}}
            return self.client.collection("bots").update(bot_id, data)
        except Exception as e:
            logging.error(f"Failed to set bot as running: {e}")
            return None
