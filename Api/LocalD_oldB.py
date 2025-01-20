from tinydb import TinyDB, Query

from pocketbase import PocketBase
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
            user_data = self.client.collection("_superusers").auth_with_password(username, password)
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
            user_data = self.client.collection("_superusers").authRefresh()
            self.token = user_data.token
            self.authenticated = user_data.is_valid
            return user_data
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            return None
    def login_as_admin(self, username, password):
        """Authenticate with the API using the provided username and password."""
        try:
            user_data = self.client.collection("_superusers").auth_with_password(username, password)
            self.token = user_data.token
            self.user_id = user_data.record.id
            self.authenticated = user_data.is_valid
            return user_data
        except Exception as e:
            logging.error(f"Failed to login as admin: {e}")
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

    def get_AH_active_cycles(self):
        """Get all active cycles."""
        try:
            return self.client.collection("adaptive_hedge_cycles").get_full_list(200, {"filter": "is_closed = false"})
        except Exception as e:
            logging.error(f"Failed to get AH active cycles: {e}")
            return None

    def update_AH_cycle_by_id(self, cycle_id, data):
        """Update a cycle by its ID."""
        try:
            return self.client.collection("adaptive_hedge_cycles").update(cycle_id, data)
        except Exception as e:
            logging.error(f"Failed to update AH cycle by ID: {e}")
            return None

    def get_AH_cycle_by_cycle_id(self, cycle_id):
        """Get a cycle by its cycle ID."""
        try:
            return self.client.collection("adaptive_hedge_cycles").get_full_list(200, {"filter": f"cycle_id = '{cycle_id}'"})
        except Exception as e:
            logging.error(f"Failed to get AH cycle by cycle ID: {e}")
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

    def get_CT_active_cycles(self):
        """Get all active cycles."""
        try:
            return self.client.collection("cycles_trader_cycles").get_full_list(200, {"filter": "is_closed = false"})
        except Exception as e:
            logging.error(f"Failed to get CT active cycles: {e}")
            return None

    def update_CT_cycle_by_id(self, cycle_id, data):
        """Update a cycle by its ID."""
        try:
            return self.client.collection("cycles_trader_cycles").update(cycle_id, data)
        except Exception as e:
            logging.error(f"Failed to update CT cycle by ID: {e}")
            return None

    def get_CT_cycle_by_cycle_id(self, cycle_id):
        """Get a cycle by its cycle ID."""
        try:
            return self.client.collection("cycles_trader_cycles").get_full_list(200, {"filter": f"cycle_id = '{cycle_id}'"})
        except Exception as e:
            logging.error(f"Failed to get CT cycle by cycle ID: {e}")
            return None

    def close_CT_cycle(self, cycle_id):
        """Close a cycle by its ID."""
        try:
            data = {"is_closed": True}
            return self.client.collection("cycles_trader_cycles").update(cycle_id, data)
        except Exception as e:
            logging.error(f"Failed to close CT cycle: {e}")
            return None

    def create_order(self, data):
        """Create an order."""
        logging.info(f"Creating order with data: {data}")

        # Ensure all required fields are present
        required_fields = ["ticket"]
        for field in required_fields:
            if field not in data:
                logging.error(f"Missing required field: {field}")
                raise ValueError(f"Missing required field: {field}")

        try:
            return self.client.collection("Orders").create(data)
        except Exception as e:
            logging.error(f"Failed to create order: {e}")
            return None

    def delete_order(self, data):
        """Delete an order."""
        try:
            return self.client.collection("Orders").delete(data)
        except Exception as e:
            logging.error(f"Failed to delete order: {e}")
            return None

    def get_order_by_id(self, order_id):
        """Get an order by its ID."""
        try:
            return self.client.collection("Orders").get_full_list(200, {"filter": f"id = '{order_id}'"})
        except Exception as e:
            logging.error(f"Failed to get order by ID: {e}")
            return None

    def update_order_by_id(self, order_id, data):
        """Update an order by its ID."""
        try:
            return self.client.collection("Orders").update(order_id, data)
        except Exception as e:
            logging.error(f"Failed to update order by ID: {e}")
            return None

    def get_order_by_ticket(self, ticket):
        """Get an order by its ticket."""
        try:
            return self.client.collection("Orders").get_full_list(200, {"filter": f"ticket = '{ticket}'"})
        except Exception as e:
            logging.error(f"Failed to get order by ticket: {e}")
            return None

    def get_open_orders_only(self):
        """Get all open orders."""
        try:
            return self.client.collection("Orders").get_full_list(200, {"filter": "is_closed = false"})
        except Exception as e:
            logging.error(f"Failed to get open orders: {e}")
            return None

    def get_open_pending_orders(self):
        """Get all pending orders."""
        try:
            return self.client.collection("Orders").get_full_list(200, {"filter": "is_closed = false && is_pending = true"})
        except Exception as e:
            logging.error(f"Failed to get open pending orders: {e}")
            return None
    def get_mt5_credintials(self):
        """Get all pending orders."""
        try:
            return self.client.collection("mt5_auth").get_full_list(200 )
        except Exception as e:
            logging.error(f"Failed to get mt5 credintials: {e}")
            return None
    def set_mt5_credintials(self,data):
        """Get all pending orders."""
        try:
            return self.client.collection("mt5_auth").create(data)
        except Exception as e:
            logging.error(f"Failed to set mt5 credintials: {e}")
            return None
    def get_pb_credintials(self):
        """Get all pending orders."""
        try:
            return self.client.collection("pb_auth").get_full_list(200)
        except Exception as e:
            logging.error(f"Failed to get remote credintials: {e}")
            return None
    def set_pb_credintials(self,data):
        """Get all pending orders."""
        try:
            return self.client.collection("pb_auth").create(data)
        except Exception as e:
            logging.error(f"Failed to set remote credintials: {e}")
            return None