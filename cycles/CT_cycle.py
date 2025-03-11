import datetime
from Orders.order import order
import MetaTrader5 as Mt5
from DB.db_engine import engine
from DB.ct_strategy.repositories.ct_repo import CTRepo
from types import SimpleNamespace


class cycle:
    def __init__(self, data, mt5, bot, source=None):
        self.bot_id = data.bot if source in ("db", "remote") else data["bot"]
        self.initial = data.initial if source == "db" else [
        ] if source == "remote" else data["initial"]
        self.hedge = data.hedge if source == "db" else [
        ] if source == "remote" else data["hedge"]
        self.recovery = data.recovery if source == "db" else [
        ] if source == "remote" else data["recovery"]
        self.pending = data.pending if source == "db" else [
        ] if source == "remote" else data["pending"]
        self.closed = data.closed if source == "db" else [
        ] if source == "remote" else data["closed"]
        self.threshold = data.threshold if source == "db" else [
        ] if source == "remote" else data["threshold"]
        self.is_closed = data.is_closed if source in (
            "db", "remote") else data['is_closed']
        self.lower_bound = data.lower_bound if source in (
            "db", "remote") else data['lower_bound']
        self.upper_bound = data.upper_bound if source in (
            "db", "remote") else data['upper_bound']
        self.lot_idx = data.lot_idx if source in (
            "db", "remote") else data['lot_idx']
        self.zone_index = data.zone_index if source == "db" else 0 if source == "remote" else data[
            'zone_index']
        self.status = data.status if source in (
            "db", "remote") else data['status']
        self.symbol = data.symbol if source in (
            "db", "remote") else data['symbol']
        self.total_profit = data.total_profit if source in (
            "db", "remote") else data['total_profit']
        self.total_volume = data.total_volume if source in (
            "db", "remote") else data['total_volume']
        self.closing_method = data.closing_method if source in (
            "db", "remote") else data['closing_method']
        self.opened_by = data.opened_by if source in (
            "db", "remote") else data['opened_by']
        self.account = data.account if source in (
            "db", "remote") else data['account']
        self.id = data.id if source == "db" else ""
        self.cycle_id = data.remote_id if source == "db" else data.id if source == "remote" else ""
        self.is_pending = data.is_pending if source == "db" else False if source == "remote" else data[
            'is_pending']
        self.local_api = CTRepo(engine=engine)
        self.mt5 = mt5
        self.bot = bot
        self.threshold_upper = data.threshold_upper if source == "db" else data[
            'threshold_top'] if source == "remote" else data["threshold_upper"]
        self.threshold_lower = data.threshold_lower if source == "db" else data[
            'threshold_bottom'] if source == "remote" else data["threshold_lower"]
        self.cycle_type = data.cycle_type if source == "db" else data['cycle_type']

        self.orders = self.get_orders_from_remote(
            data.orders['orders']) if source == 'remote' else self.combine_orders()
        self.open_price = self.local_api.get_order_by_ticket(
            self.initial[0]).open_price if len(self.initial) > 0 else 0
        self.buyLots = 0
        self.sellLots = 0

    def combine_orders(self):
        return self.initial + self.hedge + self.pending + self.recovery + self.threshold

    def get_orders_from_remote(self, orders):
        for order_data in orders:
            # convet orderdata to subscrible

            order_obj = order(SimpleNamespace(order_data),
                              self.is_pending, self.mt5, self.local_api, "db")
            order_obj.create_order()
            # add the order to the orders list
            order_kind = order_obj.kind
            order_ticket = order_obj.ticket
            if order_kind == "initial":
                self.remove_initial_order(order_ticket)
            elif order_kind == "hedge":
                self.remove_hedge_order(order_ticket)
            elif order_kind == "recovery":
                self.remove_recovery_order(order_ticket)
            elif order_kind == "pending":
                self.remove_pending_order(order_ticket)
            elif order_kind == "threshold":
                self.remove_threshold_order(order_ticket)
    # create cycle data

    def to_dict(self):
        data = {

            "bot": self.bot_id,
            "account": self.account,
            "is_pending": self.is_pending,
            "is_closed": self.is_closed,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "lot_idx": self.lot_idx,
            "zone_index": self.zone_index,
            "status": self.status,
            "symbol": self.symbol,
            "total_profit": self.total_profit,
            "total_volume": self.total_volume,
            "closing_method": self.closing_method,
            "initial": self.initial,
            "hedge": self.hedge,
            "pending": self.pending,
            "closed": self.closed,
            "recovery": self.recovery,
            "threshold": self.threshold,
            "opened_by": self.opened_by,
            "remote_id": self.cycle_id,
            "threshold_upper": round(float(self.threshold_upper), 2),
            "threshold_lower": round(float(self.threshold_lower), 2),
            "cycle_type": self.cycle_type,



        }

        return data
    # create cycle  data to  send to remote server

    def to_remote_dict(self):
        data = {
            "bot": self.bot_id,
            "account": self.account,
            "is_pending": self.is_pending,
            "is_closed": self.is_closed,
            "lower_bound": round(self.lower_bound, 2),
            "upper_bound": round(self.upper_bound, 2),
            "lot_idx": self.lot_idx,
            "zone_index": self.zone_index,
            "status": self.status,
            "symbol": self.symbol,
            "total_profit": round(float(self.total_profit), 2),
            "total_volume": round(float(self.total_volume), 2),
            "closing_method": self.closing_method,
            "orders": {
                "orders": []},
            "opened_by": self.opened_by,
            "cycle_type": self.cycle_type,
            "threshold_top": round(float(self.threshold_upper),2),
            "threshold_bottom": round(float(self.threshold_lower),2)

        }
        #  go through the orders and add them to the data
        for order_ticket in self.orders:
            order_data = self.local_api.get_order_by_ticket(order_ticket)
            order_obj = order(order_data, order_data.is_pending,
                              self.mt5, self.local_api, "db", self.id)
            data["orders"]["orders"].append(order_obj.to_dict())

        for order_ticket in self.closed:
            order_data = self.local_api.get_order_by_ticket(order_ticket)
            order_obj = order(order_data, order_data.is_pending,
                              self.mt5, self.local_api, "db", self.id)
            data["orders"]["orders"].append(order_obj.to_dict())
        return data
    # add  initial order

    def add_initial_order(self, order_ticket):

        self.initial.append(order_ticket)
        self.status = "initial"
    # add hedge order

    def add_hedge_order(self, order_ticket):
        self.hedge.append(order_ticket)
        self.status = "hedge"
    # add recovery order

    def add_recovery_order(self, order_ticket):
        self.recovery.append(order_ticket)
        self.status = "recovery"
    # add pending order

    def add_pending_order(self, order_ticket):
        self.pending.append(order_ticket)
        self.status = "pending"
    #  add thresholds order

    def add_threshold_order(self, order_ticket):
        self.threshold.append(order_ticket)
        self.status = "threshold"
    # remove pending order from pending

    def remove_pending_order(self, order_ticket):
        if order_ticket in self.pending:
            self.pending.remove(order_ticket)

    # remove initial order from initial list
    def remove_initial_order(self, order_ticket):
        if order_ticket in self.initial:
            self.initial.remove(order_ticket)

    # remove hedge order from hedge list
    def remove_hedge_order(self, order_ticket):
        if order_ticket in self.hedge:
            self.hedge.remove(order_ticket)

    # remove recovery order from recovery list
    def remove_recovery_order(self, order_ticket):
        if order_ticket in self.recovery:
            self.recovery.remove(order_ticket)

    # remove threshold order from  list\
    def remove_threshold_order(self, order_ticket):
        if order_ticket in self.threshold:
            self.threshold.remove(order_ticket)

    # update cylce orders
    async def update_cycle(self, remote_api):
        self.total_profit = 0
        self.total_volume = 0
        self.sellLots = 0
        self.buyLots = 0
        for order_ticket in self.orders:
            order_data = self.local_api.get_order_by_ticket(order_ticket)
            if order_data:
                self.total_profit += order_data.profit+order_data.swap+order_data.commission
                self.total_volume += order_data.volume
                if order_data.type == Mt5.ORDER_TYPE_SELL:
                    self.sellLots += order_data.volume
                elif order_data.type == Mt5.ORDER_TYPE_BUY:
                    self.buyLots += order_data.volume
                # check if order is already closed
                if order_data.is_closed:
                    if order_ticket not in self.closed:
                        self.closed.append(order_ticket)
                    order_kind = order_data.kind
                    if order_kind == "initial":
                        self.remove_initial_order(order_ticket)
                    elif order_kind == "hedge":
                        self.remove_hedge_order(order_ticket)
                    elif order_kind == "recovery":
                        self.remove_recovery_order(order_ticket)
                    elif order_kind == "pending":
                        if order_ticket in self.pending:
                            self.remove_pending_order(order_ticket)
                        if order_ticket in self.initial:
                            self.remove_initial_order(order_ticket)
                    elif order_kind == "threshold":
                        self.remove_threshold_order(order_ticket)
                if order_data.is_pending is False and order_ticket in self.pending:
                    self.remove_pending_order(order_ticket)
                    self.add_initial_order(order_ticket)
                    self.is_pending = False
                    self.status = "initial"
        for order_ticket in self.closed:
            order_data = self.local_api.get_order_by_ticket(order_ticket)
            if (order_data and order_data.kind != "pending" and order_data.kind != "initial") or (self.bot.ADD_All_to_PNL==True):
                self.total_profit += order_data.profit+order_data.swap+order_data.commission
        if len(self.pending) == 0 and self.is_pending is True:
            self.is_pending = False
            self.status = "initial"
        if len(self.pending) == 0 and len(self.initial) == 1 and self.status == "initial" and self.cycle_type == "BUY&SELL" and len(self.orders) == 1 and len(self.closed) == 0:
            # # close the pending order anc open it as market order
            order_data = self.local_api.get_order_by_ticket(self.initial[0])
            order_obj = order(order_data, order_data.is_pending,
                              self.mt5, self.local_api, "db", self.id)
            new_order = self.mt5.sell(
                self.symbol, order_obj.volume, self.bot.bot.magic, 0, 0, "PIPS", self.bot.slippage, "initial")
            self.add_initial_order(new_order[0].ticket)
            new_order_obj = order(
                new_order[0], False, self.mt5, self.local_api, "mt5", self.id)
            new_order_obj.create_order()

        if len(self.orders) == 0:
            self.status = "closed"
            self.is_closed = True
            self.closing_method["sent_by_admin"] = False
            self.closing_method["status"] = "MetaTrader5"
            self.closing_method["username"] = "MetaTrader5"
            remote_api.update_CT_cycle_by_id(
                self.cycle_id, self.to_remote_dict())
        self.local_api.Update_cycle(self.id, self.to_dict())
    # create a new cycle

    def create_cycle(self):
        self.orders = self.combine_orders()
        cycle_data = self.local_api.create_cycle(self.to_dict())
        for order_ticket in self.orders:
            order_data = self.local_api.get_order_by_ticket(order_ticket)
            order_objec = order(order_data, order_data.is_pending,
                                self.mt5, self.local_api, "db", cycle_data.id)
            order_objec.update_order()
        return cycle_data
    # close cycle

    def close_cycle(self, sent_by_admin, user_id, username):

        # if cycle is not closed, close it and return True
        for order_id in self.orders:
            order_data = self.local_api.get_order_by_ticket(order_id)
            if order_data:
                orderobj = order(order_data, self.is_pending,
                                 self.mt5, self.local_api, "db", self.id)
                if orderobj.close_order() is False:
                    return False
            

        self.is_closed = True
        self.status = "closed"
        self.closing_method["sent_by_admin"] = sent_by_admin
        if user_id == 0:
            self.closing_method["status"] = "MetaTrader5"
            self.closing_method["username"] = "MetaTrader5"
        else:
            self.closing_method["user_id"] = user_id
            self.closing_method["status"] = "closed by User"
        self.closing_method["username"] = username
        self.local_api.Update_cycle(self.id, self.to_dict())

        return True

    async def manage_cycle_orders(self, threshold):
        if self.is_pending:
            return
        if self.is_closed:
            return
        ask = self.mt5.get_ask(self.symbol)
        bid = self.mt5.get_bid(self.symbol)
        if self.status == "initial":
            if ask > self.upper_bound:
                total_sell = self.count_initial_sell_orders()
                if total_sell >= 1:
                    self.close_initial_buy_orders()
                    self.hedge_sell_order()
                    self.status = "recovery"
                    self.update_CT_cycle()
            elif bid < self.lower_bound:
                total_buy = self.count_initial_buy_orders()
                if total_buy >= 1:
                    self.close_initial_sell_orders()
                    self.hedge_buy_order()
                    self.status = "recovery"
                    self.update_CT_cycle()
        elif self.status in ["recovery", "max_recovery"]:
            # if not self.bot.disable_new_cycle_recovery:
            #     self.go_opposite_direction()
            self.go_hedge_direction()

        # add new order every x pips
        self.threshold_Reposition(threshold)
        if ask >= self.threshold_upper and len(self.hedge) > 0:
            self.threshold_buy_order(
                self.threshold_upper+threshold * self.mt5.get_pips(self.symbol))
        elif bid <= self.threshold_lower and len(self.hedge)>0:
            self.threshold_sell_order(
                self.threshold_lower - threshold * self.mt5.get_pips(self.symbol))
       
    def close_initial_buy_orders(self):
        total_initial = len(self.initial)
        if total_initial > 1:
            for i in range(total_initial):
                ticket = self.initial[i]
                order_data_db = self.local_api.get_order_by_ticket(ticket)
                orderobj = order(order_data_db, self.is_pending,
                                 self.mt5, self.local_api, "db", self.id)
                if orderobj.type == Mt5.ORDER_TYPE_BUY:
                    orderobj.close_order()
                    self.initial.pop(i)
                    self.closed.append(ticket)
                    break

    def threshold_Reposition(self, threshold):
        lowest = self.threshold_lower
        highest = self.threshold_upper
        for order_ticket in self.initial:
            order_data_db = self.local_api.get_order_by_ticket(order_ticket)
            orderobj = order(order_data_db, self.is_pending,
                             self.mt5, self.local_api, "db", self.id)
            if orderobj.type == Mt5.ORDER_TYPE_SELL:
                lowest = orderobj.open_price - threshold * self.mt5.get_pips(self.symbol)
                highest = orderobj.open_price + self.bot.zones[self.zone_index] * self.mt5.get_pips(
                    self.symbol)+threshold * self.mt5.get_pips(self.symbol)
            if orderobj.type == Mt5.ORDER_TYPE_BUY:
                highest = orderobj.open_price+threshold * self.mt5.get_pips(self.symbol)
                lowest = orderobj.open_price - self.bot.zones[self.zone_index] * self.mt5.get_pips(
                    self.symbol)-threshold * self.mt5.get_pips(self.symbol)
        for order_ticket in self.threshold:
            order_data_db = self.local_api.get_order_by_ticket(order_ticket)
            orderobj = order(order_data_db, self.is_pending,
                             self.mt5, self.local_api, "db", self.id)
            if orderobj.type == Mt5.ORDER_TYPE_SELL:
                if orderobj.open_price <= lowest:
                    lowest = orderobj.open_price
            if orderobj.type == Mt5.ORDER_TYPE_BUY:
                if orderobj.open_price >= highest:
                    highest = orderobj.open_price
        if lowest > self.threshold_lower:
            self.threshold_lower=lowest
        if highest < self.threshold_upper:
            self.threshold_upper=highest
        
    def close_initial_sell_orders(self):
        total_sells = len(self.initial)
        if total_sells > 1:
            for i in range(total_sells):
                ticket = self.initial[i]
                order_data_db = self.local_api.get_order_by_ticket(ticket)
                orderobj = order(order_data_db, self.is_pending,
                                 self.mt5, self.local_api, "db", self.id)
                if orderobj.type == Mt5.ORDER_TYPE_SELL:
                    orderobj.close_order()
                    self.initial.pop(i)
                    self.closed.append(ticket)
                    break

    def count_initial_sell_orders(self):
        total_sell = 0
        for ticket in self.initial:
            order_data_db = self.local_api.get_order_by_ticket(ticket)
            orderobj = order(order_data_db, self.is_pending,
                             self.mt5, self.local_api, "db", self.id)
            if orderobj.type == Mt5.ORDER_TYPE_SELL:
                total_sell += 1
        return total_sell

    def count_initial_buy_orders(self):
        total_buy = 0
        for ticket in self.initial:
            order_data_db = self.local_api.get_order_by_ticket(ticket)
            orderobj = order(order_data_db, self.is_pending,
                             self.mt5, self.local_api, "db", self.id)
            if orderobj.type == Mt5.ORDER_TYPE_BUY:
                total_buy += 1
        return total_buy

    def hedge_buy_order(self):
        self.orders = self.combine_orders()
        self.sellLots = 0
        self.buyLots = 0
        for order_ticket in self.orders:
            order_data = self.local_api.get_order_by_ticket(order_ticket)
            if order_data:
                if order_data.type == Mt5.ORDER_TYPE_SELL:
                    self.sellLots += order_data.volume
                elif order_data.type == Mt5.ORDER_TYPE_BUY:
                    self.buyLots += order_data.volume
        hedge_lot = self.buyLots-self.sellLots

        if self.bot.enable_recovery:
            recovery_order = self.mt5.buy(
                self.symbol, self.bot.lot_sizes[0], self.bot.bot.magic, 0, 0, "PIPS", self.bot.slippage, "recovery")
            if len(recovery_order) > 0:
                self.recovery.append(recovery_order[0].ticket)
                # create a new order
                order_obj = order(
                    recovery_order[0], False, self.mt5, self.local_api, "mt5", self.id)
                order_obj.create_order()

        if hedge_lot <= 0:
            return
        hedge_order = self.mt5.sell(
            self.symbol, hedge_lot, self.bot.bot.magic, 0, 0, "PIPS", self.bot.slippage, "hedge")
        self.zone_index = min(self.zone_index + 1, len(self.bot.zones) - 1)
        if len(hedge_order) > 0:
            # add the order to the hedge list
            self.hedge.append(hedge_order[0].ticket)
            # create a new order
            order_obj = order(
                hedge_order[0], False, self.mt5, self.local_api, "mt5", self.id)
            order_obj.create_order()
            self.lower_bound = float(hedge_order[0].price_open) - float(
                self.bot.zones[self.zone_index]) * float(self.mt5.get_pips(self.symbol))
            self.upper_bound = float(hedge_order[0].price_open) + float(
                self.bot.zones[self.zone_index]) * float(self.mt5.get_pips(self.symbol))

        # update the upper and lower by the zone index

    def threshold_buy_order(self, threshold):
        self.lot_idx = 0
        threshold_order = self.mt5.buy(
            self.symbol, self.bot.lot_sizes[self.lot_idx], self.bot.bot.magic, self.bot.hedges_numbers, 0, "PIPS", self.bot.slippage, "threshold")
        if len(threshold_order) > 0:
            # add the order to the hedge list
            self.threshold_upper = threshold 
            self.threshold.append(threshold_order[0].ticket)
            # create a new order
            order_obj = order(
                threshold_order[0], False, self.mt5, self.local_api, "mt5", self.id)
            order_obj.create_order()

    def threshold_sell_order(self, threshold):
        self.lot_idx = 0
        threshold_order = self.mt5.sell(
            self.symbol, self.bot.lot_sizes[self.lot_idx], self.bot.bot.magic, self.bot.hedges_numbers, 0, "PIPS", self.bot.slippage, "threshold")
        if len(threshold_order) > 0:
            # add the order to the hedge list
            self.threshold_lower = threshold 
            self.threshold.append(threshold_order[0].ticket)
            # create a new order
            order_obj = order(
                threshold_order[0], False, self.mt5, self.local_api, "mt5", self.id)
            order_obj.create_order()

    def hedge_sell_order(self):
        self.orders = self.combine_orders()

        self.sellLots = 0
        self.buyLots = 0
        for order_ticket in self.orders:
            order_data = self.local_api.get_order_by_ticket(order_ticket)
            if order_data:
                if order_data.type == Mt5.ORDER_TYPE_SELL:
                    self.sellLots += order_data.volume
                elif order_data.type == Mt5.ORDER_TYPE_BUY:
                    self.buyLots += order_data.volume

        hedge_lot = self.sellLots-self.buyLots
        # recovery order
        if self.bot.enable_recovery:
            recovery_order = self.mt5.sell(
                self.symbol, self.bot.lot_sizes[0], self.bot.bot.magic, 0, 0, "PIPS", self.bot.slippage, "recovery")
            if len(recovery_order) > 0:
                self.recovery.append(recovery_order[0].ticket)
                # create a new order
                order_obj = order(
                    recovery_order[0], False, self.mt5, self.local_api, "mt5", self.id)
                order_obj.create_order()
        # hedge order
        if hedge_lot <= 0:
            return
        hedge_order = self.mt5.buy(
            self.symbol, hedge_lot, self.bot.bot.magic, 0, 0, "PIPS", self.bot.slippage, "hedge")
        self.zone_index = min(self.zone_index + 1, len(self.bot.zones) - 1)
        if len(hedge_order) > 0:
            # add the order to the hedge list
            self.hedge.append(hedge_order[0].ticket)
            # create a new order
            order_obj = order(
                hedge_order[0], False, self.mt5, self.local_api, "mt5", self.id)
            order_obj.create_order()
            # update the upper and lower by the zone index
            self.lower_bound = float(hedge_order[0].price_open) - float(
                self.bot.zones[self.zone_index]) * float(self.mt5.get_pips(self.symbol))
            self.upper_bound = float(hedge_order[0].price_open) + float(
                self.bot.zones[self.zone_index]) * float(self.mt5.get_pips(self.symbol))

    def go_opposite_direction(self):
        # check recovery order length
        if len(self.recovery) < 1:
            return
        if len(self.recovery) > 0:
            ask = self.mt5.get_ask(self.symbol)
            bid = self.mt5.get_bid(self.symbol)
            if ask > self.upper_bound:
                self.close_recovery_orders()
                self.hedge_sell_order()

            elif bid < self.lower_bound:
                self.close_recovery_orders()
                self.hedge_buy_order()

    def close_recovery_orders(self):
        for ticket in self.recovery:
            order_data_db = self.local_api.get_order_by_ticket(ticket)
            orderobj = order(order_data_db, self.is_pending,
                             self.mt5, self.local_api, "db", self.id)
            orderobj.close_order()
            orderobj.is_closed = True
            orderobj.update_order()
            self.recovery.remove(ticket)
            self.closed.append(ticket)

    def go_hedge_direction(self):
        if len(self.hedge) > 0:
            ask = self.mt5.get_ask(self.symbol)
            bid = self.mt5.get_bid(self.symbol)
            if ask > self.upper_bound:
                last_hedge = self.hedge[-1]
                order_data_db = self.local_api.get_order_by_ticket(last_hedge)
                orderobj = order(order_data_db, self.is_pending,
                                 self.mt5, self.local_api, "db", self.id)
                last_hedge_type = orderobj.type
                last_hedge_profit = orderobj.profit
                # if last_hedge_type == Mt5.ORDER_TYPE_SELL and last_hedge_profit < 0:
                if(len(self.recovery) > 0):
                    last_recovery= self.recovery[-1]
                    order_data_recovery_db = self.local_api.get_order_by_ticket(
                        last_recovery)
                    if ( order_data_recovery_db.type==Mt5.ORDER_TYPE_SELL):
                        return
                self.close_recovery_orders()
                self.hedge_sell_order()
            elif bid < self.lower_bound:
                last_hedge = self.hedge[-1]
                order_data_db = self.local_api.get_order_by_ticket(last_hedge)
                orderobj = order(order_data_db, self.is_pending,
                                 self.mt5, self.local_api, "db", self.id)
                last_hedge_type = orderobj.type
                last_hedge_profit = orderobj.profit
                # if last_hedge_type == Mt5.ORDER_TYPE_BUY and last_hedge_profit < 0:
                if (len(self.recovery) > 0):
                    last_recovery = self.recovery[-1]
                    order_data_recovery_db = self.local_api.get_order_by_ticket(
                        last_recovery)
                    if (order_data_recovery_db.type == Mt5.ORDER_TYPE_BUY):
                        return
                self.close_recovery_orders()
                self.hedge_buy_order()

    def update_CT_cycle(self):
        self.local_api.Update_cycle(self.id, self.to_dict())
    #  close   cycle when hits  takeprofit

    async def close_cycle_on_takeprofit(self, take_profit, remote_api):
        self.update_CT_cycle()
        if self.total_profit >= take_profit:
            self.is_pending = False
            self.is_closed = True
            self.close_cycle(False, 0, "MetaTrader5")
            remote_api.update_CT_cycle_by_id(
                self.cycle_id, self.to_remote_dict())
