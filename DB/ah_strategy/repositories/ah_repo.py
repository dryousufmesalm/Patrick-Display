"""
AdaptiveHedging Repository - Compatibility layer for Supabase
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class AHRepo:
    """
    AdaptiveHedging Repository compatibility layer
    Wraps Supabase operations to maintain compatibility with legacy code
    """

    def __init__(self, engine=None):
        """Initialize with legacy engine (compatibility)"""
        self.engine = engine
        self.supabase_service = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure Supabase service is initialized"""
        if not self._initialized:
            try:
                if self.engine and hasattr(self.engine, 'get_supabase_service'):
                    self.supabase_service = self.engine.get_supabase_service()
                else:
                    self.supabase_service = SupabaseService()
                    await self.supabase_service.initialize()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize AHRepo: {e}")

    def get_cycle_by_id(self, cycle_id: str) -> Optional[Dict]:
        """Get cycle by ID - compatibility method"""
        try:
            return asyncio.run(self._async_get_cycle_by_id(cycle_id))
        except Exception as e:
            logger.error(f"Error getting cycle {cycle_id}: {e}")
            return None

    async def _async_get_cycle_by_id(self, cycle_id: str) -> Optional[Dict]:
        """Async implementation of get_cycle_by_id"""
        await self._ensure_initialized()

        try:
            if self.supabase_service:
                result = await self.supabase_service.get_cycle_by_id(cycle_id)
                return result
        except Exception as e:
            logger.error(f"Error in async get_cycle_by_id: {e}")
        return None

    def create_cycle(self, cycle_data: Dict) -> Optional[str]:
        """Create cycle - compatibility method"""
        try:
            return asyncio.run(self._async_create_cycle(cycle_data))
        except Exception as e:
            logger.error(f"Error creating cycle: {e}")
            return None

    async def _async_create_cycle(self, cycle_data: Dict) -> Optional[str]:
        """Async implementation of create_cycle"""
        await self._ensure_initialized()

        try:
            if self.supabase_service:
                result = await self.supabase_service.create_cycle(cycle_data)
                return result.get('id') if result else None
        except Exception as e:
            logger.error(f"Error in async create_cycle: {e}")
        return None

    def update_cycle(self, cycle_id: str, cycle_data: Dict) -> bool:
        """Update cycle - compatibility method"""
        try:
            return asyncio.run(self._async_update_cycle(cycle_id, cycle_data))
        except Exception as e:
            logger.error(f"Error updating cycle {cycle_id}: {e}")
            return False

    async def _async_update_cycle(self, cycle_id: str, cycle_data: Dict) -> bool:
        """Async implementation of update_cycle"""
        await self._ensure_initialized()

        try:
            if self.supabase_service:
                result = await self.supabase_service.update_cycle(cycle_id, cycle_data)
                return result is not None
        except Exception as e:
            logger.error(f"Error in async update_cycle: {e}")
        return False

    def get_cycles_by_account(self, account_id: str) -> List[Dict]:
        """Get cycles by account - compatibility method"""
        try:
            return asyncio.run(self._async_get_cycles_by_account(account_id))
        except Exception as e:
            logger.error(f"Error getting cycles for account {account_id}: {e}")
            return []

    async def _async_get_cycles_by_account(self, account_id: str) -> List[Dict]:
        """Async implementation of get_cycles_by_account"""
        await self._ensure_initialized()

        try:
            if self.supabase_service:
                result = await self.supabase_service.get_cycles_by_account(account_id)
                return result or []
        except Exception as e:
            logger.error(f"Error in async get_cycles_by_account: {e}")
        return []
