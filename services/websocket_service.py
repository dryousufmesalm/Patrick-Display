"""
Real-Time WebSocket Service for Trading Updates
Provides live data streaming to frontend applications
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
import uuid
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class WebSocketMessage:
    """WebSocket message structure"""

    def __init__(self, message_type: str, data: Any, timestamp: datetime = None):
        self.id = str(uuid.uuid4())
        self.type = message_type
        self.data = data
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.type,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class TradingWebSocketService:
    """
    Real-time WebSocket service for trading data
    Manages connections and broadcasts trading updates
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.is_running = False

        # Connection management
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        # user_id -> connection_ids
        self.user_connections: Dict[str, Set[str]] = {}
        # account_id -> connection_ids
        self.account_connections: Dict[str, Set[str]] = {}

        # Message queues
        self.message_queue = asyncio.Queue()
        self.broadcast_queue = asyncio.Queue()

        # Statistics
        self.messages_sent = 0
        self.connections_count = 0
        self.start_time = datetime.utcnow()

    async def start_server(self):
        """Start the WebSocket server"""
        try:
            logger.info(
                f"Starting WebSocket server on {self.host}:{self.port}")

            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )

            self.is_running = True

            # Start message processing tasks
            await asyncio.gather(
                self.process_message_queue(),
                self.process_broadcast_queue()
            )

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise

    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        self.connections_count += 1

        logger.info(f"New WebSocket connection: {connection_id}")

        try:
            # Send welcome message
            welcome_msg = WebSocketMessage("connection", {
                "status": "connected",
                "connection_id": connection_id,
                "server_time": datetime.utcnow().isoformat()
            })
            await self.send_to_connection(connection_id, welcome_msg)

            # Handle incoming messages
            async for message in websocket:
                await self.handle_message(connection_id, message)

        except ConnectionClosed:
            logger.info(f"WebSocket connection closed: {connection_id}")
        except WebSocketException as e:
            logger.warning(f"WebSocket error for {connection_id}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error in connection {connection_id}: {e}")
        finally:
            await self.remove_connection(connection_id)

    async def handle_message(self, connection_id: str, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            message_type = data.get('type')

            if message_type == 'auth':
                await self.handle_auth_message(connection_id, data)
            elif message_type == 'subscribe':
                await self.handle_subscribe_message(connection_id, data)
            elif message_type == 'unsubscribe':
                await self.handle_unsubscribe_message(connection_id, data)
            elif message_type == 'ping':
                await self.handle_ping_message(connection_id, data)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from connection {connection_id}")
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")

    async def handle_auth_message(self, connection_id: str, data: Dict):
        """Handle authentication message"""
        try:
            user_id = data.get('user_id')
            account_id = data.get('account_id')
            token = data.get('token')

            # TODO: Implement proper token validation
            # For now, accept all auth requests

            # Associate connection with user and account
            if user_id:
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)

            if account_id:
                if account_id not in self.account_connections:
                    self.account_connections[account_id] = set()
                self.account_connections[account_id].add(connection_id)

            # Send auth success
            auth_msg = WebSocketMessage("auth_result", {
                "status": "success",
                "user_id": user_id,
                "account_id": account_id
            })
            await self.send_to_connection(connection_id, auth_msg)

            logger.info(
                f"Connection {connection_id} authenticated for user {user_id}, account {account_id}")

        except Exception as e:
            logger.error(f"Error in auth handling: {e}")
            auth_msg = WebSocketMessage("auth_result", {
                "status": "error",
                "message": str(e)
            })
            await self.send_to_connection(connection_id, auth_msg)

    async def handle_subscribe_message(self, connection_id: str, data: Dict):
        """Handle subscription message"""
        try:
            channels = data.get('channels', [])

            # TODO: Implement channel subscription logic
            # For now, acknowledge all subscriptions

            sub_msg = WebSocketMessage("subscription_result", {
                "status": "success",
                "channels": channels
            })
            await self.send_to_connection(connection_id, sub_msg)

        except Exception as e:
            logger.error(f"Error in subscription handling: {e}")

    async def handle_unsubscribe_message(self, connection_id: str, data: Dict):
        """Handle unsubscription message"""
        try:
            channels = data.get('channels', [])

            # TODO: Implement channel unsubscription logic

            unsub_msg = WebSocketMessage("unsubscription_result", {
                "status": "success",
                "channels": channels
            })
            await self.send_to_connection(connection_id, unsub_msg)

        except Exception as e:
            logger.error(f"Error in unsubscription handling: {e}")

    async def handle_ping_message(self, connection_id: str, data: Dict):
        """Handle ping message"""
        pong_msg = WebSocketMessage("pong", {
            "timestamp": datetime.utcnow().isoformat()
        })
        await self.send_to_connection(connection_id, pong_msg)

    async def remove_connection(self, connection_id: str):
        """Remove connection and clean up associations"""
        try:
            # Remove from connections
            if connection_id in self.connections:
                del self.connections[connection_id]

            # Remove from user connections
            for user_id, conn_set in self.user_connections.items():
                conn_set.discard(connection_id)

            # Remove from account connections
            for account_id, conn_set in self.account_connections.items():
                conn_set.discard(connection_id)

            # Clean up empty sets
            self.user_connections = {k: v for k,
                                     v in self.user_connections.items() if v}
            self.account_connections = {
                k: v for k, v in self.account_connections.items() if v}

            logger.info(f"Connection {connection_id} removed and cleaned up")

        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {e}")

    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to specific connection"""
        try:
            if connection_id in self.connections:
                websocket = self.connections[connection_id]
                await websocket.send(message.to_json())
                self.messages_sent += 1
                return True
            return False

        except ConnectionClosed:
            await self.remove_connection(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to connection {connection_id}: {e}")
            return False

    async def broadcast_to_user(self, user_id: str, message: WebSocketMessage):
        """Broadcast message to all connections for a user"""
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])
            tasks = [self.send_to_connection(
                conn_id, message) for conn_id in connection_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return sum(1 for result in results if result is True)
        return 0

    async def broadcast_to_account(self, account_id: str, message: WebSocketMessage):
        """Broadcast message to all connections for an account"""
        if account_id in self.account_connections:
            connection_ids = list(self.account_connections[account_id])
            tasks = [self.send_to_connection(
                conn_id, message) for conn_id in connection_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return sum(1 for result in results if result is True)
        return 0

    async def broadcast_to_all(self, message: WebSocketMessage):
        """Broadcast message to all connections"""
        connection_ids = list(self.connections.keys())
        tasks = [self.send_to_connection(conn_id, message)
                 for conn_id in connection_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for result in results if result is True)

    async def process_message_queue(self):
        """Process queued messages"""
        while self.is_running:
            try:
                message_data = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                message_type = message_data.get('type')
                target = message_data.get('target')
                message = message_data.get('message')

                if message_type == 'user':
                    await self.broadcast_to_user(target, message)
                elif message_type == 'account':
                    await self.broadcast_to_account(target, message)
                elif message_type == 'all':
                    await self.broadcast_to_all(message)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")

    async def process_broadcast_queue(self):
        """Process broadcast queue"""
        while self.is_running:
            try:
                broadcast_data = await asyncio.wait_for(self.broadcast_queue.get(), timeout=1.0)
                await self.broadcast_to_all(broadcast_data)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing broadcast queue: {e}")

    # Public API methods for trading system integration

    async def send_order_update(self, account_id: str, order_data: Dict):
        """Send order update to account subscribers"""
        message = WebSocketMessage("order_update", order_data)
        await self.broadcast_to_account(account_id, message)

    async def send_cycle_update(self, account_id: str, cycle_data: Dict):
        """Send cycle update to account subscribers"""
        message = WebSocketMessage("cycle_update", cycle_data)
        await self.broadcast_to_account(account_id, message)

    async def send_trade_execution(self, account_id: str, trade_data: Dict):
        """Send trade execution notification"""
        message = WebSocketMessage("trade_execution", trade_data)
        await self.broadcast_to_account(account_id, message)

    async def send_account_balance(self, account_id: str, balance_data: Dict):
        """Send account balance update"""
        message = WebSocketMessage("account_balance", balance_data)
        await self.broadcast_to_account(account_id, message)

    async def send_system_status(self, status_data: Dict):
        """Send system status to all connected clients"""
        message = WebSocketMessage("system_status", status_data)
        await self.broadcast_to_all(message)

    async def send_error_notification(self, account_id: str, error_data: Dict):
        """Send error notification to account subscribers"""
        message = WebSocketMessage("error", error_data)
        await self.broadcast_to_account(account_id, message)

    def get_stats(self) -> Dict:
        """Get service statistics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            'is_running': self.is_running,
            'connections_count': len(self.connections),
            'users_connected': len(self.user_connections),
            'accounts_monitored': len(self.account_connections),
            'messages_sent': self.messages_sent,
            'uptime_seconds': uptime,
            'messages_per_minute': (self.messages_sent / (uptime / 60)) if uptime > 0 else 0
        }

    async def stop_server(self):
        """Stop the WebSocket server"""
        try:
            self.is_running = False

            if self.server:
                self.server.close()
                await self.server.wait_closed()

            # Close all connections
            for connection in self.connections.values():
                await connection.close()

            self.connections.clear()
            self.user_connections.clear()
            self.account_connections.clear()

            logger.info("WebSocket server stopped")

        except Exception as e:
            logger.error(f"Error stopping WebSocket server: {e}")


# Global instance
_websocket_service: Optional[TradingWebSocketService] = None


async def get_websocket_service() -> TradingWebSocketService:
    """Get or create the global WebSocket service instance"""
    global _websocket_service

    if _websocket_service is None:
        _websocket_service = TradingWebSocketService()

    return _websocket_service


async def start_websocket_service(host: str = "localhost", port: int = 8765):
    """Start the global WebSocket service"""
    service = await get_websocket_service()
    service.host = host
    service.port = port
    await service.start_server()


async def stop_websocket_service():
    """Stop the global WebSocket service"""
    global _websocket_service

    if _websocket_service:
        await _websocket_service.stop_server()
        _websocket_service = None
