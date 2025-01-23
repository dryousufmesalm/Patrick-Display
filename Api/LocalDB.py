
from pony.orm import *
import logging

db = Database()
class AH_cycle(db.Entity ):
    lower_bound = Required(int)
    upper_bound = Required(int)
    is_pending = Required(bool)
    is_closed = Required(bool)
    closing_method = Optional(Json)
    opened_by = Optional(Json)
    lot_idx = Required(int)
    status = Required(str)
    total_volume = Required(int)
    total_profit = Required(int)
    zone_index = Required(int)
    bot = Required(str)
    account = Required(str)
    symbol = Required(str)
    pending = Optional(Json)
    initial = Optional(Json)
    closed = Optional(Json)
    hedge = Optional(Json)
    recovery = Optional(Json)
    cycle_id = Required(str)
    max_recovery = Optional(Json)

class CT_cycle(db.Entity):
    lower_bound = Required(int)
    upper_bound = Required(int)
    is_pending = Required(bool)
    is_closed = Required(bool)
    closing_method = Optional(Json)
    opened_by = Optional(Json)
    lot_idx = Required(int)
    status = Required(str)
    total_volume = Required(int)
    total_profit = Required(int)
    zone_index = Required(int)
    bot = Required(str)
    account = Required(str)
    symbol = Required(str)
    pending = Optional(Json)
    initial = Optional(Json)
    closed = Optional(Json)
    hedge = Optional(Json)
    recovery = Optional(Json)
    cycle_id = Required(str)
    threshold = Optional(Json)
    threshold_upper = Required(int)
    threshold_lower = Required(int)
class Orders(db.Entity):
    ticket = Required(int)
    comment = Required(str)
    commission = Required(int)
    is_pending = Required(bool)
    kind = Required(str)
    magic_number = Required(int)
    open_price = Required(float)
    open_time = Required(str)  # Store as string; consider using datetime for actual datetime
    profit = Required(int)
    tp = Required(int)
    sl = Required(int)
    swap = Required(int)
    symbol = Required(str)
    type = Required(int)
    volume = Required(float)
    is_closed = Required(bool)
    trailing_steps = Required(int)
    # JSON fields
    closing_method = Optional(Json)
    opened_by = Optional(Json)
    pending = Optional(Json)
    initial = Optional(Json)
    closed = Optional(Json)
    hedge = Optional(Json)
    recovery = Optional(Json)
    cycle_id = Optional(str)
    threshold = Optional(Json)
    threshold_upper = Optional(int)
    threshold_lower = Optional(int)
class Mt5Login(db.Entity):
    username = Required(int)
    password = Required(str)
    server = Required(str)
    type = Required(str)
    program_path = Required(str)
    # JSON fields
    additional_info = Optional(Json)
class PbLogin(db.Entity):
    username = Required(str)
    password = Required(str)
    server = Required(str)

db.bind(provider='sqlite',  filename='database.sqlite', create_db=True)
db.generate_mapping(create_tables=True)
set_sql_debug(True)
class API:
    """ The base class for all the API handlers"""
    def __init__(self):
        self.authenticated = False
        self.user_name = None
        self.user_email = None
        self.is_active = False
        self.user_id = None

    @db_session
    def create_AH_cycle(self, data):
        """Create a cycle."""
        try:
            ah_cycle = AH_cycle(**data)
            return ah_cycle
        except Exception as e:
            logging.error(f"Failed to create AH cycle: {e}")
            return None

    @db_session
    def delete_AH_cycle(self, cycle_id):
        """Delete a cycle."""
        try:
            ah_cycle = AH_cycle.get(id=cycle_id)
            if ah_cycle:
                ah_cycle.delete()
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to delete AH cycle: {e}")
            return None

    @db_session
    def get_AH_cycle_by_id(self, cycle_id):
        """Get a cycle by its ID."""
        try:
            return AH_cycle.get(id=cycle_id)
        except Exception as e:
            logging.error(f"Failed to get AH cycle by ID: {e}")
            return None

    @db_session
    def get_AH_active_cycles(self):
        """Get all active cycles."""
        try:
            return select(c for c in AH_cycle if not c.is_closed)[:]
        except Exception as e:
            logging.error(f"Failed to get AH active cycles: {e}")
            return None

    @db_session
    def update_AH_cycle_by_id(self, cycle_id, data):
        """Update a cycle by its ID."""
        try:
            ah_cycle = AH_cycle.get(id=cycle_id)
            if ah_cycle:
                ah_cycle.set(**data)
                return ah_cycle
            return None
        except Exception as e:
            logging.error(f"Failed to update AH cycle by ID: {e}")
            return None

    @db_session
    def get_AH_cycle_by_cycle_id(self, cycle_id):
        """Get a cycle by its cycle ID."""
        try:
            return AH_cycle.get(cycle_id=cycle_id)
        except Exception as e:
            logging.error(f"Failed to get AH cycle by cycle ID: {e}")
            return None

    @db_session
    def close_AH_cycle(self, cycle_id):
        """Close a cycle by its ID."""
        try:
            ah_cycle = AH_cycle.get(id=cycle_id)
            if ah_cycle:
                ah_cycle.is_closed = True
                return ah_cycle
            return None
        except Exception as e:
            logging.error(f"Failed to close AH cycle: {e}")
            return None

    @db_session
    def create_CT_cycle(self, data):
        """Create a cycle."""
        try:
            ct_cycle = CT_cycle(**data)
            return ct_cycle
        except Exception as e:
            logging.error(f"Failed to create CT cycle: {e}")
            return None

    @db_session
    def delete_CT_cycle(self, cycle_id):
        """Delete a cycle."""
        try:
            ct_cycle = CT_cycle.get(id=cycle_id)
            if ct_cycle:
                ct_cycle.delete()
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to delete CT cycle: {e}")
            return None

    @db_session
    def get_CT_cycle_by_id(self, cycle_id):
        """Get a cycle by its ID."""
        try:
            return CT_cycle.get(id=cycle_id)
        except Exception as e:
            logging.error(f"Failed to get CT cycle by ID: {e}")
            return None

    @db_session
    def get_CT_active_cycles(self):
        """Get all active cycles."""
        try:
            return select(c for c in CT_cycle if not c.is_closed)[:]
        except Exception as e:
            logging.error(f"Failed to get CT active cycles: {e}")
            return None

    @db_session
    def update_CT_cycle_by_id(self, cycle_id, data):
        """Update a cycle by its ID."""
        try:
            ct_cycle = CT_cycle.get(id=cycle_id)
            if ct_cycle:
                ct_cycle.set(**data)
                return ct_cycle
            return None
        except Exception as e:
            logging.error(f"Failed to update CT cycle by ID: {e}")
            return None

    @db_session
    def get_CT_cycle_by_cycle_id(self, cycle_id):
        """Get a cycle by its cycle ID."""
        try:
            return CT_cycle.get(cycle_id=cycle_id)
        except Exception as e:
            logging.error(f"Failed to get CT cycle by cycle ID: {e}")
            return None

    @db_session
    def close_CT_cycle(self, cycle_id):
        """Close a cycle by its ID."""
        try:
            ct_cycle = CT_cycle.get(id=cycle_id)
            if ct_cycle:
                ct_cycle.is_closed = True
                return ct_cycle
            return None
        except Exception as e:
            logging.error(f"Failed to close CT cycle: {e}")
            return None

    @db_session
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
            order = Orders(**data)
            return order
        except Exception as e:
            logging.error(f"Failed to create order: {e}")
            return None

    @db_session
    def delete_order(self, order_id):
        """Delete an order."""
        try:
            order = Orders.get(id=order_id)
            if order:
                order.delete()
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to delete order: {e}")
            return None

    @db_session
    def get_order_by_id(self, order_id):
        """Get an order by its ID."""
        try:
            return Orders.get(id=order_id)
        except Exception as e:
            logging.error(f"Failed to get order by ID: {e}")
            return None

    @db_session
    def update_order_by_id(self, order_id, data):
        """Update an order by its ID."""
        try:
            order = Orders.get(id=order_id)
            if order:
                order.set(**data)
                return order
            return None
        except Exception as e:
            logging.error(f"Failed to update order by ID: {e}")
            return None

    @db_session
    def get_order_by_ticket(self, ticket):
        """Get an order by its ticket."""
        try:
            return Orders.get(ticket=ticket)
        except Exception as e:
            logging.error(f"Failed to get order by ticket: {e}")
            return None

    @db_session
    def get_open_orders_only(self):
        """Get all open orders."""
        try:
            return select(o for o in Orders if not o.is_closed)[:]
        except Exception as e:
            logging.error(f"Failed to get open orders: {e}")
            return None

    @db_session
    def get_open_pending_orders(self):
        """Get all pending orders."""
        try:
            return select(o for o in Orders if not o.is_closed and o.is_pending)[:]
        except Exception as e:
            logging.error(f"Failed to get open pending orders: {e}")
            return None


    def get_mt5_credentials(self):
        """Get all MT5 credentials."""
        try:
            with db_session:
                return Mt5Login.select()
        except Exception as e:
            logging.error("Failed to get MT5 credentials: %s", e)
            return None
    def set_mt5_credentials(self, data):
        """Set MT5 credentials."""
        try:
            with db_session:
                mt5_login = Mt5Login(
                    username=data["username"],
                    password=data["password"],
                    server=data["server"],
                    type=data["type"],
                    program_path=data["program_path"]
            )
            return mt5_login
        except Exception as e:
            logging.error(f"Failed to set MT5 credentials: {e}")
            return None

    @db_session
    def get_pb_credentials(self):
        """Get all PocketBase credentials."""
        try:
            return select(c for c in PbLogin)[:]
        except Exception as e:
            logging.error(f"Failed to get PocketBase credentials: {e}")
            return None

    @db_session
    def set_pb_credentials(self, data):
        """Set PocketBase credentials."""
        try:
            pb_login = PbLogin(**data)
            return pb_login
        except Exception as e:
            logging.error(f"Failed to set PocketBase credentials: {e}")
            return None
        
local_auth=API()