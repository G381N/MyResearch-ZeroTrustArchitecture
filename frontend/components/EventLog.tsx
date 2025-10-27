'use client'

import { useEffect, useRef } from 'react'
import { AlertTriangle, CheckCircle, Clock, User, Activity } from 'lucide-react'

interface EventLogProps {
  events: any[]
  showAnomalies?: boolean
  isLive?: boolean
  emptyMessage?: string
}

export default function EventLog({ events, showAnomalies = false, isLive = false, emptyMessage = 'No events' }: EventLogProps) {
  const logRef = useRef<HTMLDivElement>(null)
  
  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (logRef.current && isLive) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [events, isLive])
  
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }
  
  const getEventTypeColor = (eventType: string) => {
    const colors: Record<string, string> = {
      'auth_failure': 'text-red-500',
      'sudo_command': 'text-orange-500',
      'network_connection': 'text-blue-500',
      'file_change': 'text-yellow-500',
      'process_start': 'text-green-500',
      'process_end': 'text-gray-500',
      'login': 'text-purple-500',
      'logout': 'text-gray-500'
    }
    return colors[eventType] || 'text-gray-500'
  }
  
  const getEventIcon = (eventType: string) => {
    const icons: Record<string, any> = {
      'auth_failure': AlertTriangle,
      'sudo_command': AlertTriangle,
      'network_connection': Activity,
      'file_change': Activity,
      'process_start': CheckCircle,
      'process_end': CheckCircle,
      'login': User,
      'logout': User
    }
    return icons[eventType] || Activity
  }
  
  if (events.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>{emptyMessage}</p>
      </div>
    )
  }
  
  return (
    <div 
      ref={logRef}
      className="h-96 overflow-y-auto bg-black/50 font-mono text-sm"
      style={{ scrollbarWidth: 'thin' }}
    >
      {events.map((event, index) => {
        const Icon = getEventIcon(event.event_type)
        const isAnomaly = showAnomalies ? event.is_anomaly : false
        
        return (
          <div
            key={event.id || index}
            className={`p-3 border-b border-border/50 hover:bg-muted/20 transition-colors fade-in ${
              isAnomaly ? 'bg-red-500/5 border-red-500/20' : ''
            }`}
          >
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 mt-1">
                <Icon className={`h-4 w-4 ${getEventTypeColor(event.event_type)}`} />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <span className="text-muted-foreground text-xs">
                    {formatTimestamp(event.timestamp)}
                  </span>
                  
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getEventTypeColor(event.event_type)} bg-current/10`}>
                    {event.event_type}
                  </span>
                  
                  {isAnomaly && (
                    <span className="px-2 py-1 rounded text-xs font-medium text-red-500 bg-red-500/10">
                      ANOMALY
                    </span>
                  )}
                  
                  {event.confidence_score && (
                    <span className="text-xs text-muted-foreground">
                      {Math.round(event.confidence_score * 100)}% confidence
                    </span>
                  )}
                </div>
                
                <div className="text-foreground">
                  {event.metadata?.process_name && (
                    <div className="font-medium">{event.metadata.process_name}</div>
                  )}
                  
                  {event.metadata?.command && (
                    <div className="font-medium">{event.metadata.command}</div>
                  )}
                  
                  {event.metadata?.user_id && (
                    <div className="text-sm text-muted-foreground">
                      User: {event.metadata.user_id}
                    </div>
                  )}
                  
                  {event.metadata?.file_path && (
                    <div className="text-sm text-muted-foreground">
                      File: {event.metadata.file_path}
                    </div>
                  )}
                  
                  {event.metadata?.local_address && event.metadata?.remote_address && (
                    <div className="text-sm text-muted-foreground">
                      {event.metadata.local_address} → {event.metadata.remote_address}
                    </div>
                  )}
                  
                  {event.trust_impact && event.trust_impact !== 0 && (
                    <div className="text-sm text-red-500">
                      Trust Impact: {event.trust_impact > 0 ? '+' : ''}{event.trust_impact}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
