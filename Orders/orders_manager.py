
from Orders.order import order
import time
import threading
class orders_manager:
    def __init__(self, local_api,mt5):
        self.local_api = local_api
        self.mt5 = mt5
        self.all_mt5_orders = []
        self.all_db_orders = []
        self.suspious_orders = []
    

    def get_all_mt5_orders(self):
        orders = self.mt5.get_all_orders()
        positions = self.mt5.get_all_positions()

        if orders:
            for pos in orders:
                self.all_mt5_orders.append(pos.ticket)

        if positions:
            for position in positions:
                self.all_mt5_orders.append(position.ticket)

        return self.all_mt5_orders
    
    # update orders in database
    def update_orders_in_db(self):
        for pos in self.all_mt5_orders:
            # get order from database
            db_order = self.local_api.get_order_by_ticket(pos)
            # if order exists in database, update it
            if db_order:
                order_obj= order( db_order[0], db_order[0].is_pending,self.mt5,self.local_api,"db")
                
                order_obj.update_from_mt5()
                order_obj.update_order()
        # go through all db orders and update
        for db_order in self.suspious_orders:
            # get order from database
            is_closed = self.mt5.check_order_is_closed(db_order.ticket)
            # if order exists in MT5, update it
            if is_closed:
                order_obj= order( db_order, db_order.is_pending,self.mt5,self.local_api,"db")
                order_obj.is_closed=is_closed
                order_obj.update_order()
            # # if order does not exist in database, create it
            # else:
            #     order_obj= order(None, pos, False,self.mt5,self.local_api)
            #     self.local_api.create_order( pos.to_dict())
    # function that get all open orders in database
    def get_all_orders_in_db(self):
        self.all_db_orders= self.local_api.get_open_orders_only()
        return self.all_db_orders
    # function that get all suspicious orders in database
    def get_suspicious_orders_in_db(self):
        # get the orders in db orders and not in mt5 orders
        self.suspious_orders = [order for order in self.all_db_orders if order not in self.all_mt5_orders]
        return self.suspious_orders
           
    # run in thread
    def run_orders_manager(self):
        #loop 
        while True:
            self.all_mt5_orders = self.get_all_mt5_orders()  # get all orders from MT5
            self.all_db_orders = self.get_all_orders_in_db() # get all orders from DB
            self.get_suspicious_orders_in_db()
            self.update_orders_in_db()
            time.sleep(1) # sleep for 10 seconds before checking again
       
                
    # run in thread
    def run_in_thread(self):
        OrdersManager = threading.Thread(target=self.run_orders_manager, daemon=True)
        # Start the thread
        OrdersManager.start()            
