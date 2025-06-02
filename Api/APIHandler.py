"""
Compatibility layer for legacy PocketBase API
This wraps the new SupabaseAuthService to maintain compatibility with existing code
"""

import asyncio
from typing import Optional, Dict, Any
from services.supabase_auth_service import SupabaseAuthService
from Views.globals.app_logger import app_logger


class API:
    """
    Compatibility wrapper for the old PocketBase API
    Now uses SupabaseAuthService under the hood
    """

    def __init__(self, pb_url: str = None):
        """Initialize the API wrapper"""
        self.pb_url = pb_url  # Keep for compatibility, but not used
        self.auth_service = None
        self.current_user_data = None
        self.is_authenticated = False

    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Login compatibility method - now uses Supabase
        Note: Legacy compatibility - returns None to prevent blocking
        """
        try:
            app_logger.warning(
                f"Legacy API.login() called with {username} - this is deprecated")
            app_logger.info(
                "Use Views.auth.supabase_auth.login() for proper async authentication")

            # Legacy code expects this to return user data immediately,
            # but we can't block in Flet's async environment
            # Return None to indicate login should be handled elsewhere
            return None

        except Exception as e:
            app_logger.error(f"API login error: {e}")
            return None

    async def _async_login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Async login implementation using Supabase"""
        try:
            if not self.auth_service:
                self.auth_service = SupabaseAuthService()
                await self.auth_service.initialize()

            success, message, user_data = await self.auth_service.login(email, password)

            if success and user_data:
                self.current_user_data = user_data
                self.is_authenticated = True

                # Return in format expected by legacy code
                return {
                    'id': user_data['user'].id,
                    'email': user_data['user'].email,
                    'token': user_data['session'].access_token,
                    'profile': user_data.get('profile', {}),
                    'user': user_data['user'],
                    'session': user_data['session']
                }
            else:
                app_logger.error(f"Supabase login failed: {message}")
                return None

        except Exception as e:
            app_logger.error(f"Async login error: {e}")
            return None

    def logout(self) -> bool:
        """Logout compatibility method"""
        try:
            app_logger.warning(
                "Legacy API.logout() called - this is deprecated")
            app_logger.info(
                "Use Views.auth.supabase_auth.logout() for proper async authentication")

            # Clear local state for compatibility
            self.current_user_data = None
            self.is_authenticated = False
            return True
        except Exception as e:
            app_logger.error(f"API logout error: {e}")
            return False

    def get_user_accounts(self, user_id: str = None) -> list:
        """Get user accounts - compatibility method"""
        try:
            app_logger.warning(
                "Legacy API.get_user_accounts() called - this is deprecated")
            app_logger.info(
                "Use Views.auth.supabase_auth.get_user_accounts() for proper async functionality")

            # Return empty list for compatibility
            return []

        except Exception as e:
            app_logger.error(f"Error getting user accounts: {e}")
            return []

    def get_current_user(self) -> Optional[Dict]:
        """Get current user data"""
        return self.current_user_data

    def is_auth_valid(self) -> bool:
        """Check if authentication is valid"""
        try:
            app_logger.warning(
                "Legacy API.is_auth_valid() called - this is deprecated")

            # Return False to encourage proper authentication flow
            return False
        except Exception as e:
            app_logger.error(f"Error checking auth validity: {e}")
            return False


# Legacy compatibility - some code might import this directly
APIHandler = API
