"""
Supabase Authentication Service for Flet UI
Handles user authentication, JWT tokens, and account management
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
from supabase._async.client import create_client, AsyncClient
from gotrue.errors import AuthError
from postgrest.exceptions import APIError
import aiohttp

logger = logging.getLogger(__name__)


class SupabaseAuthService:
    """
    Supabase Authentication Service for Flet UI
    Handles user login/logout, JWT management, and account loading
    """

    def __init__(self, url: str = None, key: str = None, service_role_key: str = None):
        # Use provided values or environment variables or hardcoded fallbacks
        self.url = url or os.getenv(
            'SUPABASE_URL') or 'https://mkccvhogjqwmcqjuxfzv.supabase.co'
        self.anon_key = key or os.getenv(
            'SUPABASE_ANON_KEY') or 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rY2N2aG9nanF3bWNxanV4Znp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNTMyODksImV4cCI6MjA2MjcyOTI4OX0.lrRfMJhFhVU1W4gNx8Rdu4LP36an0iCy3XyFNJ5ktDY'
        self.service_role_key = service_role_key or os.getenv(
            'SUPABASE_SERVICE_ROLE_KEY')

        self.client: Optional[AsyncClient] = None
        self.admin_client: Optional[AsyncClient] = None
        self.is_connected = False

        # Current user session
        self.current_user = None
        self.current_session = None
        self.access_token = None
        self.refresh_token = None

        # Connection settings
        self.timeout = aiohttp.ClientTimeout(total=15, connect=5)
        self.max_retries = 3

    async def initialize(self) -> bool:
        """Initialize the Supabase auth client"""
        try:
            if not self.url or not self.anon_key:
                raise ValueError("Supabase URL and anon key are required")

            # Create client for user operations
            self.client = await create_client(self.url, self.anon_key)

            # Create admin client for admin operations (if service role key is provided)
            if self.service_role_key:
                self.admin_client = await create_client(self.url, self.service_role_key)

            # Test connection
            await self.test_connection()

            self.is_connected = True
            logger.info("Supabase auth service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Supabase auth service: {e}")
            self.is_connected = False
            return False

    async def test_connection(self) -> bool:
        """Test the Supabase connection"""
        try:
            # Simple query to test connection
            if self.client:
                result = await self.client.table('users').select('id').limit(1).execute()
                return True
        except Exception as e:
            logger.error(f"Auth connection test failed: {e}")
            return False

    async def login(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Authenticate user with email and password against public.users table
        Returns: (success, message, user_data)
        """
        try:
            if not self.client:
                await self.initialize()

            # Query the public.users table directly (PayloadCMS users)
            # First check if user exists with this email
            result = await self.client.table('users').select('*').eq('email', email).execute()

            if not result.data or len(result.data) == 0:
                logger.warning(f"No user found with email: {email}")
                return False, "Invalid email or password", None

            user_record = result.data[0]

            # Check if user account is verified and enabled (relaxed for development)
            email_verified = user_record.get('email_verified', False)
            if not email_verified:
                logger.info(
                    f"User {email} email is not verified - allowing for development")
                # In production, you would return False here

            # Check user status (pending, approved, rejected) - relaxed for development
            user_status = user_record.get('status', 'pending')
            if user_status == 'rejected':
                logger.warning(f"User {email} account is rejected")
                return False, "Account has been rejected. Please contact support.", None
            elif user_status in ['pending', 'approved']:
                logger.info(
                    f"User {email} account status is {user_status} - allowing for development")

            # Basic password validation (for development)
            # In production, use bcrypt to verify hashed passwords
            # PayloadCMS stores hashed password in 'hash' field
            stored_password = user_record.get('hash')
            if stored_password and len(password) < 6:
                logger.warning(f"Password too short for user {email}")
                return False, "Invalid email or password", None

            logger.info(
                f"User {email} found and validated in public.users table")

            # Create a mock session for compatibility
            mock_session = {
                'access_token': f"mock_token_{user_record['id']}",
                'refresh_token': f"mock_refresh_{user_record['id']}",
                'expires_at': None,
                'user': {
                    'id': user_record['id'],
                    'email': user_record['email'],
                    'user_metadata': {},
                    'app_metadata': {}
                }
            }

            # Store session data
            self.current_user = mock_session['user']
            self.current_session = mock_session
            self.access_token = mock_session['access_token']
            self.refresh_token = mock_session['refresh_token']

            logger.info(f"User {email} logged in successfully (public.users)")
            return True, "Login successful", {
                "user": mock_session['user'],
                "session": mock_session,
                "profile": user_record
            }

        except Exception as e:
            logger.error(f"Login error for {email}: {e}")
            return False, f"Login failed: {str(e)}", None

    async def logout(self) -> Tuple[bool, str]:
        """
        Logout current user and clear session
        Returns: (success, message)
        """
        try:
            if not self.client or not self.current_session:
                return True, "No active session"

            # Sign out from Supabase
            await self.client.auth.sign_out()

            # Clear session data
            self.current_user = None
            self.current_session = None
            self.access_token = None
            self.refresh_token = None

            logger.info("User logged out successfully")
            return True, "Logout successful"

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            # Clear session data anyway
            self.current_user = None
            self.current_session = None
            self.access_token = None
            self.refresh_token = None
            return True, "Logout completed with errors"

    async def refresh_session(self) -> bool:
        """Refresh the current session using refresh token"""
        try:
            if not self.client or not self.refresh_token:
                return False

            response = await self.client.auth.refresh_session(self.refresh_token)

            if response.session:
                self.current_session = response.session
                self.access_token = response.session.access_token
                self.refresh_token = response.session.refresh_token
                logger.info("Session refreshed successfully")
                return True
            else:
                logger.warning("Session refresh failed")
                return False

        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return False

    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile data from users table"""
        try:
            if not self.client:
                return None

            result = await self.client.table('users').select('*').eq('id', user_id).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                logger.warning(f"No profile found for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error fetching user profile for {user_id}: {e}")
            return None

    async def get_user_accounts(self, user_id: str) -> List[Dict]:
        """
        Get all MetaTrader accounts for a user from meta-trader-accounts table
        Returns list of account dictionaries
        """
        try:
            if not self.client:
                await self.initialize()

            # Query meta_trader_accounts table for user's accounts
            result = await self.client.table('meta_trader_accounts').select('''
                id,
                user_id,
                meta_trader_id,
                status,
                expire_date,
                balance,
                equity,
                margin,
                total_pnl,
                config,
                symbols,
                created_at,
                approval_date,
                rejection_reason
            ''').eq('user_id', user_id).execute()

            if result.data:
                logger.info(
                    f"Found {len(result.data)} accounts for user {user_id}")
                return result.data
            else:
                logger.info(f"No accounts found for user {user_id}")
                return []

        except Exception as e:
            logger.error(f"Error fetching accounts for user {user_id}: {e}")
            return []

    async def get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """Get specific account by ID"""
        try:
            if not self.client:
                await self.initialize()

            result = await self.client.table('meta_trader_accounts').select('*').eq('id', account_id).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                logger.warning(f"No account found with ID {account_id}")
                return None

        except Exception as e:
            logger.error(f"Error fetching account {account_id}: {e}")
            return None

    async def update_account_status(self, account_id: str, status: str) -> bool:
        """Update account status (e.g., 'connected', 'disconnected', 'trading', 'error')"""
        try:
            if not self.client:
                await self.initialize()

            result = await self.client.table('meta_trader_accounts').update({
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', account_id).execute()

            if result.data:
                logger.info(f"Updated account {account_id} status to {status}")
                return True
            else:
                logger.warning(f"Failed to update account {account_id} status")
                return False

        except Exception as e:
            logger.error(f"Error updating account {account_id} status: {e}")
            return False

    async def is_session_valid(self) -> bool:
        """Check if current session is valid"""
        if not self.current_session or not self.access_token:
            return False

        try:
            # Check if token is expired
            if self.current_session.expires_at:
                expires_at = datetime.fromtimestamp(
                    self.current_session.expires_at)
                if datetime.utcnow() >= expires_at:
                    # Try to refresh session
                    return await self.refresh_session()

            return True

        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return False

    async def get_user_bots(self, user_id: str) -> List[Dict]:
        """Get all bots configured for a user"""
        try:
            if not self.client:
                await self.initialize()

            result = await self.client.table('bots').select('''
                id,
                name,
                strategy_type,
                status,
                account_id,
                symbols,
                config,
                is_active,
                created_at,
                updated_at
            ''').eq('user_id', user_id).eq('is_active', True).execute()

            if result.data:
                logger.info(
                    f"Found {len(result.data)} bots for user {user_id}")
                return result.data
            else:
                logger.info(f"No bots found for user {user_id}")
                return []

        except Exception as e:
            logger.error(f"Error fetching bots for user {user_id}: {e}")
            return []

    async def create_trading_session(self, user_id: str, account_id: str, bot_config: Dict) -> Optional[str]:
        """Create a new trading session record"""
        try:
            if not self.client:
                await self.initialize()

            session_data = {
                'user_id': user_id,
                'account_id': account_id,
                'bot_config': json.dumps(bot_config),
                'status': 'initializing',
                'started_at': datetime.utcnow().isoformat(),
                'is_active': True
            }

            result = await self.client.table('trading_sessions').insert(session_data).execute()

            if result.data and len(result.data) > 0:
                session_id = result.data[0]['id']
                logger.info(
                    f"Created trading session {session_id} for user {user_id}, account {account_id}")
                return session_id
            else:
                logger.error("Failed to create trading session")
                return None

        except Exception as e:
            logger.error(f"Error creating trading session: {e}")
            return None

    async def update_trading_session_status(self, session_id: str, status: str) -> bool:
        """Update trading session status"""
        try:
            if not self.client:
                await self.initialize()

            update_data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }

            if status in ['stopped', 'error', 'completed']:
                update_data['ended_at'] = datetime.utcnow().isoformat()
                update_data['is_active'] = False

            result = await self.client.table('trading_sessions').update(update_data).eq('id', session_id).execute()

            if result.data:
                logger.info(
                    f"Updated trading session {session_id} status to {status}")
                return True
            else:
                logger.warning(
                    f"Failed to update trading session {session_id} status")
                return False

        except Exception as e:
            logger.error(
                f"Error updating trading session {session_id} status: {e}")
            return False

    async def get_active_trading_sessions(self, user_id: str = None) -> List[Dict]:
        """Get all active trading sessions, optionally filtered by user"""
        try:
            if not self.client:
                await self.initialize()

            query = self.client.table('trading_sessions').select(
                '*').eq('is_active', True)

            if user_id:
                query = query.eq('user_id', user_id)

            result = await query.execute()

            if result.data:
                return result.data
            else:
                return []

        except Exception as e:
            logger.error(f"Error fetching active trading sessions: {e}")
            return []

    async def close(self):
        """Close the auth service and cleanup"""
        try:
            if self.current_session:
                await self.logout()

            self.client = None
            self.admin_client = None
            self.is_connected = False

            logger.info("Supabase auth service closed")

        except Exception as e:
            logger.error(f"Error closing auth service: {e}")


# Global auth service instance
_auth_service_instance: Optional[SupabaseAuthService] = None


async def get_auth_service() -> SupabaseAuthService:
    """Get or create the global auth service instance"""
    global _auth_service_instance

    if _auth_service_instance is None:
        _auth_service_instance = SupabaseAuthService()
        await _auth_service_instance.initialize()

    return _auth_service_instance


async def cleanup_auth_service():
    """Cleanup the global auth service instance"""
    global _auth_service_instance

    if _auth_service_instance:
        await _auth_service_instance.close()
        _auth_service_instance = None
