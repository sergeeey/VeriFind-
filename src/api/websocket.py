"""
WebSocket endpoint for real-time query updates.

Week 9 Day 5: WebSocket Backend Implementation

Features:
- Real-time query status updates
- Connection management (reconnect, heartbeat)
- Subscribe/unsubscribe to specific query IDs
- Broadcast updates to all subscribers
- Connection pooling and cleanup

Protocol:
    Client → Server:
        {"action": "subscribe", "query_id": "abc123"}
        {"action": "unsubscribe", "query_id": "abc123"}
        {"action": "ping"}

    Server → Client:
        {"type": "status", "query_id": "abc123", "status": "running", "progress": 0.5}
        {"type": "complete", "query_id": "abc123", "result": {...}}
        {"type": "error", "query_id": "abc123", "error": "..."}
        {"type": "pong"}
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


# ============================================================================
# WebSocket Message Types
# ============================================================================

@dataclass
class WSMessage:
    """Base WebSocket message."""
    type: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self))


@dataclass
class StatusMessage(WSMessage):
    """Query status update message."""
    type: str = "status"
    query_id: str = ""
    status: str = ""
    progress: float = 0.0
    current_step: str = ""


@dataclass
class CompleteMessage(WSMessage):
    """Query completion message."""
    type: str = "complete"
    query_id: str = ""
    result_summary: Dict = None


@dataclass
class ErrorMessage(WSMessage):
    """Error message."""
    type: str = "error"
    query_id: str = ""
    error: str = ""


@dataclass
class PongMessage(WSMessage):
    """Pong response to ping."""
    type: str = "pong"


# ============================================================================
# Connection Manager
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections and message routing.

    Features:
    - Connection pooling
    - Subscribe/unsubscribe to query updates
    - Broadcast messages to subscribers
    - Heartbeat/ping-pong
    - Automatic cleanup of disconnected clients
    """

    def __init__(self):
        # Active connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # Subscriptions: {query_id: Set[connection_id]}
        self.subscriptions: Dict[str, Set[str]] = {}

        # Connection metadata: {connection_id: {"connected_at": datetime, "last_ping": datetime}}
        self.connection_meta: Dict[str, Dict] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, connection_id: str):
        """
        Accept new WebSocket connection.

        Args:
            websocket: WebSocket instance
            connection_id: Unique connection identifier
        """
        await websocket.accept()

        async with self._lock:
            self.active_connections[connection_id] = websocket
            self.connection_meta[connection_id] = {
                "connected_at": datetime.now(timezone.utc),
                "last_ping": datetime.now(timezone.utc)
            }

        logger.info(f"WebSocket connected: {connection_id}")

    async def disconnect(self, connection_id: str):
        """
        Remove connection and clean up subscriptions.

        Args:
            connection_id: Connection to disconnect
        """
        async with self._lock:
            # Remove from active connections
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]

            # Remove from all subscriptions
            for query_id in list(self.subscriptions.keys()):
                if connection_id in self.subscriptions[query_id]:
                    self.subscriptions[query_id].remove(connection_id)

                # Clean up empty subscription sets
                if not self.subscriptions[query_id]:
                    del self.subscriptions[query_id]

            # Remove metadata
            if connection_id in self.connection_meta:
                del self.connection_meta[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe(self, connection_id: str, query_id: str):
        """
        Subscribe connection to query updates.

        Args:
            connection_id: Connection to subscribe
            query_id: Query to subscribe to
        """
        async with self._lock:
            if query_id not in self.subscriptions:
                self.subscriptions[query_id] = set()

            self.subscriptions[query_id].add(connection_id)

        logger.info(f"Connection {connection_id} subscribed to query {query_id}")

    async def unsubscribe(self, connection_id: str, query_id: str):
        """
        Unsubscribe connection from query updates.

        Args:
            connection_id: Connection to unsubscribe
            query_id: Query to unsubscribe from
        """
        async with self._lock:
            if query_id in self.subscriptions and connection_id in self.subscriptions[query_id]:
                self.subscriptions[query_id].remove(connection_id)

                # Clean up empty subscription sets
                if not self.subscriptions[query_id]:
                    del self.subscriptions[query_id]

        logger.info(f"Connection {connection_id} unsubscribed from query {query_id}")

    async def send_personal_message(self, message: str, connection_id: str):
        """
        Send message to specific connection.

        Args:
            message: JSON message to send
            connection_id: Target connection
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                await self.disconnect(connection_id)

    async def broadcast_to_query_subscribers(self, message: str, query_id: str):
        """
        Broadcast message to all subscribers of a query.

        Args:
            message: JSON message to send
            query_id: Query whose subscribers should receive message
        """
        if query_id not in self.subscriptions:
            return

        # Get snapshot of subscribers (avoid iteration during modification)
        subscribers = list(self.subscriptions[query_id])

        for connection_id in subscribers:
            await self.send_personal_message(message, connection_id)

    async def broadcast_to_all(self, message: str):
        """
        Broadcast message to all connected clients.

        Args:
            message: JSON message to send
        """
        # Get snapshot of connections
        connections = list(self.active_connections.keys())

        for connection_id in connections:
            await self.send_personal_message(message, connection_id)

    async def handle_ping(self, connection_id: str):
        """
        Handle ping message and send pong.

        Args:
            connection_id: Connection that sent ping
        """
        # Update last ping time
        if connection_id in self.connection_meta:
            self.connection_meta[connection_id]["last_ping"] = datetime.now(timezone.utc)

        # Send pong
        pong = PongMessage()
        await self.send_personal_message(pong.to_json(), connection_id)

    def get_stats(self) -> Dict:
        """
        Get connection statistics.

        Returns:
            Dict with connection stats
        """
        return {
            "active_connections": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "unique_queries": len(self.subscriptions)
        }


# ============================================================================
# Global Connection Manager Instance
# ============================================================================

manager = ConnectionManager()


# ============================================================================
# WebSocket Handler
# ============================================================================

async def websocket_handler(websocket: WebSocket, connection_id: str):
    """
    Handle WebSocket connection lifecycle.

    Args:
        websocket: WebSocket connection
        connection_id: Unique connection identifier
    """
    await manager.connect(websocket, connection_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    query_id = message.get("query_id")
                    if query_id:
                        await manager.subscribe(connection_id, query_id)
                        # Send confirmation
                        response = {
                            "type": "subscribed",
                            "query_id": query_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await manager.send_personal_message(json.dumps(response), connection_id)

                elif action == "unsubscribe":
                    query_id = message.get("query_id")
                    if query_id:
                        await manager.unsubscribe(connection_id, query_id)
                        # Send confirmation
                        response = {
                            "type": "unsubscribed",
                            "query_id": query_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        await manager.send_personal_message(json.dumps(response), connection_id)

                elif action == "ping":
                    await manager.handle_ping(connection_id)

                else:
                    # Unknown action
                    error = {
                        "type": "error",
                        "error": f"Unknown action: {action}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await manager.send_personal_message(json.dumps(error), connection_id)

            except json.JSONDecodeError:
                error = {
                    "type": "error",
                    "error": "Invalid JSON",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await manager.send_personal_message(json.dumps(error), connection_id)

    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        await manager.disconnect(connection_id)


# ============================================================================
# Helper Functions for Broadcasting Updates
# ============================================================================

async def broadcast_status_update(
    query_id: str,
    status: str,
    progress: float = 0.0,
    current_step: str = ""
):
    """
    Broadcast status update to subscribers.

    Args:
        query_id: Query ID
        status: Current status
        progress: Progress (0.0 to 1.0)
        current_step: Current processing step
    """
    message = StatusMessage(
        query_id=query_id,
        status=status,
        progress=progress,
        current_step=current_step
    )
    await manager.broadcast_to_query_subscribers(message.to_json(), query_id)


async def broadcast_completion(query_id: str, result_summary: Dict):
    """
    Broadcast completion message to subscribers.

    Args:
        query_id: Query ID
        result_summary: Summary of results
    """
    message = CompleteMessage(
        query_id=query_id,
        result_summary=result_summary
    )
    await manager.broadcast_to_query_subscribers(message.to_json(), query_id)


async def broadcast_error(query_id: str, error: str):
    """
    Broadcast error message to subscribers.

    Args:
        query_id: Query ID
        error: Error message
    """
    message = ErrorMessage(
        query_id=query_id,
        error=error
    )
    await manager.broadcast_to_query_subscribers(message.to_json(), query_id)
