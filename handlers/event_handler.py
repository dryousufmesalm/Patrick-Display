import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum
from db.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for trading system communication"""
    # Bot Management
    BOT_CREATE = "BOT_CREATE"
    BOT_START = "BOT_START"
    BOT_STOP = "BOT_STOP"
    BOT_UPDATE_SETTINGS = "BOT_UPDATE_SETTINGS"
    BOT_STATUS_CHANGE = "BOT_STATUS_CHANGE"

    # Trading Operations
    ORDER_CREATE = "ORDER_CREATE"
    ORDER_MODIFY = "ORDER_MODIFY"
    ORDER_CLOSE = "ORDER_CLOSE"
    ORDER_EXECUTED = "ORDER_EXECUTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"

    # Cycle Management
    CYCLE_START = "CYCLE_START"
    CYCLE_CLOSE = "CYCLE_CLOSE"
    CYCLE_UPDATE = "CYCLE_UPDATE"

    # Account Management
    ACCOUNT_BALANCE_UPDATE = "ACCOUNT_BALANCE_UPDATE"
    ACCOUNT_STATUS_CHANGE = "ACCOUNT_STATUS_CHANGE"

    # System Events
    SYSTEM_ERROR = "SYSTEM_ERROR"
    SYSTEM_WARNING = "SYSTEM_WARNING"
    SYSTEM_INFO = "SYSTEM_INFO"

    # Strategy Events
    STRATEGY_UPDATE = "STRATEGY_UPDATE"
    STRATEGY_RELOAD = "STRATEGY_RELOAD"


class EventSeverity(Enum):
    """Event severity levels"""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class EventHandler:
    """
    Event handler for real-time communication with the trading system
    Uses the 'events' collection for messaging and notifications
    """

    def __init__(self, supabase_client: SupabaseClient):
        self.client = supabase_client.get_client()
        self.db_client = supabase_client
        self.events_table = "events"
        self.listeners: Dict[str, List[Callable]] = {}
        self.subscription = None
        logger.info("EventHandler initialized")

    async def send_event(
        self,
        account_id: str,
        event_type: EventType,
        content: Dict[str, Any],
        bot_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        severity: EventSeverity = EventSeverity.INFO
    ) -> str:
        """Send an event to the events table"""
        try:
            event_data = {
                "uuid": str(uuid.uuid4()),
                "account": account_id,
                "bot": bot_id,
                "strategy": strategy_id,
                "event_type": event_type.value,
                "content": content,
                "severity": severity.value,
                "created_at": datetime.utcnow().isoformat()
            }

            response = self.client.table(
                self.events_table).insert(event_data).execute()
            event_id = response.data[0]["id"]

            logger.info(
                f"Event sent: {event_type.value} for account {account_id}")
            return event_id
        except Exception as e:
            logger.error(f"Error sending event: {e}")
            raise

    async def send_bot_command(
        self,
        account_id: str,
        bot_id: str,
        command: str,
        parameters: Dict[str, Any] = None
    ) -> str:
        """Send a command to a specific bot"""
        try:
            content = {
                "command": command,
                "parameters": parameters or {},
                "timestamp": datetime.utcnow().isoformat()
            }

            event_type = EventType.BOT_UPDATE_SETTINGS
            if command == "start":
                event_type = EventType.BOT_START
            elif command == "stop":
                event_type = EventType.BOT_STOP

            return await self.send_event(
                account_id=account_id,
                bot_id=bot_id,
                event_type=event_type,
                content=content,
                severity=EventSeverity.INFO
            )
        except Exception as e:
            logger.error(f"Error sending bot command: {e}")
            raise

    async def send_order_command(
        self,
        account_id: str,
        bot_id: str,
        order_type: str,
        symbol: str,
        volume: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> str:
        """Send an order command"""
        try:
            content = {
                "order_type": order_type,
                "symbol": symbol,
                "volume": volume,
                "price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "timestamp": datetime.utcnow().isoformat()
            }

            return await self.send_event(
                account_id=account_id,
                bot_id=bot_id,
                event_type=EventType.ORDER_CREATE,
                content=content,
                severity=EventSeverity.INFO
            )
        except Exception as e:
            logger.error(f"Error sending order command: {e}")
            raise

    async def send_balance_update(
        self,
        account_id: str,
        balance: float,
        equity: float,
        margin: Optional[float] = None
    ) -> str:
        """Send account balance update event"""
        try:
            content = {
                "balance": balance,
                "equity": equity,
                "margin": margin,
                "timestamp": datetime.utcnow().isoformat()
            }

            return await self.send_event(
                account_id=account_id,
                event_type=EventType.ACCOUNT_BALANCE_UPDATE,
                content=content,
                severity=EventSeverity.INFO
            )
        except Exception as e:
            logger.error(f"Error sending balance update: {e}")
            raise

    async def send_error_event(
        self,
        account_id: str,
        error_message: str,
        bot_id: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> str:
        """Send an error event"""
        try:
            content = {
                "error_message": error_message,
                "error_code": error_code,
                "timestamp": datetime.utcnow().isoformat()
            }

            return await self.send_event(
                account_id=account_id,
                bot_id=bot_id,
                event_type=EventType.SYSTEM_ERROR,
                content=content,
                severity=EventSeverity.ERROR
            )
        except Exception as e:
            logger.error(f"Error sending error event: {e}")
            raise

    async def get_recent_events(
        self,
        account_id: Optional[str] = None,
        bot_id: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent events with optional filtering"""
        try:
            query = self.client.table(self.events_table).select(
                "*").order("created_at", desc=True).limit(limit)

            if account_id:
                query = query.eq("account", account_id)

            if bot_id:
                query = query.eq("bot", bot_id)

            if event_types:
                event_type_values = [et.value for et in event_types]
                query = query.in_("event_type", event_type_values)

            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            raise

    async def get_events_since(
        self,
        since: datetime,
        account_id: Optional[str] = None
    ) -> List[Dict]:
        """Get events since a specific timestamp"""
        try:
            query = self.client.table(self.events_table).select("*").gte(
                "created_at", since.isoformat()
            ).order("created_at", desc=False)

            if account_id:
                query = query.eq("account", account_id)

            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting events since {since}: {e}")
            raise

    def add_event_listener(self, event_type: EventType, callback: Callable[[Dict], None]):
        """Add a callback function for specific event types"""
        if event_type.value not in self.listeners:
            self.listeners[event_type.value] = []

        self.listeners[event_type.value].append(callback)
        logger.info(f"Added listener for event type: {event_type.value}")

    def remove_event_listener(self, event_type: EventType, callback: Callable[[Dict], None]):
        """Remove a callback function for specific event types"""
        if event_type.value in self.listeners:
            try:
                self.listeners[event_type.value].remove(callback)
                logger.info(
                    f"Removed listener for event type: {event_type.value}")
            except ValueError:
                logger.warning(
                    f"Callback not found for event type: {event_type.value}")

    def start_real_time_listener(self, account_id: Optional[str] = None):
        """Start listening for real-time events using Supabase subscriptions"""
        try:
            def handle_event_change(payload):
                """Handle incoming real-time events"""
                if payload['eventType'] == 'INSERT':
                    event = payload['new']
                    event_type = event.get('event_type')

                    # Call registered listeners
                    if event_type in self.listeners:
                        for callback in self.listeners[event_type]:
                            try:
                                callback(event)
                            except Exception as e:
                                logger.error(
                                    f"Error in event listener callback: {e}")

                    logger.debug(f"Received real-time event: {event_type}")

            # Set up subscription
            subscription_query = self.client.table(
                self.events_table).on('INSERT', handle_event_change)

            # Filter by account if specified
            if account_id:
                subscription_query = subscription_query.filter(
                    'account', 'eq', account_id)

            self.subscription = subscription_query.subscribe()
            logger.info(
                f"Started real-time event listener{' for account ' + account_id if account_id else ''}")
        except Exception as e:
            logger.error(f"Error starting real-time listener: {e}")
            raise

    def stop_real_time_listener(self):
        """Stop the real-time event listener"""
        if self.subscription:
            try:
                self.subscription.unsubscribe()
                self.subscription = None
                logger.info("Stopped real-time event listener")
            except Exception as e:
                logger.error(f"Error stopping real-time listener: {e}")

    async def mark_event_processed(self, event_id: str):
        """Mark an event as processed (add to content)"""
        try:
            # Get current event
            response = self.client.table(self.events_table).select(
                "content").eq("id", event_id).execute()
            if not response.data:
                return

            current_content = response.data[0]["content"] or {}
            current_content["processed"] = True
            current_content["processed_at"] = datetime.utcnow().isoformat()

            # Update event
            self.client.table(self.events_table).update({
                "content": current_content
            }).eq("id", event_id).execute()

            logger.debug(f"Marked event {event_id} as processed")
        except Exception as e:
            logger.error(f"Error marking event as processed: {e}")

    async def cleanup_old_events(self, days_to_keep: int = 30):
        """Clean up events older than specified days"""
        try:
            cutoff_date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(
                day=cutoff_date.day - days_to_keep)

            response = self.client.table(self.events_table).delete().lt(
                "created_at", cutoff_date.isoformat()
            ).execute()

            deleted_count = len(response.data) if response.data else 0
            logger.info(f"Cleaned up {deleted_count} old events")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
            raise
