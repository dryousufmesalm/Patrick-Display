import asyncio
from Orders.order import order
import time
import threading
from DB.db_engine import engine
from DB.ah_strategy.repositories.ah_repo import AHRepo
from DB.ct_strategy.repositories.ct_repo import CTRepo

from Views.globals.app_logger import app_logger as logger


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
        self.logger = logger

    async def get_all_mt5_orders(self):
        try:
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
        except Exception as e:
            self.logger.error(f"Error in get_all_mt5_orders: {e}")

    async def update_ah_orders_in_db(self):
        try:
            tasks = []
            for pos in self.all_mt5_orders:
                tasks.append(self.update_single_ah_order(pos))
            for db_order in self.suspious_ah_orders:
                tasks.append(self.update_single_suspicious_ah_order(db_order))
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Error in update_ah_orders_in_db: {e}")

    async def update_single_ah_order(self, pos):
        try:
            db_order = self.ah_repo.get_order_by_ticket(pos)
            if db_order:
                order_obj = order(db_order, db_order.is_pending,
                                  self.mt5, self.ah_repo, "db", db_order.cycle_id)
                order_obj.update_from_mt5()
                order_obj.check_false_closed_cycles()
                order_obj.update_order()
        except Exception as e:
            self.logger.error(f"Error in update_single_ah_order: {e}")

    async def update_single_suspicious_ah_order(self, db_order):
        try:
            is_closed = self.mt5.check_order_is_closed(db_order.ticket)
            if is_closed:
                order_obj = order(db_order, db_order.is_pending,
                                  self.mt5, self.ah_repo, "db", db_order.cycle_id)
                order_obj.is_closed = is_closed
                order_obj.update_order()
        except Exception as e:
            self.logger.error(
                f"Error in update_single_suspicious_ah_order: {e}")
        except Exception as e:
            self.logger.error(f"Error in update_ah_orders_in_db: {e}")

    async def get_all_ah_orders_in_db(self):
        try:
            orders = self.ah_repo.get_open_orders_only()
            self.all_ah_orders = [
                entry for entry in orders if entry.account == self.mt5.account_id]
            return self.all_ah_orders
        except Exception as e:
            self.logger.error(f"Error in get_all_ah_orders_in_db: {e}")

    async def get_suspicious_ah_orders_in_db(self):
        try:
            self.suspious_ah_orders = [
                order for order in self.all_ah_orders if order not in self.all_mt5_orders]
            return self.suspious_ah_orders
        except Exception as e:
            self.logger.error(f"Error in get_suspicious_ah_orders_in_db: {e}")

    async def get_false_closed_orders(self):
        try:
            if len(self.all_ah_orders) != len(self.all_mt5_orders):
                self.false_closed_orders = [
                    order for order in self.all_ah_orders if order not in self.all_mt5_orders]
        except Exception as e:
            self.logger.error(f"Error in get_false_closed_orders: {e}")

    async def update_ct_orders_in_db(self):
        try:
            tasks = []
            for pos in self.all_mt5_orders:
                tasks.append(self.update_single_ct_order(pos))
            for db_order in self.suspious_ct_orders:
                tasks.append(self.update_single_suspicious_ct_order(db_order))
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Error in update_ct_orders_in_db: {e}")

    async def update_single_ct_order(self, pos):
        try:
            db_order = self.ct_repo.get_order_by_ticket(pos)
            if db_order:
                order_obj = order(db_order, db_order.is_pending,
                                  self.mt5, self.ct_repo, "db", db_order.cycle_id)
                order_obj.update_from_mt5()
                order_obj.check_false_closed_cycles()
                order_obj.update_order()
        except Exception as e:
            self.logger.error(f"Error in update_single_ct_order: {e}")

    async def update_single_suspicious_ct_order(self, db_order):
        try:
            is_closed = self.mt5.check_order_is_closed(db_order.ticket)
            if is_closed:
                order_obj = order(db_order, db_order.is_pending,
                                  self.mt5, self.ct_repo, "db", db_order.cycle_id)
                order_obj.is_closed = is_closed
                order_obj.update_order()
        except Exception as e:
            self.logger.error(
                f"Error in update_single_suspicious_ct_order: {e}")

    async def get_all_ct_orders_in_db(self):
        try:
            orders = self.ct_repo.get_open_orders_only()
            self.all_ct_orders = [
                entry for entry in orders if entry.account == self.mt5.account_id]
            return self.all_ct_orders
        except Exception as e:
            self.logger.error(f"Error in get_all_ct_orders_in_db: {e}")

    async def get_suspicious_ct_orders_in_db(self):
        try:
            self.suspious_ct_orders = [
                order for order in self.all_ct_orders if order not in self.all_mt5_orders]
            return self.suspious_ct_orders
        except Exception as e:
            self.logger.error(f"Error in get_suspicious_ct_orders_in_db: {e}")

    async def run_orders_manager(self):
        while True:
            try:
                task1 = asyncio.create_task(self.get_all_mt5_orders())
                task2 = asyncio.create_task(self.get_all_ah_orders_in_db())
                task3 = asyncio.create_task(
                    self.get_suspicious_ah_orders_in_db())
                await asyncio.gather(task1, task2, task3)
                task4 = asyncio.create_task(self.get_all_ct_orders_in_db())
                task5 = asyncio.create_task(
                    self.get_suspicious_ct_orders_in_db())
                await asyncio.gather(task4, task5)
                await asyncio.gather(
                    self.update_ah_orders_in_db(),
                    self.update_ct_orders_in_db()
                )
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in run_orders_manager: {e}")

    async def run_in_thread(self):
        try:
            await self.run_orders_manager()
        except Exception as e:
            logger.error(f"Error starting cycles_manager: {e}")
