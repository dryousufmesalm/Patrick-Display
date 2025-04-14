from sqlmodel import SQLModel, create_engine
from typing import TYPE_CHECKING
import os
import logging

logger = logging.getLogger(__name__)

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

    # Create all tables based on the models
    SQLModel.metadata.create_all(engine)

    # After creating tables, run migrations if database file exists
    db_path = os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))), 'database.db')
    if os.path.exists(db_path):
        logger.info("Running database migrations...")
        try:
            # Import and run the migration script
            from DB.migrate_ct_cycles import migrate_ct_cycles
            migrate_ct_cycles()
            logger.info("Database migrations completed successfully.")
        except Exception as e:
            logger.error(f"Error running database migrations: {e}")


create_db_and_tables()
