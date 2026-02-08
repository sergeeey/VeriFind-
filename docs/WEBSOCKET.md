# WebSocket API Documentation

**Endpoint:** `ws://localhost:8000/ws`

**Status:** ✅ Implemented (Week 9 Day 1)

---

## Overview

The WebSocket endpoint provides real-time updates for query execution status. Clients can subscribe to specific query IDs and receive live updates as the query progresses through the APE pipeline.

---

## Connection Flow

```
┌─────────┐                                 ┌─────────┐
│ Client  │                                 │  Server │
└────┬────┘                                 └────┬────┘
     │                                           │
     │  1. WebSocket Connect                     │
     ├──────────────────────────────────────────>│
     │                                           │
     │  2. Subscribe to query_id                 │
     │  {"action": "subscribe", "query_id": "..."} │
     ├──────────────────────────────────────────>│
     │                                           │
     │  3. Confirmation                          │
     │  {"status": "subscribed", ...}            │
     │<──────────────────────────────────────────┤
     │                                           │
     │  4. Live Updates (pushed by server)       │
     │  {"query_id": "...", "data": {...}}       │
     │<══════════════════════════════════════════┤
     │                                           │
     │  5. Unsubscribe (optional)                │
     │  {"action": "unsubscribe", "query_id": "..."} │
     ├──────────────────────────────────────────>│
     │                                           │
     │  6. Disconnect                            │
     │<──────────────────────────────────────────┤
     └───────────────────────────────────────────┘
```

---

## Message Protocol

### Client → Server Messages

All messages must be valid JSON.

#### 1. Subscribe to Query

```json
{
  "action": "subscribe",
  "query_id": "abc-123-def-456"
}
```

**Response:**
```json
{
  "status": "subscribed",
  "query_id": "abc-123-def-456",
  "message": "Subscribed to updates for query abc-123-def-456"
}
```

#### 2. Unsubscribe from Query

```json
{
  "action": "unsubscribe",
  "query_id": "abc-123-def-456"
}
```

**Response:**
```json
{
  "status": "unsubscribed",
  "query_id": "abc-123-def-456",
  "message": "Unsubscribed from query abc-123-def-456"
}
```

#### 3. Ping (Heartbeat)

```json
{
  "action": "ping"
}
```

**Response:**
```json
{
  "status": "pong",
  "timestamp": "2026-02-08T12:00:00.000Z"
}
```

---

### Server → Client Messages

#### Query Status Update (Broadcast)

Sent automatically when query status changes.

```json
{
  "query_id": "abc-123-def-456",
  "data": {
    "status": "processing",
    "current_node": "VEE",
    "progress": 0.6,
    "verified_facts_count": 2,
    "error": null,
    "updated_at": "2026-02-08T12:00:00.000Z",
    "metadata": {
      "priority": "normal",
      "query_text": "Calculate Sharpe ratio of SPY for 2023"
    }
  }
}
```

**Fields:**
- `query_id` (string): Query identifier
- `data.status` (string): Current status
  - `"accepted"` - Query accepted, not yet started
  - `"processing"` - Query is being processed
  - `"completed"` - Query completed successfully
  - `"failed"` - Query failed with error
- `data.current_node` (string|null): Current pipeline node
  - `"PLAN"` - Planning analysis steps
  - `"FETCH"` - Fetching market data
  - `"VEE"` - Verifying facts in sandbox
  - `"GATE"` - Truth boundary validation
  - `"DEBATE"` - Bull/bear debate analysis
  - `null` - Not in pipeline (accepted/completed/failed)
- `data.progress` (number): Completion progress (0.0 to 1.0)
- `data.verified_facts_count` (number): Facts generated so far
- `data.error` (string|null): Error message if failed
- `data.updated_at` (string): ISO 8601 timestamp
- `data.metadata` (object): Additional metadata

---

## Pipeline Progress Mapping

| Node | Progress | Description |
|------|----------|-------------|
| Accepted | 0.0 | Query accepted, queued |
| PLAN | 0.2 | Planning analysis steps |
| FETCH | 0.4 | Fetching market data |
| VEE | 0.6 | Verifying facts in sandbox |
| GATE | 0.8 | Truth boundary validation |
| DEBATE | 0.9 | Bull/bear debate |
| Completed | 1.0 | Query completed |

---

## Error Handling

### Invalid Message Format

**Client sends:**
```json
{
  "invalid": "message"
}
```

**Server responds:**
```json
{
  "error": "Invalid message format. Expected: {action, query_id}",
  "received": {
    "invalid": "message"
  }
}
```

### Unknown Action

**Client sends:**
```json
{
  "action": "unknown",
  "query_id": "test"
}
```

**Server responds:**
```json
{
  "error": "Unknown action: unknown",
  "supported_actions": ["subscribe", "unsubscribe", "ping"]
}
```

### Invalid JSON

**Client sends:**
```
not valid json
```

**Server responds:**
```json
{
  "error": "Invalid JSON format"
}
```

---

## Client Implementation Examples

### JavaScript (Browser)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('✅ Connected');

  // Subscribe to query
  ws.send(JSON.stringify({
    action: 'subscribe',
    query_id: 'my-query-id'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('📥 Update:', message);

  if (message.data) {
    // Update UI with query status
    updateUI(message.data);
  }
};

ws.onerror = (error) => {
  console.error('❌ WebSocket error:', error);
};

ws.onclose = () => {
  console.log('🔌 Disconnected');
};

// Unsubscribe before closing
function cleanup() {
  ws.send(JSON.stringify({
    action: 'unsubscribe',
    query_id: 'my-query-id'
  }));
  ws.close();
}
```

### Python (websockets library)

```python
import asyncio
import json
import websockets

async def listen_to_query(query_id):
    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:
        # Subscribe
        await websocket.send(json.dumps({
            "action": "subscribe",
            "query_id": query_id
        }))

        # Listen for updates
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📥 Update: {data}")

            # Check if completed
            if data.get("data", {}).get("status") == "completed":
                break

        # Unsubscribe
        await websocket.send(json.dumps({
            "action": "unsubscribe",
            "query_id": query_id
        }))

asyncio.run(listen_to_query("my-query-id"))
```

### React Hook (TypeScript)

```typescript
import { useEffect, useState } from 'react';

interface QueryUpdate {
  status: string;
  current_node: string | null;
  progress: number;
  verified_facts_count: number;
  error: string | null;
  updated_at: string;
}

export function useQueryStatus(queryId: string | null) {
  const [update, setUpdate] = useState<QueryUpdate | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!queryId) return;

    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({
        action: 'subscribe',
        query_id: queryId
      }));
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.data) {
        setUpdate(message.data);
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    return () => {
      ws.send(JSON.stringify({
        action: 'unsubscribe',
        query_id: queryId
      }));
      ws.close();
    };
  }, [queryId]);

  return { update, connected };
}
```

---

## Testing

### Manual Test

```bash
# Install websockets library
pip install websockets

# Run test script
python tests/manual/test_websocket.py
```

### Interactive Test (wscat)

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/ws

# Send subscribe message
> {"action": "subscribe", "query_id": "test-123"}

# Send ping
> {"action": "ping"}

# Unsubscribe
> {"action": "unsubscribe", "query_id": "test-123"}
```

---

## Architecture

### Connection Manager

The `ConnectionManager` class manages WebSocket connections:

- **Subscription tracking**: Maps `query_id` → Set of WebSocket connections
- **Thread-safe**: Uses `asyncio.Lock` for concurrent access
- **Auto-cleanup**: Removes disconnected clients automatically
- **Broadcasting**: Efficient message delivery to all subscribers

### Integration Points

1. **Query Submission**: `POST /query` broadcasts initial "accepted" status
2. **Orchestrator**: Should call `broadcast_query_update()` at each pipeline node
3. **Query Completion**: Broadcasts final "completed" or "failed" status

---

## Performance Considerations

- **Connection Limit**: No hard limit, but monitor memory usage in production
- **Message Size**: Keep updates small (<1 KB) for efficiency
- **Heartbeat**: Clients should send ping every 30-60 seconds
- **Reconnection**: Clients should implement exponential backoff on disconnect

---

## Security Considerations

⚠️ **TODO for Production:**

1. **Authentication**: Currently no auth on WebSocket endpoint
   - Add JWT token validation
   - Verify client has access to query_id
2. **Rate Limiting**: Prevent subscription spam
3. **CORS**: Configure allowed origins
4. **WSS**: Use secure WebSocket (wss://) in production

---

## Future Enhancements

- [ ] Authentication/Authorization
- [ ] Subscription to multiple queries with wildcards
- [ ] Historical replay of events
- [ ] Binary protocol for efficiency (e.g., MessagePack)
- [ ] Compression for large messages

---

**Last Updated:** 2026-02-08
**Status:** Production Ready (authentication pending)
**Version:** 1.0.0
