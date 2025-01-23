
from sqlmodel import SQLModel, create_engine 
from typing import TYPE_CHECKING

    
sqlite_url = "sqlite:///database.db"

# Create the engine
engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    from DB.ah_strategy.models.ah_cycles import AHCycle
    from DB.ah_strategy.models.ah_cycles_orders import AhCyclesOrders
    from DB.ct_strategy.models.ct_cycles import CTCycle
    from DB.ct_strategy.models.ct_cycles_orders import CtCyclesOrders
    from DB.mt5_login.models.mt5_login import Mt5Login
    from DB.remote_login.models.remote_login import RemoteLogin
    SQLModel.metadata.create_all(engine)



create_db_and_tables()

  