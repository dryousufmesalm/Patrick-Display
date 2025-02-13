import datetime
from DB.ah_strategy.repositories.ah_repo import AHRepo
from DB.ct_strategy.repositories.ct_repo import CTRepo

from DB.db_engine import engine


class order:
    def __init__(self, order_data, is_pending, mt5, local_api, source=None, cycle_id=""):
        self.comment = order_data.comment
        self.commission = order_data.commission if source == "db" else 0
        self.is_pending = is_pending
        self.is_closed = order_data.is_closed if source == "db" else False
        self.kind = order_data.kind if source == "db" else order_data.comment
        self.magic_number = order_data.magic if source == "mt5" else order_data.magic_number
        self.open_price = round(order_data.price_open,
                                2) if source == "mt5" else order_data.open_price
        self.open_time = datetime.datetime.fromtimestamp(order_data.time_setup if is_pending else order_data.time).strftime(
            "%Y-%m-%d %H:%M:%S") if source == "mt5" else order_data.open_time
        self.profit = round(0 if is_pending else order_data.profit, 2)
        self.sl = round(order_data.sl, 2)
        self.swap = round(0 if is_pending else order_data.swap, 2)
        self.symbol = order_data.symbol
        self.ticket = order_data.ticket
        self.tp = round(order_data.tp, 2)
        self.type = order_data.type
        self.volume = round(order_data.volume_current if is_pending else order_data.volume,
                            2) if source == "mt5" else order_data.volume
        self.trailing_steps = round(
            order_data.trailing_steps, 2) if source == "db" else 0
        self.Mt5 = mt5
        self.local_api = local_api
        self.id = getattr(order_data, 'id', "")
        self.account = self.Mt5.account_id
        self.cycle_id = cycle_id
        self.ah_repo = AHRepo(engine=engine)
        self.ct_repo = CTRepo(engine=engine)

    def to_dict(self):
        return {

            "ticket": self.ticket,
            "comment": self.comment,
            "commission": self.commission,
            "is_pending": self.is_pending,
            "kind": self.kind,
            "magic_number": self.magic_number,
            "open_price": self.open_price,
            "open_time": self.open_time,
            "profit": self.profit,
            "sl": self.sl,
            "swap": self.swap,
            "symbol": self.symbol,
            "tp": self.tp,
            "type": self.type,
            "volume": self.volume,
            "is_closed": self.is_closed,
            "trailing_steps": self.trailing_steps,
            "account":  self.account,
            "cycle_id": self.cycle_id,
        }

    def update_from_mt5(self):
        # check if the order is pending
        self.is_pending = self.Mt5.check_order_is_pending(self.ticket)
        # if the order is closed, mark it as closed and return False
        self.is_closed = self.Mt5.check_order_is_closed(self.ticket)

        # get the order information if it exists and update the class attributes accordingly
        # if the order does not exist, print an error message and return False. Otherwise, return True.
        if self.is_pending:
            order_data = self.Mt5.get_order_by_ticket(ticket=self.ticket)
        else:
            order_data = self.Mt5.get_position_by_ticket(ticket=self.ticket)
        if len(order_data) == 0:
            return False
        if self.is_closed:
            return False
        order_data = order_data[0]

        self.comment = order_data.comment
        self.magic_number = order_data.magic
        self.open_price = round(order_data.price_open, 2)
        self.open_time = datetime.datetime.fromtimestamp(
            order_data.time_setup if self.is_pending else order_data.time).strftime('%Y-%m-%d %H:%M:%S')
        self.profit = round(0 if self.is_pending else order_data.profit, 2)
        self.swap = round(0 if self.is_pending else order_data.swap, 2)
        self.symbol = order_data.symbol
        self.ticket = order_data.ticket
        self.type = order_data.type
        self.volume = round(
            order_data.volume_current if self.is_pending else order_data.volume, 2)

        return True

    def check_false_closed_cycles(self):
        from cycles.AH_cycle import cycle as AH_cycle
        from cycles.CT_cycle import cycle as CT_cycle
        cycle_data = self.ah_repo.get_cycle_by_id(self.cycle_id)
        if cycle_data is not None:
            cycle_obj = AH_cycle(cycle_data, self.Mt5, self, "db")
            if cycle_obj is not None:
                if cycle_obj.is_closed == True:
                    cycle_obj.is_closed = False
                    if self.ticket in cycle_obj.closed:
                        cycle_obj.closed.remove(self.ticket)
                    cycle_obj.status = "recovery"
                    cycle_obj.closing_method = {}
                    for pos in cycle_obj.closed:
                        # move order to open depend on kind
                        if (self.kind == "pending"):
                            cycle_obj.remove_pending_order(pos)
                        if (self.kind == "initial"):
                            cycle_obj.remove_initial_order(pos)
                        if (self.kind == "hedge"):
                            cycle_obj.remove_hedge_order(pos)
                        if (self.kind == "recovery"):
                            cycle_obj.remove_recovery_order(pos)
                    cycle_obj.update_AH_cycle()
            return True

        cycle_data = self.ct_repo.get_cycle_by_id(self.cycle_id)
        if cycle_data is not None:
            cycle_obj = CT_cycle(cycle_data, self.Mt5, self, "db")
            if cycle_obj is not None:
                if cycle_obj.is_closed == True:
                    cycle_obj.is_closed = False
                    if self.ticket in cycle_obj.closed:
                        cycle_obj.closed.remove(self.ticket)
                    cycle_obj.status = "recovery"
                    cycle_obj.closing_method = {}
                    for pos in cycle_obj.closed:
                        # move pos to open depend on kind
                        if (self.kind == "pending"):
                            cycle_obj.remove_pending_order(pos)
                        if (self.kind == "initial"):
                            cycle_obj.remove_initial_order(pos)
                        if (self.kind == "hedge"):
                            cycle_obj.remove_hedge_order(pos)
                        if (self.kind == "recovery"):
                            cycle_obj.remove_recovery_order(pos)
                        if (self.kind == "threshold"):
                            cycle_obj.remove_threshold_order(pos)
                    cycle_obj.update_CT_cycle()
        return True

    def update_order_configs(self, stoploss, take_profit, trailing):
        # Update the order configurations using MetaTrader
        self.sl = round(stoploss, 2)
        self.tp = round(take_profit, 2)
        self.trailing_steps = round(trailing, 2)

    def close_order(self):
        # Close the order using MetaTrader
        if self.is_pending:
            print(f"Closing pending order with ticket {self.ticket}")
            data = self.to_dict()
            res = self.Mt5.close_order(data, 30)
            if res.retcode == 10009:
                self.is_closed = True

        else:
            print(f"Closing order with ticket {self.ticket}")
            data = self.to_dict()
            res = self.Mt5.close_position(data, 30)
            if res.retcode == 10009:
                self.is_closed = True

        # update the order
        self.update_order()

        return self.is_closed

    # create a new order
    def create_order(self):
        # Create the order using MetaTrader
        print(f"Creating order with ticket {self.ticket}")
        res = self.local_api.create_order(self.to_dict())
        return res
    # update the order

    def update_order(self):
        # Update the order using MetaTrader
        res = self.local_api.update_order_by_id(self.id, self.to_dict())
        return res

    def ManageOrder(self, sltp):
        # check if the order hits the stoploss or take profit
        if self.is_closed:
            return
        if sltp == "price":
            ask = self.Mt5.get_ask(self.symbol)
            bid = self.Mt5.get_bid(self.symbol)
            if self.type == 0:
                if self.tp <= ask:
                    self.close_order()
            else:
                if self.sl >= ask:
                    self.close_order()
        else:
            if self.type == "buy":
                if self.tp <= self.profit:
                    self.close_order()
            else:
                if self.sl >= self.profit:
                    self.close_order()


# Example usage:
# order1 = Order(self.bot.id, order1[0], is_pending)
# data["orders"]["orders"].append(order1.to_dict())
# if order2:
#     order2 = Order(self.bot.id, order2[0], is_pending)
#     data["orders"]["orders"].append(order2.to_dict())
