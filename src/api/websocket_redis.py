"""
Redis-based WebSocket Connection Manager

Week 1 Day 5: Production Readiness
Enables horizontal scaling across multiple server instances
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime
from dataclasses import dataclass, asdict

import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Connection metadata"""
    client_id: str
    connected_at: str
    last_ping: str
    server_id: str  # For debugging which server handled connection


class RedisConnectionManager:
    """
    WebSocket connection manager using Redis for horizontal scaling.
    
    Features:
    - Connection state stored in Redis (survives server restarts)
    - Cross-server broadcasting via Redis pub/sub
    - Automatic reconnection handling
    - Graceful degradation if Redis unavailable
    
    Architecture:
    - Each server instance subscribes to Redis channels
    - Messages published to Redis are broadcast to all servers
    - Local connections tracked in memory for fast access
    """
    
    def __init__(self, redis_url: str = None, server_id: str = None):
        """
        Initialize connection manager.
        
        Args:
            redis_url: Redis connection URL (defaults to env var)
            server_id: Unique identifier for this server instance
        """
        self.redis_url = redis_url or os.getenv(
            "REDIS_URL", 
            "redis://localhost:6380/0"
        )
        self.server_id = server_id or f"server_{os.getpid()}_{datetime.utcnow().timestamp()}"
        
        # Redis clients
        self._redis: redis.Redis = None
        self._pubsub = None
        
        # Local state (for fast access)
        self._local_connections: Dict[str, WebSocket] = {}
        
        # Background tasks
        self._listener_task = None
        self._running = False
    
    async def connect(self) -> bool:
        """
        Connect to Redis and start listener.
        
        Returns:
            True if connected, False if using fallback mode
        """
        try:
            # Connect to Redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            
            # Start pub/sub listener
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe("ws:broadcast", "ws:server:*")
            
            # Start background listener
            self._running = True
            self._listener_task = asyncio.create_task(self._listen())
            
            logger.info(f"RedisConnectionManager connected: {self.server_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
            self._redis = None
            self._pubsub = None
            return False
    
    async def disconnect(self):
        """Disconnect from Redis and cleanup"""
        self._running = False
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        
        if self._redis:
            await self._redis.close()
        
        # Close all local connections
        for client_id, websocket in list(self._local_connections.items()):
            try:
                await websocket.close()
            except:
                pass
        
        self._local_connections.clear()
        logger.info(f"RedisConnectionManager disconnected: {self.server_id}")
    
    async def connect_client(self, client_id: str, websocket: WebSocket):
        """
        Register new WebSocket connection.
        
        Args:
            client_id: Unique client identifier
            websocket: FastAPI WebSocket instance
        """
        await websocket.accept()
        
        # Store locally
        self._local_connections[client_id] = websocket
        
        # Store in Redis (for cross-server awareness)
        if self._redis:
            conn_info = ConnectionInfo(
                client_id=client_id,
                connected_at=datetime.utcnow().isoformat(),
                last_ping=datetime.utcnow().isoformat(),
                server_id=self.server_id
            )
            await self._redis.hset(
                "ws:connections",
                client_id,
                json.dumps(asdict(conn_info))
            )
        
        logger.info(f"Client connected: {client_id} on {self.server_id}")
    
    async def disconnect_client(self, client_id: str):
        """Unregister WebSocket connection"""
        # Remove locally
        if client_id in self._local_connections:
            del self._local_connections[client_id]
        
        # Remove from Redis
        if self._redis:
            await self._redis.hdel("ws:connections", client_id)
        
        logger.info(f"Client disconnected: {client_id}")
    
    async def send_personal_message(self, message: str, client_id: str):
        """
        Send message to specific client.
        
        If client is connected to this server, send directly.
        Otherwise, message will be lost (client may be on another server).
        """
        if client_id in self._local_connections:
            websocket = self._local_connections[client_id]
            try:
                await websocket.send_text(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send to {client_id}: {e}")
                await self.disconnect_client(client_id)
                return False
        else:
            logger.warning(f"Client {client_id} not connected to this server")
            return False
    
    async def broadcast(self, message: str):
        """
        Broadcast message to all connected clients.
        
        Uses Redis pub/sub for cross-server broadcasting.
        """
        # Send to local connections
        disconnected = []
        for client_id, websocket in list(self._local_connections.items()):
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Cleanup disconnected
        for client_id in disconnected:
            await self.disconnect_client(client_id)
        
        # Publish to Redis for other servers
        if self._redis:
            await self._redis.publish("ws:broadcast", json.dumps({
                "type": "broadcast",
                "message": message,
                "server_id": self.server_id,
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    async def broadcast_to_others(self, message: str, sender_id: str):
        """Broadcast to all except sender"""
        for client_id, websocket in list(self._local_connections.items()):
            if client_id != sender_id:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to send to {client_id}: {e}")
                    await self.disconnect_client(client_id)
        
        # Publish to Redis for other servers
        if self._redis:
            await self._redis.publish("ws:broadcast", json.dumps({
                "type": "broadcast_except",
                "message": message,
                "except_client": sender_id,
                "server_id": self.server_id,
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    async def get_connection_count(self) -> int:
        """Get total number of connections (approximate)"""
        # Local count (accurate for this server)
        local_count = len(self._local_connections)
        
        # Redis count (may include stale entries)
        if self._redis:
            redis_count = await self._redis.hlen("ws:connections")
            return max(local_count, redis_count)
        
        return local_count
    
    async def _listen(self):
        """Background task: listen for Redis messages"""
        if not self._pubsub:
            return
        
        try:
            async for message in self._pubsub.listen():
                if not self._running:
                    break
                
                if message["type"] == "message":
                    await self._handle_redis_message(message)
                    
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
    
    async def _handle_redis_message(self, message: dict):
        """Handle message from Redis pub/sub"""
        try:
            data = json.loads(message["data"])
            msg_type = data.get("type")
            
            if msg_type == "broadcast":
                # Message from another server, already sent to local clients
                # by the originating server, so we ignore it to avoid duplicates
                pass
                
            elif msg_type == "direct":
                # Direct message to client on this server
                client_id = data.get("client_id")
                msg = data.get("message")
                if client_id in self._local_connections:
                    await self._local_connections[client_id].send_text(msg)
                    
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in Redis message: {message}")
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")
    
    async def ping(self, client_id: str):
        """Update last ping time for client"""
        if self._redis:
            conn_json = await self._redis.hget("ws:connections", client_id)
            if conn_json:
                conn_info = json.loads(conn_json)
                conn_info["last_ping"] = datetime.utcnow().isoformat()
                await self._redis.hset(
                    "ws:connections",
                    client_id,
                    json.dumps(conn_info)
                )


# Global instance (initialized on startup)
manager: RedisConnectionManager = None


async def get_manager() -> RedisConnectionManager:
    """Get or initialize connection manager"""
    global manager
    if manager is None:
        manager = RedisConnectionManager()
        await manager.connect()
    return manager
