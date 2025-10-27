 'use client'

import { useEffect, useRef, useState } from 'react'
import { adminAPI } from './api'

export interface WebSocketMessage {
  type: string
  data: any
}

export interface UseWebSocketReturn {
  socket: WebSocket | null
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  sendMessage: (message: any) => void
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  useEffect(() => {
    const connect = () => {
      try {
        setConnectionStatus('connecting')
        const ws = new WebSocket(url)
        
        ws.onopen = () => {
          console.log('WebSocket connected')
          setIsConnected(true)
          setConnectionStatus('connected')
          reconnectAttempts.current = 0
        }
        
        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            setLastMessage(message)
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }
        
        ws.onclose = () => {
          console.log('WebSocket disconnected')
          setIsConnected(false)
          setConnectionStatus('disconnected')
          
          // Attempt to reconnect
          if (reconnectAttempts.current < maxReconnectAttempts) {
            reconnectAttempts.current++
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
            console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current})`)
            
            reconnectTimeoutRef.current = setTimeout(() => {
              connect()
            }, delay)
          } else {
            setConnectionStatus('error')
            console.error('Max reconnection attempts reached')
          }
        }
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          setConnectionStatus('error')
        }
        
        setSocket(ws)
      } catch (error) {
        console.error('Error creating WebSocket:', error)
        setConnectionStatus('error')
      }
    }
    
    connect()
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (socket) {
        socket.close()
      }
    }
  }, [url])
  
  const sendMessage = (message: any) => {
    if (socket && isConnected) {
      try {
        socket.send(JSON.stringify(message))
      } catch (error) {
        console.error('Error sending WebSocket message:', error)
      }
    } else {
      console.warn('WebSocket not connected, cannot send message')
    }
  }
  
  return {
    socket,
    isConnected,
    lastMessage,
    sendMessage,
    connectionStatus
  }
}

// Hook for handling specific message types
export const useWebSocketMessage = (
  websocket: UseWebSocketReturn,
  messageType: string,
  callback: (data: any) => void
) => {
  useEffect(() => {
    if (websocket.lastMessage && websocket.lastMessage.type === messageType) {
      callback(websocket.lastMessage.data)
    }
  }, [websocket.lastMessage, messageType, callback])
}

// Hook for system status
export const useSystemStatus = () => {
  const [status, setStatus] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setIsLoading(true)
        // Use the axios-based adminAPI so requests go to the backend defined by API_URL
        const resp = await adminAPI.systemStatus()
        setStatus(resp.data)
        setError(null)
      } catch (err) {
        // axios error may have response data or message
        const message = err && (err as any).response?.data ? JSON.stringify((err as any).response.data) : (err as any)?.message || 'Unknown error'
        setError(message)
      } finally {
        setIsLoading(false)
      }
    }

    // Fetch once on mount only. Rely on WebSocket `session_update` messages
    // to keep the UI up-to-date in real-time. Polling was causing periodic
    // UI updates that looked like a page refresh; remove the 5s polling to
    // avoid that and rely on the server push via WebSocket.
    fetchStatus()

    return () => {
      /* no interval to clear since we only poll once on mount */
    }
  }, [])
  
  return { status, isLoading, error }
}
