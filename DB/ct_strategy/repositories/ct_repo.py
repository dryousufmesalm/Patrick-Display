from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from DB.ct_strategy.models.ct_cycles import CTCycle
from DB.ct_strategy.models.ct_cycles_orders import CtCyclesOrders
from datetime import datetime


class CTRepo:
    def __init__(self, engine):
        self.engine = engine

    def get_cycle(self) -> CTCycle | None:
        with Session(self.engine) as session:
            result = session.get(CTCycle, 1)
            return result

    def get_cycle_by_id(self, id) -> CTCycle | None:
        with Session(self.engine) as session:
            result = session.get(CTCycle, id)
            return result

    def get_cycle_by_remote_id(self, remote_id) -> CTCycle | None:
        with Session(self.engine) as session:
            result = session.exec(select(CTCycle).where(
                CTCycle.remote_id == remote_id)).first()
            return result

    def get_active_cycles(self, account) -> list[CTCycle] | None:
        """
        Retrieve active cycles for a given account.

        :param account: The account to filter active cycles.
        :return: A list of active CTCycle objects or None.
        """
        with Session(self.engine) as session:
            cycles = session.exec(
                select(CTCycle).where(
                    CTCycle.is_closed == False
                )
            ).all()

            active_cycles = [
                cycle for cycle in cycles if cycle.account == account]
            return active_cycles

    def get_all_cycles(self) -> list[CTCycle] | None:
        with Session(self.engine) as session:
            result = session.exec(select(CTCycle)).all()
            return result

    def create_cycle(self, cycle_data) -> CTCycle | None:
        try:
            with Session(self.engine) as session:
                new_cycle = CTCycle(**cycle_data)
                session.add(new_cycle)
                session.commit()
                session.refresh(new_cycle)
                return new_cycle
        except SQLAlchemyError as e:
            print(f"Failed to create AH cycle: {e}")
            return None

    def Update_cycle(self, id, cycle_data) -> CTCycle | None:
        try:
            with Session(self.engine) as session:
                cycle = session.get(CTCycle, id)
                if cycle:
                    for key, value in cycle_data.items():
                        setattr(cycle, key, value)
                    session.add(cycle)
                    session.commit()
                    session.refresh(cycle)
                    return cycle
                return None
        except SQLAlchemyError as e:
            print(f"Failed to update AH cycle: {e}")
            return None

    def update_cycle_by_remote_id(self, remote_id, cycle_data) -> CTCycle | None:
        try:
            with Session(self.engine) as session:
                cycle = self.get_cycle_by_remote_id(remote_id)
                if cycle:
                    for key, value in cycle_data.items():
                        setattr(cycle, key, value)
                    session.add(cycle)
                    session.commit()
                    session.refresh(cycle)
                    return cycle
                return None
        except SQLAlchemyError as e:
            print(f"Failed to update AH cycle: {e}")
            return None

    def close_cycle(self, cycle_id) -> CTCycle | None:
        try:
            with Session(self.engine) as session:
                cycle = session.get(CTCycle, cycle_id)
                if cycle:
                    cycle.is_closed = True
                    session.add(cycle)
                    session.commit()
                    session.refresh(cycle)
                    return cycle
                return None
        except SQLAlchemyError as e:
            print(f"Failed to close AH cycle: {e}")
            return None

    def create_order(self, order_data) -> CtCyclesOrders | None:
        try:
            with Session(self.engine) as session:
                new_order = CtCyclesOrders(**order_data)
                session.add(new_order)
                session.commit()
                session.refresh(new_order)
                return new_order
        except SQLAlchemyError as e:
            print(f"Failed to create AH order: {e}")
            return None

    def close_order(self, order_id) -> CtCyclesOrders | None:
        try:
            with Session(self.engine) as session:
                order = session.get(CtCyclesOrders, order_id)
                if order:
                    order.is_closed = True
                    session.add(order)
                    session.commit()
                    session.refresh(order)
                    return order
                return None
        except SQLAlchemyError as e:
            print(f"Failed to close AH order: {e}")
            return None

    def get_order_by_ticket(self, ticket) -> CtCyclesOrders | None:
        with Session(self.engine) as session:
            result = session.exec(select(CtCyclesOrders).where(
                CtCyclesOrders.ticket == ticket)).first()
            return result

    def get_order_by_id(self, id) -> list[CtCyclesOrders] | None:
        with Session(self.engine) as session:
            result = session.get(CtCyclesOrders, id)
            return result

    def get_orders_by_cycle_id(self, cycle_id) -> list[CtCyclesOrders] | None:
        with Session(self.engine) as session:
            result = session.exec(select(CtCyclesOrders).where(
                CtCyclesOrders.cycle_id == cycle_id)).all()
            return result

    def get_open_orders_only(self) -> list[CtCyclesOrders] | None:
        with Session(self.engine) as session:
            result = session.exec(select(CtCyclesOrders).where(
                CtCyclesOrders.is_closed == False)).all()
            return result

    def get_open_pending_orders(self) -> list[CtCyclesOrders] | None:
        with Session(self.engine) as session:
            result = session.exec(select(CtCyclesOrders).where(
                CtCyclesOrders.is_pending == True and CtCyclesOrders.is_closed == False)).all()
            return result

    def get_all_orders(self) -> list[CtCyclesOrders] | None:
        with Session(self.engine) as session:
            result = session.exec(select(CtCyclesOrders)).all()
            return result

    def update_order_by_ticket(self, ticket, order_data) -> CtCyclesOrders | None:
        try:
            with Session(self.engine) as session:
                order = self.get_order_by_ticket(ticket)
                if order:
                    for key, value in order_data.items():
                        setattr(order, key, value)
                    session.add(order)
                    session.commit()
                    session.refresh(order)
                    return order
                return None
        except SQLAlchemyError as e:
            print(f"Failed to update AH order: {e}")
            return None

    def update_order_by_id(self, id, order_data) -> CtCyclesOrders | None:
        try:
            with Session(self.engine) as session:
                order = session.get(CtCyclesOrders, id)
                if order:
                    for key, value in order_data.items():
                        setattr(order, key, value)
                    session.add(order)
                    session.commit()
                    session.refresh(order)
                    return order
                return None
        except SQLAlchemyError as e:
            print(f"Failed to update AH order: {e}")
            return None
