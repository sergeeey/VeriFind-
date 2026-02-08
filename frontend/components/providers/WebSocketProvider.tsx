'use client'

import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { WS_URL } from '@/lib/constants'
import type { WebSocketMessage } from '@/types/query'

interface WebSocketContextType {
  connected: boolean
  subscribe: (queryId: string, callback: (data: any) => void) => () => void
  send: (message: any) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: React.ReactNode
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const listenersRef = useRef<Map<string, Set<(data: any) => void>>>(new Map())
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttempts = useRef(0)

  const connect = () => {
    // Skip WebSocket connection in server-side rendering
    if (typeof window === 'undefined') return

    try {
      const ws = new WebSocket(`${WS_URL}/ws`)

      ws.onopen = () => {
        console.log('[WebSocket] Connected')
        setConnected(true)
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          console.log('[WebSocket] Message received:', message)

          // Notify all listeners for this query_id
          const listeners = listenersRef.current.get(message.query_id)
          if (listeners) {
            listeners.forEach((callback) => callback(message.data))
          }
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
      }

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected')
        setConnected(false)
        wsRef.current = null

        // Attempt to reconnect with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
        reconnectAttempts.current++

        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`)
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('[WebSocket] Connection failed:', error)
      // Fallback: Don't attempt reconnect if WebSocket is not available
      setConnected(false)
    }
  }

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const subscribe = (queryId: string, callback: (data: any) => void) => {
    // Get or create listeners set for this queryId
    let listeners = listenersRef.current.get(queryId)
    if (!listeners) {
      listeners = new Set()
      listenersRef.current.set(queryId, listeners)
    }

    // Add callback to listeners
    listeners.add(callback)

    console.log(`[WebSocket] Subscribed to query ${queryId}`)

    // Return unsubscribe function
    return () => {
      listeners?.delete(callback)
      if (listeners?.size === 0) {
        listenersRef.current.delete(queryId)
      }
      console.log(`[WebSocket] Unsubscribed from query ${queryId}`)
    }
  }

  const send = (message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('[WebSocket] Cannot send message - not connected')
    }
  }

  const value: WebSocketContextType = {
    connected,
    subscribe,
    send,
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}
