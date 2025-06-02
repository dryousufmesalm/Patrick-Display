"""
Remote Login Repository - Compatibility layer for Supabase
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from services.supabase_auth_service import SupabaseAuthService

logger = logging.getLogger(__name__)


class MockUser:
    """Mock user object for compatibility"""

    def __init__(self, username: str, password: str, user_id: str = None):
        self.username = username
        self.password = password
        self.id = user_id or username


class RemoteLoginRepo:
    """
    Remote Login Repository compatibility layer
    Wraps Supabase auth operations to maintain compatibility with legacy code
    """

    def __init__(self, engine=None):
        """Initialize with legacy engine (compatibility)"""
        self.engine = engine
        self.auth_service = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure Supabase auth service is initialized"""
        if not self._initialized:
            try:
                self.auth_service = SupabaseAuthService()
                await self.auth_service.initialize()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize RemoteLoginRepo: {e}")

    def get_All_users(self) -> List[MockUser]:
        """
        Get all users - compatibility method
        Returns mock users for legacy compatibility
        """
        try:
            # In the new system, we don't store plain passwords
            # Return empty list to prevent legacy auth from running
            logger.info(
                "Legacy get_All_users called - returning empty list for security")
            return []
        except Exception as e:
            logger.error(f"Error in get_All_users: {e}")
            return []

    def create_user(self, username: str, password: str) -> Optional[str]:
        """Create user - compatibility method"""
        try:
            return asyncio.run(self._async_create_user(username, password))
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    async def _async_create_user(self, username: str, password: str) -> Optional[str]:
        """Async implementation of create_user"""
        await self._ensure_initialized()

        try:
            if self.auth_service:
                # In Supabase, we would use sign_up instead of direct user creation
                logger.info(
                    f"Legacy create_user called for {username} - use Supabase signup instead")
                return None
        except Exception as e:
            logger.error(f"Error in async create_user: {e}")
        return None

    def get_user_by_username(self, username: str) -> Optional[MockUser]:
        """Get user by username - compatibility method"""
        try:
            return asyncio.run(self._async_get_user_by_username(username))
        except Exception as e:
            logger.error(f"Error getting user {username}: {e}")
            return None

    async def _async_get_user_by_username(self, username: str) -> Optional[MockUser]:
        """Async implementation of get_user_by_username"""
        await self._ensure_initialized()

        try:
            if self.auth_service:
                # In new system, we don't expose user data this way
                logger.info(
                    f"Legacy get_user_by_username called for {username}")
                return None
        except Exception as e:
            logger.error(f"Error in async get_user_by_username: {e}")
        return None

    def get_pb_credintials(self):
        """Legacy PocketBase credentials method for compatibility"""
        try:
            logger.warning(
                "get_pb_credintials called - PocketBase is deprecated, returning None")
            return None
        except Exception as e:
            logger.error(f"Error in get_pb_credintials: {e}")
            return None
