"""
Supabase Authentication Module for Flet UI
Handles email/password authentication with the same Supabase instance as the website
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
import functools

from Views.globals.app_logger import app_logger
from services.supabase_auth_service import SupabaseAuthService
from helpers.store import store
from helpers.actions_creators import add_user, add_account

logger = logging.getLogger(__name__)

# Global auth service instance
_auth_service: Optional[SupabaseAuthService] = None


async def get_auth_service() -> SupabaseAuthService:
    """Get or create the global auth service instance"""
    global _auth_service

    if _auth_service is None:
        _auth_service = SupabaseAuthService()
        await _auth_service.initialize()

    return _auth_service


def run_async_safely(async_func):
    """
    Wrapper to run async functions safely in Flet context
    Creates a new event loop in a separate thread if needed
    """
    @functools.wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            # Try to check if there's a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we get here, there's a running loop, so we need to use a thread

                def run_in_thread():
                    # Create a new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(async_func(*args, **kwargs))
                    finally:
                        new_loop.close()

                with ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=30)  # 30 second timeout

            except RuntimeError:
                # No running event loop, safe to run directly
                return asyncio.run(async_func(*args, **kwargs))

        except Exception as e:
            logger.error(f"Error in async wrapper: {e}")
            return None
    return wrapper


async def login(email: str, password: str) -> Tuple[bool, str]:
    """
    Login function using email and password (not username)

    Args:
        email: User's email address
        password: User's password

    Returns:
        tuple[bool, str]: (success_status, message)
    """
    try:
        auth_service = await get_auth_service()

        # Use email authentication
        success, message, user_data = await auth_service.login(email, password)

        if success:
            app_logger.info(f"Login successful for email: {email}")
            return True, "Login successful"
        else:
            app_logger.error(f"Login failed for email: {email} - {message}")
            return False, message

    except Exception as e:
        app_logger.error(f"Login error for email {email}: {e}")
        return False, "Login failed due to system error"


# Add a sync version of login for Flet compatibility
def login_sync(email: str, password: str) -> Tuple[bool, str]:
    """
    Synchronous wrapper for login function that works better with Flet
    """
    try:
        @run_async_safely
        async def _login():
            return await login(email, password)

        result = _login()
        if result:
            return result
        else:
            return False, "Login failed due to system error"
    except Exception as e:
        app_logger.error(f"Sync login error: {e}")
        return False, f"Login failed: {str(e)}"


async def logout() -> Tuple[bool, str]:
    """
    Logout current user

    Returns:
        tuple[bool, str]: (success_status, message)
    """
    try:
        auth_service = await get_auth_service()
        success, message = await auth_service.logout()

        if success:
            app_logger.info("User logged out successfully")
        else:
            app_logger.error(f"Logout failed: {message}")

        return success, message

    except Exception as e:
        app_logger.error(f"Logout error: {e}")
        return False, "Logout failed"


async def is_authenticated() -> bool:
    """
    Check if user is currently authenticated

    Returns:
        bool: True if authenticated, False otherwise
    """
    try:
        auth_service = await get_auth_service()
        return await auth_service.is_session_valid()

    except Exception as e:
        app_logger.error(f"Authentication check error: {e}")
        return False


async def get_current_user() -> Optional[Dict]:
    """
    Get current authenticated user data

    Returns:
        Optional[Dict]: User data if authenticated, None otherwise
    """
    try:
        auth_service = await get_auth_service()

        if auth_service.current_user:
            return {
                "id": auth_service.current_user["id"],
                "email": auth_service.current_user["email"],
                "user_metadata": auth_service.current_user.get("user_metadata", {}),
                "app_metadata": auth_service.current_user.get("app_metadata", {}),
            }

        return None

    except Exception as e:
        app_logger.error(f"Get current user error: {e}")
        return None


async def get_current_user_id() -> Optional[str]:
    """
    Get current authenticated user ID

    Returns:
        Optional[str]: User ID if authenticated, None otherwise
    """
    try:
        auth_service = await get_auth_service()

        if auth_service.current_user:
            return auth_service.current_user["id"]

        return None

    except Exception as e:
        app_logger.error(f"Get current user ID error: {e}")
        return None


async def get_user_accounts(user_id: str) -> List[Dict]:
    """
    Get MetaTrader accounts for a user

    Args:
        user_id: User's ID

    Returns:
        List[Dict]: List of user's MetaTrader accounts
    """
    try:
        auth_service = await get_auth_service()
        return await auth_service.get_user_accounts(user_id)

    except Exception as e:
        app_logger.error(f"Get user accounts error for user {user_id}: {e}")
        return []


async def get_user_bots(user_id: str) -> List[Dict]:
    """
    Get trading bots for a user

    Args:
        user_id: User's ID

    Returns:
        List[Dict]: List of user's trading bots
    """
    try:
        auth_service = await get_auth_service()
        return await auth_service.get_user_bots(user_id)

    except Exception as e:
        app_logger.error(f"Get user bots error for user {user_id}: {e}")
        return []


async def refresh_session() -> bool:
    """
    Refresh the current session

    Returns:
        bool: True if refresh successful, False otherwise
    """
    try:
        auth_service = await get_auth_service()
        return await auth_service.refresh_session()

    except Exception as e:
        app_logger.error(f"Session refresh error: {e}")
        return False


async def cleanup_auth():
    """Cleanup authentication service"""
    global _auth_service

    try:
        if _auth_service:
            await _auth_service.close()
            _auth_service = None
            app_logger.info("Auth service cleanup completed")

    except Exception as e:
        app_logger.error(f"Auth cleanup error: {e}")

# Legacy compatibility functions (for gradual migration)


async def login_legacy(username: str, password: str) -> Tuple[bool, str]:
    """
    Legacy login function for backward compatibility
    Assumes username is actually an email

    Args:
        username: Actually the email address
        password: User's password

    Returns:
        tuple[bool, str]: (success_status, message)
    """
    app_logger.warning(
        "Using legacy login function - consider updating to use login() with email parameter")
    return await login(username, password)  # Treat username as email


class SupabaseAuthManager:
    """
    Supabase Authentication Manager for Flet UI
    Handles all authentication operations using Supabase
    """

    def __init__(self):
        self.auth_service = None
        self.current_user = None
        self.user_accounts = []

    async def initialize(self):
        """Initialize the Supabase auth service"""
        try:
            self.auth_service = await get_auth_service()
            app_logger.info("Supabase auth manager initialized successfully")
            return True
        except Exception as e:
            app_logger.error(
                f"Failed to initialize Supabase auth manager: {e}")
            return False

    async def get_user_accounts(self, user_id: str) -> List[Dict]:
        """Get all accounts for a user"""
        try:
            if not self.auth_service:
                await self.initialize()

            accounts = await self.auth_service.get_user_accounts(user_id)
            return accounts

        except Exception as e:
            app_logger.error(
                f"Error fetching accounts for user {user_id}: {e}")
            return []

    async def get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """Get account by ID"""
        try:
            if not self.auth_service:
                await self.initialize()

            account = await self.auth_service.get_account_by_id(account_id)
            return account

        except Exception as e:
            app_logger.error(f"Error fetching account {account_id}: {e}")
            return None

    async def get_user_bots(self, user_id: str) -> List[Dict]:
        """Get all bots for a user"""
        try:
            if not self.auth_service:
                await self.initialize()

            bots = await self.auth_service.get_user_bots(user_id)
            return bots

        except Exception as e:
            app_logger.error(f"Error fetching bots for user {user_id}: {e}")
            return []

    async def update_account_status(self, account_id: str, status: str) -> bool:
        """Update account status"""
        try:
            if not self.auth_service:
                await self.initialize()

            success = await self.auth_service.update_account_status(account_id, status)
            return success

        except Exception as e:
            app_logger.error(
                f"Error updating account {account_id} status: {e}")
            return False

    async def create_trading_session(self, user_id: str, account_id: str, bot_config: Dict) -> Optional[str]:
        """Create a new trading session"""
        try:
            if not self.auth_service:
                await self.initialize()

            session_id = await self.auth_service.create_trading_session(user_id, account_id, bot_config)
            return session_id

        except Exception as e:
            app_logger.error(f"Error creating trading session: {e}")
            return None

    async def update_trading_session_status(self, session_id: str, status: str) -> bool:
        """Update trading session status"""
        try:
            if not self.auth_service:
                await self.initialize()

            success = await self.auth_service.update_trading_session_status(session_id, status)
            return success

        except Exception as e:
            app_logger.error(
                f"Error updating trading session {session_id} status: {e}")
            return False

    async def get_active_trading_sessions(self, user_id: str = None) -> List[Dict]:
        """Get active trading sessions"""
        try:
            if not self.auth_service:
                await self.initialize()

            sessions = await self.auth_service.get_active_trading_sessions(user_id)
            return sessions

        except Exception as e:
            app_logger.error(f"Error fetching trading sessions: {e}")
            return []

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.current_user is not None and self.auth_service is not None

    async def is_session_valid(self) -> bool:
        """Check if current session is valid"""
        try:
            if not self.auth_service or not self.current_user:
                return False

            return await self.auth_service.is_session_valid()

        except Exception as e:
            app_logger.error(f"Error checking session validity: {e}")
            return False

    def get_current_user(self) -> Optional[Dict]:
        """Get current user data"""
        return self.current_user

    def get_user_id(self) -> Optional[str]:
        """Get current user ID"""
        if self.current_user:
            # current_user is already the user object, not a container with 'user' key
            if isinstance(self.current_user, dict) and 'id' in self.current_user:
                return self.current_user['id']
        return None

    async def close(self):
        """Close the auth manager"""
        try:
            if self.auth_service:
                await self.auth_service.close()

            self.current_user = None
            self.user_accounts = []

            app_logger.info("Supabase auth manager closed")

        except Exception as e:
            app_logger.error(f"Error closing auth manager: {e}")


# Global auth manager instance
_auth_manager: Optional[SupabaseAuthManager] = None


async def get_auth_manager() -> SupabaseAuthManager:
    """Get or create the global auth manager instance"""
    global _auth_manager

    if _auth_manager is None:
        _auth_manager = SupabaseAuthManager()
        await _auth_manager.initialize()

    return _auth_manager


async def get_account_by_id(account_id: str) -> Optional[Dict]:
    """Get account by ID"""
    try:
        auth_manager = await get_auth_manager()
        return await auth_manager.get_account_by_id(account_id)

    except Exception as e:
        app_logger.error(f"Error fetching account: {e}")
        return None


async def update_account_status(account_id: str, status: str) -> bool:
    """Update account status"""
    try:
        auth_manager = await get_auth_manager()
        return await auth_manager.update_account_status(account_id, status)

    except Exception as e:
        app_logger.error(f"Error updating account status: {e}")
        return False


# Account and session management functions
async def create_trading_session(user_id: str, account_id: str, strategies: List[str], config: Dict = None) -> Optional[str]:
    """Create a new trading session with selected strategies"""
    try:
        auth_manager = await get_auth_manager()

        bot_config = {
            'strategies': strategies,
            'config': config or {},
            'created_at': datetime.utcnow().isoformat()
        }

        session_id = await auth_manager.create_trading_session(user_id, account_id, bot_config)
        return session_id

    except Exception as e:
        app_logger.error(f"Error creating trading session: {e}")
        return None


async def update_trading_session_status(session_id: str, status: str) -> bool:
    """Update trading session status"""
    try:
        auth_manager = await get_auth_manager()
        return await auth_manager.update_trading_session_status(session_id, status)

    except Exception as e:
        app_logger.error(f"Error updating session status: {e}")
        return False


async def get_active_trading_sessions(user_id: str = None) -> List[Dict]:
    """Get active trading sessions"""
    try:
        auth_manager = await get_auth_manager()
        return await auth_manager.get_active_trading_sessions(user_id)

    except Exception as e:
        app_logger.error(f"Error fetching trading sessions: {e}")
        return []
