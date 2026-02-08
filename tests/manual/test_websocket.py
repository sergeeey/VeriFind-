"""
Manual test script for WebSocket endpoint.

Run this script to test real-time WebSocket communication with the API.

Requirements:
    pip install websockets

Usage:
    python tests/manual/test_websocket.py
"""

import asyncio
import json
import websockets
from datetime import datetime


async def test_websocket_connection():
    """Test WebSocket connection and subscription flow."""
    uri = "ws://localhost:8000/ws"

    print("🔌 Connecting to WebSocket...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket!")

            # Test 1: Subscribe to a query
            query_id = "test-query-123"
            subscribe_message = {
                "action": "subscribe",
                "query_id": query_id
            }

            print(f"\n📤 Subscribing to query: {query_id}")
            await websocket.send(json.dumps(subscribe_message))

            # Receive subscription confirmation
            response = await websocket.recv()
            print(f"📥 Received: {response}")

            # Test 2: Send ping (heartbeat)
            print("\n📤 Sending ping...")
            await websocket.send(json.dumps({"action": "ping"}))

            response = await websocket.recv()
            print(f"📥 Received: {response}")

            # Test 3: Listen for updates (with timeout)
            print(f"\n👂 Listening for updates for {query_id} (10 seconds)...")
            print("   (In another terminal, submit a query or trigger an update)")

            try:
                for i in range(10):
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    print(f"📥 Update {i+1}: {json.dumps(data, indent=2)}")
            except asyncio.TimeoutError:
                print("   (No updates received - this is normal for testing)")

            # Test 4: Unsubscribe
            unsubscribe_message = {
                "action": "unsubscribe",
                "query_id": query_id
            }

            print(f"\n📤 Unsubscribing from query: {query_id}")
            await websocket.send(json.dumps(unsubscribe_message))

            response = await websocket.recv()
            print(f"📥 Received: {response}")

            # Test 5: Test invalid action
            print("\n📤 Testing invalid action...")
            await websocket.send(json.dumps({"action": "invalid", "query_id": "test"}))

            response = await websocket.recv()
            print(f"📥 Received: {response}")

            print("\n✅ All tests completed successfully!")

    except websockets.exceptions.ConnectionRefused:
        print("❌ Connection refused. Make sure the API server is running:")
        print("   python -m src.api.main")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_multiple_subscriptions():
    """Test subscribing to multiple queries simultaneously."""
    uri = "ws://localhost:8000/ws"

    print("\n🔌 Testing multiple subscriptions...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")

            # Subscribe to multiple queries
            query_ids = ["query-1", "query-2", "query-3"]

            for query_id in query_ids:
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "query_id": query_id
                }))
                response = await websocket.recv()
                print(f"📥 {response}")

            print(f"\n✅ Subscribed to {len(query_ids)} queries")

            # Unsubscribe from all
            for query_id in query_ids:
                await websocket.send(json.dumps({
                    "action": "unsubscribe",
                    "query_id": query_id
                }))
                response = await websocket.recv()
                print(f"📥 {response}")

            print("\n✅ Multiple subscriptions test completed!")

    except Exception as e:
        print(f"❌ Error: {e}")


async def simulate_query_updates(query_id: str = "simulation-query"):
    """
    Simulate query status updates (for testing without orchestrator).

    This requires importing and calling broadcast_query_update from the API.
    For now, this is a placeholder showing the expected flow.
    """
    print(f"\n🎭 Simulating query updates for: {query_id}")
    print("   (This would require direct API integration)")

    updates = [
        {"status": "processing", "current_node": "PLAN", "progress": 0.2},
        {"status": "processing", "current_node": "FETCH", "progress": 0.4},
        {"status": "processing", "current_node": "VEE", "progress": 0.6},
        {"status": "processing", "current_node": "GATE", "progress": 0.8},
        {"status": "processing", "current_node": "DEBATE", "progress": 0.9},
        {"status": "completed", "current_node": None, "progress": 1.0},
    ]

    for update in updates:
        print(f"   📤 Would broadcast: {update}")
        await asyncio.sleep(1)

    print("✅ Simulation complete")


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Test Suite")
    print("=" * 60)

    # Run basic connection test
    asyncio.run(test_websocket_connection())

    # Run multiple subscriptions test
    asyncio.run(test_multiple_subscriptions())

    # Show simulation example
    asyncio.run(simulate_query_updates())

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
