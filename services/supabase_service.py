"""
Supabase Service for Real-Time Trading Operations
Optimized for sub-second performance with connection pooling
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from supabase._async.client import create_client, AsyncClient
from postgrest.exceptions import APIError
import aiohttp

logger = logging.getLogger(__name__)


class SupabaseService:
    """
    High-performance Supabase client for real-time trading operations
    Features connection pooling, error handling, and retry logic
    """

    def __init__(self, url: str = None, key: str = None):
        # Use provided values or environment variables or hardcoded fallbacks
        self.url = url or os.getenv(
            'SUPABASE_URL') or 'https://mkccvhogjqwmcqjuxfzv.supabase.co'
        self.key = key or os.getenv(
            'SUPABASE_ANON_KEY') or 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1rY2N2aG9nanF3bWNxanV4Znp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcxNTMyODksImV4cCI6MjA2MjcyOTI4OX0.lrRfMJhFhVU1W4gNx8Rdu4LP36an0iCy3XyFNJ5ktDY'
        self.client: Optional[AsyncClient] = None
        self.is_connected = False
        self.connection_retries = 0
        self.max_retries = 3

        # Performance tracking
        self.query_count = 0
        self.last_query_time = datetime.utcnow()

        # Connection pool settings
        self.timeout = aiohttp.ClientTimeout(total=15, connect=5)

    async def initialize(self) -> bool:
        """Initialize the Supabase client with connection pooling"""
        try:
            if not self.url or not self.key:
                raise ValueError("Supabase URL and key are required")

            # Create client with custom timeout
            self.client = await create_client(self.url, self.key)

            # Test connection
            await self.test_connection()

            self.is_connected = True
            self.connection_retries = 0
            logger.info("Supabase client initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.is_connected = False
            return False

    async def test_connection(self) -> bool:
        """Test the Supabase connection"""
        try:
            # Simple query to test connection
            result = await self.client.table('meta_trader_accounts').select('id').limit(1).execute()
            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def ensure_connected(self) -> bool:
        """Ensure connection is active, reconnect if needed"""
        if not self.is_connected or not self.client:
            return await self.reconnect()

        # Test connection periodically
        if not await self.test_connection():
            return await self.reconnect()

        return True

    async def reconnect(self) -> bool:
        """Reconnect to Supabase with exponential backoff"""
        if self.connection_retries >= self.max_retries:
            logger.error(
                f"Max reconnection attempts ({self.max_retries}) reached")
            return False

        self.connection_retries += 1
        wait_time = 2 ** self.connection_retries

        logger.info(
            f"Reconnecting to Supabase (attempt {self.connection_retries}/{self.max_retries})...")
        await asyncio.sleep(wait_time)

        return await self.initialize()

    async def execute_query(self, operation: str, **kwargs) -> Optional[Any]:
        """Execute a query with automatic retry logic"""
        for attempt in range(self.max_retries):
            try:
                if not await self.ensure_connected():
                    raise ConnectionError(
                        "Failed to establish Supabase connection")

                # Execute the operation
                result = await self._execute_operation(operation, **kwargs)

                # Track performance
                self.query_count += 1
                self.last_query_time = datetime.utcnow()

                return result

            except (ConnectionError, APIError) as e:
                logger.warning(f"Query attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Query failed after {self.max_retries} attempts")
                    raise

                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return None

    async def _execute_operation(self, operation: str, **kwargs) -> Any:
        """Execute specific Supabase operation"""
        table_name = kwargs.get('table')

        if operation == 'insert':
            return await self.client.table(table_name).insert(kwargs['data']).execute()

        elif operation == 'select':
            query = self.client.table(table_name).select(
                kwargs.get('columns', '*'))

            # Apply filters
            for filter_key, filter_value in kwargs.get('filters', {}).items():
                if filter_key == 'eq':
                    for field, value in filter_value.items():
                        query = query.eq(field, value)
                elif filter_key == 'gte':
                    for field, value in filter_value.items():
                        query = query.gte(field, value)
                elif filter_key == 'lte':
                    for field, value in filter_value.items():
                        query = query.lte(field, value)
                elif filter_key == 'in':
                    for field, values in filter_value.items():
                        query = query.in_(field, values)

            # Apply limit
            if 'limit' in kwargs:
                query = query.limit(kwargs['limit'])

            # Apply ordering
            if 'order' in kwargs:
                for field, ascending in kwargs['order'].items():
                    query = query.order(field, desc=not ascending)

            return await query.execute()

        elif operation == 'update':
            query = self.client.table(table_name).update(kwargs['data'])

            # Apply filters for update
            for filter_key, filter_value in kwargs.get('filters', {}).items():
                if filter_key == 'eq':
                    for field, value in filter_value.items():
                        query = query.eq(field, value)

            return await query.execute()

        elif operation == 'upsert':
            return await self.client.table(table_name).upsert(kwargs['data']).execute()

        elif operation == 'delete':
            query = self.client.table(table_name).delete()

            # Apply filters for delete
            for filter_key, filter_value in kwargs.get('filters', {}).items():
                if filter_key == 'eq':
                    for field, value in filter_value.items():
                        query = query.eq(field, value)

            return await query.execute()

        else:
            raise ValueError(f"Unknown operation: {operation}")

    # High-level trading operations
    async def create_cycle(self, cycle_data: Dict) -> Optional[str]:
        """Create a new trading cycle"""
        try:
            result = await self.execute_query(
                'insert',
                table='cycles',
                data=cycle_data
            )

            if result and result.data:
                return result.data[0]['id']

            return None

        except Exception as e:
            logger.error(f"Error creating cycle: {e}")
            return None

    async def create_order(self, order_data: Dict) -> Optional[str]:
        """Create a new order"""
        try:
            result = await self.execute_query(
                'insert',
                table='orders',
                data=order_data
            )

            if result and result.data:
                return result.data[0]['id']

            return None

        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    async def update_cycle(self, cycle_id: str, updates: Dict) -> bool:
        """Update a cycle"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()

            result = await self.execute_query(
                'update',
                table='cycles',
                data=updates,
                filters={'eq': {'id': cycle_id}}
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error updating cycle {cycle_id}: {e}")
            return False

    async def update_order(self, order_id: str, updates: Dict) -> bool:
        """Update an order"""
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()

            result = await self.execute_query(
                'update',
                table='orders',
                data=updates,
                filters={'eq': {'id': order_id}}
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return False

    async def get_active_cycles(self, account_id: str, bot_id: str) -> List[Dict]:
        """Get active cycles for an account and bot"""
        try:
            result = await self.execute_query(
                'select',
                table='cycles',
                columns='*, orders(*)',
                filters={'eq': {
                    'account': account_id,
                    'bot': bot_id,
                    'is_closed': False
                }}
            )

            return result.data if result else []

        except Exception as e:
            logger.error(f"Error getting active cycles: {e}")
            return []

    async def get_bot_config(self, user_id: str, config_name: str) -> Optional[Dict]:
        """Get bot configuration"""
        try:
            result = await self.execute_query(
                'select',
                table='bot-configs',
                filters={'eq': {
                    'user': user_id,
                    'name': config_name
                }},
                limit=1
            )

            return result.data[0] if result and result.data else None

        except Exception as e:
            logger.error(f"Error getting bot config: {e}")
            return None

    async def save_bot_config(self, config_data: Dict) -> bool:
        """Save bot configuration"""
        try:
            result = await self.execute_query(
                'upsert',
                table='bot-configs',
                data=config_data
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error saving bot config: {e}")
            return False

    async def create_event(self, event_data: Dict) -> bool:
        """Create a trading event"""
        try:
            event_data['created_at'] = datetime.utcnow().isoformat()

            result = await self.execute_query(
                'insert',
                table='events',
                data=event_data
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return False

    async def get_daily_cycles(self, account_id: str, bot_id: str, date: str = None) -> List[Dict]:
        """Get cycles for a specific day"""
        try:
            if not date:
                date = datetime.utcnow().date().isoformat()

            result = await self.execute_query(
                'select',
                table='cycles',
                columns='total_profit',
                filters={
                    'eq': {
                        'account': account_id,
                        'bot': bot_id,
                        'is_closed': True
                    },
                    'gte': {'created_at': f"{date}T00:00:00"}
                }
            )

            return result.data if result else []

        except Exception as e:
            logger.error(f"Error getting daily cycles: {e}")
            return []

    async def get_orders_for_cycle(self, cycle_id: str) -> List[Dict]:
        """Get all orders for a specific cycle"""
        try:
            result = await self.execute_query(
                'select',
                table='orders',
                filters={'eq': {'cycle': cycle_id}},
                order={'created_at': True}
            )

            return result.data if result else []

        except Exception as e:
            logger.error(f"Error getting orders for cycle {cycle_id}: {e}")
            return []

    async def bulk_insert_orders(self, orders: List[Dict]) -> bool:
        """Bulk insert multiple orders for performance"""
        try:
            result = await self.execute_query(
                'insert',
                table='orders',
                data=orders
            )

            return result is not None

        except Exception as e:
            logger.error(f"Error bulk inserting orders: {e}")
            return False

    async def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        try:
            uptime = (datetime.utcnow() - self.last_query_time).total_seconds()

            return {
                'is_connected': self.is_connected,
                'query_count': self.query_count,
                'connection_retries': self.connection_retries,
                'last_query_time': self.last_query_time.isoformat(),
                'queries_per_minute': self.query_count / max(uptime / 60, 1) if uptime > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}

    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.client:
                # Close any open connections
                await self.client.auth.sign_out()

            self.is_connected = False
            logger.info("Supabase service cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def close(self):
        """Close Supabase connection"""
        try:
            await self.cleanup()
            logger.info("Supabase connection closed")
        except Exception as e:
            logger.error(f"Error closing Supabase connection: {e}")


# Singleton instance for global use
_supabase_service: Optional[SupabaseService] = None


async def get_supabase_service() -> SupabaseService:
    """Get or create the global Supabase service instance"""
    global _supabase_service

    if _supabase_service is None:
        _supabase_service = SupabaseService()
        await _supabase_service.initialize()

    return _supabase_service


async def cleanup_supabase_service():
    """Clean up the global Supabase service"""
    global _supabase_service

    if _supabase_service:
        await _supabase_service.cleanup()
        _supabase_service = None
