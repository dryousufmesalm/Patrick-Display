
from Orders.order import order
import time
import threading
from DB.db_engine import engine
from DB.ah_strategy.repositories.ah_repo import AHRepo
from DB.ct_strategy.repositories.ct_repo import CTRepo


class orders_manager:
    def __init__(self, mt5):
        self.ah_repo = AHRepo(engine=engine)
        self.ct_repo = CTRepo(engine=engine)
        self.mt5 = mt5
        self.all_mt5_orders = []
        self.all_ah_orders = []
        self.suspious_ah_orders = []
        self.all_ct_orders = []
        self.suspious_ct_orders = []
        self.false_closed_orders = []

    def get_all_mt5_orders(self):
        orders = self.mt5.get_all_orders()
        positions = self.mt5.get_all_positions()
        self.all_mt5_orders = []
        if orders:
            for pos in orders:
                self.all_mt5_orders.append(pos.ticket)

        if positions:
            for position in positions:
                self.all_mt5_orders.append(position.ticket)

        return self.all_mt5_orders

    # update orders in database
    def update_ah_orders_in_db(self):
        for pos in self.all_mt5_orders:
            # get order from database
            db_order = self.ah_repo.get_order_by_ticket(pos)
            # if order exists in database, update it
            if db_order:
                order_obj = order(db_order, db_order.is_pending,
                                  self.mt5, self.ah_repo, "db", db_order.cycle_id)

                order_obj.update_from_mt5()
                order_obj.check_false_closed_cycles()

                order_obj.update_order()
        # go through all db orders and update
        for db_order in self.suspious_ah_orders:
            # get order from database
            is_closed = self.mt5.check_order_is_closed(db_order.ticket)
            # if order exists in MT5, update it
            if is_closed:
                print("Order is closed")
                order_obj = order(db_order, db_order.is_pending,
                                  self.mt5, self.ah_repo, "db", db_order.cycle_id)
                order_obj.is_closed = is_closed
                order_obj.update_order()
            # # if order does not exist in database, create it
            # else:
            #     order_obj= order(None, pos, False,self.mt5,self.local_api)
            #     self.local_api.create_order( pos.to_dict())
    # function that get all open orders in database

    def get_all_ah_orders_in_db(self):
        orders = self.ah_repo.get_open_orders_only()
        self.all_ah_orders = [
            entry for entry in orders if entry.account == self.mt5.account_id]
        return self.all_ah_orders

    def get_suspicious_ah_orders_in_db(self):
        # get the orders in db orders and not in mt5 orders
        self.suspious_ah_orders = [
            order for order in self.all_ah_orders if order not in self.all_mt5_orders]
        return self.suspious_ah_orders

    def get_false_closed_orders(self):
        # compare all orders in db with mt5 orders
        if len(self.all_ah_orders) != len(self.all_mt5_orders):
            self.false_closed_orders = [
                order for order in self.all_ah_orders if order not in self.all_mt5_orders]

    def update_ct_orders_in_db(self):
        for pos in self.all_mt5_orders:
            # get order from database
            db_order = self.ct_repo.get_order_by_ticket(pos)
            # if order exists in database, update it
            if db_order:
                order_obj = order(db_order, db_order.is_pending,
                                  self.mt5, self.ct_repo, "db", db_order.cycle_id)

                order_obj.update_from_mt5()
                order_obj.check_false_closed_cycles()
                order_obj.update_order()
        # go through all db orders and update
        for db_order in self.suspious_ct_orders:
            # get order from database
            is_closed = self.mt5.check_order_is_closed(db_order.ticket)
            # if order exists in MT5, update it
            if is_closed:
                order_obj = order(db_order, db_order.is_pending,
                                  self.mt5, self.ct_repo, "db", db_order.cycle_id)
                order_obj.is_closed = is_closed
                order_obj.update_order()
            # # if order does not exist in database, create it
            # else:
            #     order_obj= order(None, pos, False,self.mt5,self.local_api)
            #     self.local_api.create_order( pos.to_dict())
    # function that get all open orders in database

    def get_all_ct_orders_in_db(self):
        orders = self.ct_repo.get_open_orders_only()
        self.all_ct_orders = [
            entry for entry in orders if entry.account == self.mt5.account_id]
        return self.all_ct_orders
    # function that get all suspicious orders in database

    def get_suspicious_ct_orders_in_db(self):
        # get the orders in db orders and not in mt5 orders
        self.suspious_ct_orders = [
            order for order in self.all_ct_orders if order not in self.all_mt5_orders]
        return self.suspious_ct_orders

    # run in thread
    def run_orders_manager(self):
        # loop
        while True:
            self.all_mt5_orders = self.get_all_mt5_orders()  # get all orders from MT5
            self.all_ah_orders = self.get_all_ah_orders_in_db()  # get all orders from DB
            self.get_suspicious_ah_orders_in_db()
            self.update_ah_orders_in_db()
            self.all_ct_orders = self.get_all_ct_orders_in_db()
            self.get_suspicious_ct_orders_in_db()
            self.update_ct_orders_in_db()
            time.sleep(1)  # sleep for 10 seconds before checking again

    # run in thread

    def run_in_thread(self):
        OrdersManager = threading.Thread(
            target=self.run_orders_manager, daemon=True)
        # Start the thread
        OrdersManager.start()
