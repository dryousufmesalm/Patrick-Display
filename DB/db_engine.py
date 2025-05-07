from DB.ah_strategy.models.ah_cycles_orders import AhCyclesOrders
from DB.ah_strategy.models.ah_cycles import AHCycle
from DB.ct_strategy.models.ct_config import CTConfig
from DB.ct_strategy.models.ct_cycles_orders import CtCyclesOrders
from DB.ct_strategy.models.ct_cycles import CTCycle
from DB.mt5_login.models.mt5_login import Mt5Login
from DB.remote_login.models.remote_login import RemoteLogin
from sqlmodel import SQLModel, create_engine
from typing import TYPE_CHECKING
import os
import logging
from sqlmodel import create_engine, SQLModel, Session
from typing import Dict, List
from sqlmodel import create_engine, SQLModel, Session, Field, Column, JSON, select
import uuid
from dotenv import load_dotenv
from datetime import datetime
from os import path

logger = logging.getLogger(__name__)

load_dotenv()

# Import db models

# Create the database file path
db_path = os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), 'database.db')

# db connection string
sqlite_url = f"sqlite:///{db_path}"

# Create the engine
engine = create_engine(sqlite_url, echo=False)

# Create the db tables


def create_db_and_tables():
    # Create all tables based on the models
    SQLModel.metadata.create_all(engine)

    # After creating tables, run migrations if database file exists
    if os.path.exists(db_path):
        logger.info("Running database migrations...")
        try:
            # Import and run the migration script
            from DB.migrate_ct_cycles import migrate_ct_cycles
            migrate_ct_cycles()

            # Run the CT config migration
            from DB.migrate_ct_config import run_migration
            run_migration()

            logger.info("Database migrations completed successfully.")
        except Exception as e:
            logger.error(f"Error running database migrations: {e}")

# Connect to the db


def get_session():
    """Get a session to the db"""
    with Session(engine) as session:
        yield session


create_db_and_tables()
