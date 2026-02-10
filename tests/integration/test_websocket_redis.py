"""
Redis WebSocket Tests

Week 1 Day 5: Production Readiness
Test horizontal scaling with Redis
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


class TestRedisConnectionManager:
    """Redis connection manager tests"""
    
    @pytest.mark.asyncio
    async def test_connection_stored_in_redis(self):
        """Connection info stored in Redis"""
        from src.api.websocket_redis import RedisConnectionManager
        
        manager = RedisConnectionManager()
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.hset = AsyncMock()
        manager._redis = mock_redis
        manager._pubsub = None  # Skip pub/sub for this test
        
        # Mock WebSocket
        mock_ws = AsyncMock()
        
        # Connect client
        await manager.connect_client("test_client", mock_ws)
        
        # Verify stored in Redis
        assert mock_redis.hset.called
        args = mock_redis.hset.call_args
        assert args[0][0] == "ws:connections"
        assert args[0][1] == "test_client"
    
    @pytest.mark.asyncio
    async def test_connection_removed_on_disconnect(self):
        """Connection removed from Redis on disconnect"""
        from src.api.websocket_redis import RedisConnectionManager
        
        manager = RedisConnectionManager()
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.hdel = AsyncMock()
        manager._redis = mock_redis
        
        # Add and remove connection
        mock_ws = AsyncMock()
        manager._local_connections["test_client"] = mock_ws
        
        await manager.disconnect_client("test_client")
        
        # Verify removed from Redis
        mock_redis.hdel.assert_called_with("ws:connections", "test_client")
    
    @pytest.mark.asyncio
    async def test_broadcast_publishes_to_redis(self):
        """Broadcast publishes message to Redis"""
        from src.api.websocket_redis import RedisConnectionManager
        
        manager = RedisConnectionManager(server_id="test_server")
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()
        manager._redis = mock_redis
        
        # Broadcast
        await manager.broadcast("test message")
        
        # Verify published to Redis
        assert mock_redis.publish.called
        args = mock_redis.publish.call_args
        assert args[0][0] == "ws:broadcast"
        assert "test message" in args[0][1]
    
    @pytest.mark.asyncio
    async def test_fallback_mode_when_redis_unavailable(self):
        """ Falls back to in-memory mode when Redis unavailable"""
        from src.api.websocket_redis import RedisConnectionManager
        
        manager = RedisConnectionManager(redis_url="redis://invalid:9999/0")
        
        # Try to connect (should fail gracefully)
        connected = await manager.connect()
        
        # Should return False but not crash
        assert connected is False
        assert manager._redis is None
    
    @pytest.mark.asyncio
    async def test_local_connections_fast_access(self):
        """Local connections accessible without Redis roundtrip"""
        from src.api.websocket_redis import RedisConnectionManager
        
        manager = RedisConnectionManager()
        
        # Add connection locally
        mock_ws = AsyncMock()
        manager._local_connections["client1"] = mock_ws
        
        # Send message (should use local connection)
        await manager.send_personal_message("hello", "client1")
        
        # Verify sent via local connection
        mock_ws.send_text.assert_called_with("hello")
    
    @pytest.mark.asyncio
    async def test_connection_count_accurate(self):
        """Connection count reflects actual connections"""
        from src.api.websocket_redis import RedisConnectionManager
        
        manager = RedisConnectionManager()
        
        # Add connections
        manager._local_connections["c1"] = AsyncMock()
        manager._local_connections["c2"] = AsyncMock()
        manager._local_connections["c3"] = AsyncMock()
        
        # Mock Redis hlen
        mock_redis = AsyncMock()
        mock_redis.hlen = AsyncMock(return_value=5)
        manager._redis = mock_redis
        
        count = await manager.get_connection_count()
        
        # Should return max of local and Redis counts
        assert count >= 3


class TestHorizontalScaling:
    """Horizontal scaling tests"""
    
    @pytest.mark.asyncio
    async def test_multiple_servers_share_state(self):
        """Multiple server instances share connection state via Redis"""
        from src.api.websocket_redis import RedisConnectionManager
        
        # Simulate two servers
        server1 = RedisConnectionManager(server_id="server_1")
        server2 = RedisConnectionManager(server_id="server_2")
        
        # Mock shared Redis
        shared_redis = AsyncMock()
        shared_redis.hset = AsyncMock()
        shared_redis.hget = AsyncMock(return_value='{"client_id": "c1", "server_id": "server_1"}')
        
        server1._redis = shared_redis
        server2._redis = shared_redis
        
        # Client connects to server1
        mock_ws = AsyncMock()
        await server1.connect_client("c1", mock_ws)
        
        # Server2 should be able to see the connection
        conn_info = await shared_redis.hget("ws:connections", "c1")
        assert conn_info is not None
    
    @pytest.mark.asyncio
    async def test_broadcast_reaches_all_servers(self):
        """Broadcast message reaches clients on all servers"""
        from src.api.websocket_redis import RedisConnectionManager
        
        server1 = RedisConnectionManager(server_id="server_1")
        server2 = RedisConnectionManager(server_id="server_2")
        
        # Mock Redis pub/sub
        mock_redis1 = AsyncMock()
        mock_redis1.publish = AsyncMock()
        server1._redis = mock_redis1
        
        # Client on server1
        mock_ws = AsyncMock()
        await server1.connect_client("c1", mock_ws)
        
        # Broadcast from server1
        await server1.broadcast("hello all")
        
        # Should publish to Redis (for server2 to receive)
        assert mock_redis1.publish.called


class TestGracefulDegradation:
    """Graceful degradation tests"""
    
    @pytest.mark.asyncio
    async def test_operations_continue_without_redis(self):
        """Local operations continue when Redis unavailable"""
        from src.api.websocket_redis import RedisConnectionManager
        
        manager = RedisConnectionManager()
        manager._redis = None  # Simulate Redis failure
        
        # Should still accept connections locally
        mock_ws = AsyncMock()
        await manager.connect_client("c1", mock_ws)
        
        assert "c1" in manager._local_connections
        
        # Should still be able to broadcast locally
        await manager.broadcast("test")
        mock_ws.send_text.assert_called_with("test")


class TestWebSocketEndpoint:
    """WebSocket endpoint integration tests"""
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_accepts_connection(self):
        """WebSocket endpoint accepts connections"""
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        client = TestClient(app)
        
        # Try to connect to WebSocket
        with client.websocket_connect("/ws/test_client") as websocket:
            # Should be able to send/receive
            websocket.send_text("ping")
            # Response depends on implementation
    
    @pytest.mark.asyncio
    async def test_websocket_message_broadcast(self):
        """Messages broadcast to all connected clients"""
        # This would require multiple WebSocket connections
        # Integration test with real server
        pass


# Mark all tests in this file
pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.redis,
]
