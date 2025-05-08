from cycles.AH_cycle import cycle as AH_cycle
from cycles.CT_cycle import cycle as CTcycle
from DB.db_engine import engine
from DB.ah_strategy.repositories.ah_repo import AHRepo
from DB.ct_strategy.repositories.ct_repo import CTRepo
import time
import asyncio
from Views.globals.app_logger import app_logger as logger


class cycles_manager:
    def __init__(self, mt5, remote_api, account):
        self.mt5 = mt5
        self.ah_repo = AHRepo(engine=engine)
        self.ct_repo = CTRepo(engine=engine)
        self.remote_api = remote_api
        self.all_AH_cycles = []
        self.remote_AH_cycles = []
        self.all_CT_cycles = []
        self.remote_CT_cycles = []
        self.account = account

    def get_all_AH_active_cycles(self):
        try:
            cycles = self.ah_repo.get_active_cycles(self.account.id)
            active_cycles = [
                cycle for cycle in cycles if cycle.is_closed is False]
            return active_cycles
        except Exception as e:
            logger.error(f"Error getting all AH active cycles: {e}")
            return []

    def get_all_CT_active_cycles(self):
        try:
            cycles = self.ct_repo.get_active_cycles(self.account.id)
            active_cycles = [
                cycle for cycle in cycles if cycle.is_closed is False]
            return active_cycles
        except Exception as e:
            logger.error(f"Error getting all CT active cycles: {e}")
            return []

    def get_remote_AH_active_cycles(self):
        try:
            cycles = self.remote_api.get_all_AH_active_cycles_by_account(
                self.account.id)
            if cycles is None or len(cycles) == 0:
                return []
            active_cycles = [
                cycle for cycle in cycles if cycle.is_closed is False]
            return active_cycles
        except Exception as e:
            logger.error(f"Error getting remote AH active cycles: {e}")
            return []

    def get_remote_CT_active_cycles(self):
        try:
            cycles = self.remote_api.get_all_CT_active_cycles_by_account(
                self.account.id)
            if cycles is None or len(cycles) == 0:
                return []
            active_cycles = [
                cycle for cycle in cycles if cycle.is_closed is False]
            return active_cycles
        except Exception as e:
            logger.error(f"Error getting remote CT active cycles: {e}")
            return []

    async def run_cycles_manager(self):
        while True:
            try:
                await asyncio.gather(
                    self.sync_AH_cycles(),
                    self.sync_CT_cycles(),
                    self.fix_incorrectly_closed_cycles()
                )
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in run_cycles_manager: {e}")

    async def sync_AH_cycles(self):
        try:
            self.all_AH_cycles = self.get_all_AH_active_cycles()  # get all orders from MT5
            # get all orders from remote
            self.remote_AH_cycles = self.get_remote_AH_active_cycles()

            if self.remote_AH_cycles is None:
                logger.error("remote_AH_cycles is None")
                return

            for remote_cycle in self.remote_AH_cycles:
                try:
                    if remote_cycle is None:
                        logger.error(
                            "Found None remote_cycle in remote_AH_cycles")
                        continue

                    cycle_id = remote_cycle.id
                    if cycle_id not in [cycle.remote_id for cycle in self.all_AH_cycles]:
                        cycle_data = self.ah_repo.get_cycle_by_remote_id(
                            cycle_id)
                        if cycle_data is not None:
                            cycle_obj = AH_cycle(
                                cycle_data, self.mt5, self, "db")
                            self.remote_api.update_AH_cycle_by_id(
                                cycle_obj.cycle_id, cycle_obj.to_remote_dict())
                        if cycle_data is None:
                            try:
                                cycle_obj = AH_cycle(
                                    remote_cycle, self.mt5, self, "remote")
                                self.ah_repo.create_cycle(cycle_obj.to_dict())
                            except Exception as creation_error:
                                logger.error(
                                    f"Error creating AH cycle from remote data: {creation_error}")
                except Exception as cycle_error:
                    logger.error(
                        f"Error processing remote AH cycle: {cycle_error}")

            for cycle_data in self.all_AH_cycles:
                try:
                    if cycle_data is None:
                        logger.error("Found None cycle_data in all_AH_cycles")
                        continue

                    cycle_obj = AH_cycle(cycle_data, self.mt5, self, "db")
                    remote_id = cycle_obj.cycle_id

                    if not remote_id:
                        logger.error(
                            f"Empty remote_id for local AH cycle {cycle_data.id}")
                        continue

                    self.remote_api.update_AH_cycle_by_id(
                        remote_id, cycle_obj.to_remote_dict())
                except Exception as local_cycle_error:
                    logger.error(
                        f"Error processing local AH cycle: {local_cycle_error}")
        except Exception as e:
            logger.error(f"Error in sync_AH_cycles: {e}")

    async def sync_CT_cycles(self):
        try:
            self.all_CT_cycles = self.get_all_CT_active_cycles()

            self.remote_CT_cycles = self.get_remote_CT_active_cycles()

            if self.remote_CT_cycles is None:
                logger.error("remote_CT_cycles is None")
                return

            for remote_cycle in self.remote_CT_cycles:
                if remote_cycle is None:
                    logger.error("Found None remote_cycle in remote_CT_cycles")
                    continue

                try:
                    cycle_id = remote_cycle.id

                    if cycle_id not in [cycle.remote_id for cycle in self.all_CT_cycles]:
                        cycle_data = self.ct_repo.get_cycle_by_remote_id(
                            cycle_id)

                        if cycle_data is not None:
                            cycle_obj = CTcycle(
                                cycle_data, self.mt5, self, "db")
                            self.remote_api.update_CT_cycle_by_id(
                                cycle_obj.cycle_id, cycle_obj.to_remote_dict())
                        if cycle_data is None:
                            try:
                                cycle_obj = CTcycle(
                                    remote_cycle, self.mt5, self, "remote")
                                self.ct_repo.create_cycle(cycle_obj.to_dict())
                            except Exception as creation_error:
                                logger.error(
                                    f"Error creating cycle from remote data: {creation_error}")
                except Exception as cycle_error:
                    logger.error(
                        f"Error processing remote cycle: {cycle_error}")

            for cycle_data in self.all_CT_cycles:
                try:
                    if cycle_data is None:
                        logger.error("Found None cycle_data in all_CT_cycles")
                        continue

                    cycle_obj = CTcycle(cycle_data, self.mt5, self, "db")
                    remote_id = cycle_obj.cycle_id

                    if not remote_id:
                        logger.error(
                            f"Empty remote_id for local cycle {cycle_data.id}")
                        continue

                    remote_dict = cycle_obj.to_remote_dict()
                    self.remote_api.update_CT_cycle_by_id(
                        remote_id, remote_dict)
                except Exception as local_cycle_error:
                    logger.error(
                        f"Error processing local cycle: {local_cycle_error}")
        except Exception as e:
            logger.error(f"Error in sync_CT_cycles: {e}")

    async def fix_incorrectly_closed_cycles(self):
        """
        Check for cycles that are marked as closed but still have open orders in MT5.
        This fixes the issue where cycles are incorrectly marked as closed.
        """
        try:
            # Get all closed cycles from the last 24 hours
            time_24h_ago = int(time.time()) - (24 * 60 * 60)
            closed_ah_cycles = self.ah_repo.get_recently_closed_cycles(
                self.account.id, time_24h_ago)
            closed_ct_cycles = self.ct_repo.get_recently_closed_cycles(
                self.account.id, time_24h_ago)

            # Process AH cycles
            fixed_ah_count = 0
            for cycle_data in closed_ah_cycles:
                if await self.check_and_fix_closed_cycle(cycle_data, self.ah_repo, AH_cycle, "AH"):
                    fixed_ah_count += 1

            # Process CT cycles
            fixed_ct_count = 0
            for cycle_data in closed_ct_cycles:
                if await self.check_and_fix_closed_cycle(cycle_data, self.ct_repo, CTcycle, "CT"):
                    fixed_ct_count += 1

            if fixed_ah_count > 0 or fixed_ct_count > 0:
                logger.info(
                    f"Fixed {fixed_ah_count} AH cycles and {fixed_ct_count} CT cycles incorrectly marked as closed")
        except Exception as e:
            logger.error(f"Error in fix_incorrectly_closed_cycles: {e}")

    async def check_and_fix_closed_cycle(self, cycle_data, repo, cycle_class, cycle_type):
        """
        Check if a cycle still has open orders in MT5 and fix its status if needed.

        Args:
            cycle_data: The cycle data from the database
            repo: The repository for the cycle type (AH or CT)
            cycle_class: The cycle class to instantiate
            cycle_type: A string indicating the cycle type ("AH" or "CT")

        Returns:
            bool: True if the cycle was fixed, False otherwise
        """
        try:
            # Create cycle object
            cycle_obj = cycle_class(cycle_data, self.mt5, self, "db")

            # Get all order tickets from this cycle
            all_cycle_orders = cycle_obj.combine_orders()

            # Check if any orders are still open in MT5
            still_open = False
            for ticket in all_cycle_orders:
                # Check if the order is still open in MT5
                position = self.mt5.get_position_by_ticket(ticket=ticket)
                if position and len(position) > 0:
                    logger.warning(
                        f"Found open position {ticket} in MT5 for closed {cycle_type} cycle {cycle_data.id}")
                    still_open = True
                    break

                # Also check pending orders
                pending = self.mt5.get_order_by_ticket(ticket=ticket)
                if pending and len(pending) > 0:
                    logger.warning(
                        f"Found pending order {ticket} in MT5 for closed {cycle_type} cycle {cycle_data.id}")
                    still_open = True
                    break

            # If we found open orders, update the cycle status
            if still_open:
                logger.info(
                    f"Fixing {cycle_type} cycle {cycle_data.id} incorrectly marked as closed")

                # Reopen the cycle
                cycle_obj.is_closed = False
                cycle_obj.status = "open"  # Reset status to open

                # Update in database
                repo.Update_cycle(cycle_data.id, cycle_obj.to_dict())

                # Update in remote API if it has a remote ID
                if cycle_obj.cycle_id:
                    if cycle_type == "AH":
                        self.remote_api.update_AH_cycle_by_id(
                            cycle_obj.cycle_id, cycle_obj.to_remote_dict())
                    else:
                        self.remote_api.update_CT_cycle_by_id(
                            cycle_obj.cycle_id, cycle_obj.to_remote_dict())

                return True

            return False
        except Exception as e:
            logger.error(f"Error checking cycle {cycle_data.id}: {e}")
            return False

    async def run_in_thread(self):
        try:
            await self.run_cycles_manager()
        except Exception as e:
            logger.error(f"Error starting cycles_manager: {e}")
