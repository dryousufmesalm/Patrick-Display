"""
Database engine compatibility layer
Provides compatibility for the old SQLAlchemy engine while using Supabase
"""

import logging
from typing import Any
from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class CompatibilityEngine:
    """Compatibility wrapper for database engine operations"""

    def __init__(self):
        self.supabase_service = None
        self.is_initialized = False

    async def initialize(self):
        """Initialize the Supabase service"""
        try:
            self.supabase_service = SupabaseService()
            await self.supabase_service.initialize()
            self.is_initialized = True
            logger.info("Compatibility engine initialized with Supabase")
        except Exception as e:
            logger.error(f"Failed to initialize compatibility engine: {e}")

    def get_supabase_service(self):
        """Get the underlying Supabase service"""
        return self.supabase_service


# Global engine instance for compatibility
engine = CompatibilityEngine()


def create_db_and_tables():
    """
    Compatibility function for database initialization
    In the new system, this ensures Supabase connection is ready
    """
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(engine.initialize())
        logger.info("Database and tables creation completed (Supabase)")
        return True
    except Exception as e:
        logger.error(f"Error in create_db_and_tables: {e}")
        return False
