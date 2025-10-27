'use client'

import { useState, useEffect } from 'react'
import { trainingAPI, eventsAPI } from '@/lib/api'
import { useWebSocketMessage } from '@/lib/websocket'
import EventLog from './EventLog'
import StatsPanel from './StatsPanel'
import { Play, Square, Activity, Database, Brain } from 'lucide-react'

interface TrainingModeProps {
  websocket: any
}

interface TrainingStats {
  totalEvents: number
  eventCounts: Record<string, number>
  sessionDuration: number
  isActive: boolean
}

export default function TrainingMode({ websocket }: TrainingModeProps) {
  const [isTraining, setIsTraining] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [events, setEvents] = useState<any[]>([])
  const [stats, setStats] = useState<TrainingStats>({
    totalEvents: 0,
    eventCounts: {},
    sessionDuration: 0,
    isActive: false
  })
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Handle WebSocket messages
  useWebSocketMessage(websocket, 'event', (data) => {
    if (isTraining) {
      setEvents(prev => [data, ...prev.slice(0, 99)]) // Keep last 100 events
      setStats(prev => ({
        ...prev,
        totalEvents: prev.totalEvents + 1,
        eventCounts: {
          ...prev.eventCounts,
          [data.event_type]: (prev.eventCounts[data.event_type] || 0) + 1
        }
      }))
    }
  })

  useWebSocketMessage(websocket, 'session_update', (data) => {
    if (data.mode === 'training') {
      if (data.status === 'started') {
        setIsTraining(true)
        setSuccess('Training mode started successfully')
        setError(null)
      } else if (data.status === 'completed') {
        setIsTraining(false)
        setSuccess('Training completed and model trained successfully')
        setError(null)
      }
    }
  })

  const startTraining = async () => {
    try {
      setIsLoading(true)
      setError(null)
      setSuccess(null)
      
      const response = await trainingAPI.start()
      
      if (response.data) {
        setIsTraining(true)
        setSuccess('Training mode started')
        // Keep existing events collected in the UI so training continues until Stop is pressed
        setStats(prev => ({ ...prev, isActive: true }))
        // If server returned a session id, preload any events attached to it (useful after page reloads)
        if (response.data.session_id) {
          await loadSessionEvents(response.data.session_id)
        }
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || (err.message ?? 'Failed to start training')
      setError(detail)

      // If server says training is already active, sync UI with existing session
      if (err.response?.status === 400 && typeof detail === 'string' && detail.toLowerCase().includes('already active')) {
        try {
          await getTrainingStatus()
          setSuccess('Resumed existing training session')
          setError(null)
        } catch (e) {
          console.error('Failed to sync training status after start conflict:', e)
        }
      }
    } finally {
      setIsLoading(false)
    }
  }

  const stopTraining = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const response = await trainingAPI.stop()
      
      if (response.data) {
        setIsTraining(false)
        setSuccess('Training stopped and model trained')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to stop training')
    } finally {
      setIsLoading(false)
    }
  }

  const getTrainingStatus = async () => {
    try {
      const response = await trainingAPI.status()
      const status = response.data
      
      if (status.active) {
        setIsTraining(true)
        setStats(prev => ({ ...prev, isActive: true }))
        if (status.session_id) {
          // Load events for the active session so UI survives refreshes
          await loadSessionEvents(status.session_id)
        }
      }
    } catch (err) {
      console.error('Error getting training status:', err)
    }
  }

  const loadSessionEvents = async (sessionId: number) => {
    try {
      const resp = await eventsAPI.get({ session_id: sessionId, limit: 1000 })
      if (resp && resp.data) {
        // resp.data is newest-first (timestamp desc)
        setEvents(resp.data)
        setStats(prev => ({
          ...prev,
          totalEvents: resp.data.length,
          eventCounts: resp.data.reduce((acc: any, ev: any) => {
            acc[ev.event_type] = (acc[ev.event_type] || 0) + 1
            return acc
          }, {})
        }))
      }
    } catch (err) {
      console.error('Failed to load session events:', err)
    }
  }

  useEffect(() => {
    getTrainingStatus()
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Activity className="h-8 w-8 text-blue-500" />
          <div>
            <h2 className="text-2xl font-bold">Training Mode</h2>
            <p className="text-muted-foreground">
              Collect system events to train the anomaly detection model
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          {isTraining && (
            <div className="flex items-center space-x-2 text-green-500">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium">Training Active</span>
            </div>
          )}
        </div>
      </div>

      {/* Status Messages */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-destructive rounded-full" />
            <span className="text-destructive font-medium">{error}</span>
          </div>
        </div>
      )}
      
      {success && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-md p-4">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-green-500 font-medium">{success}</span>
          </div>
        </div>
      )}

      {/* Control Panel */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Database className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {stats.totalEvents} events collected
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <Brain className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Model: {isTraining ? 'Training...' : 'Ready'}
              </span>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {!isTraining ? (
              <button
                onClick={startTraining}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="h-4 w-4" />
                <span>{isLoading ? 'Starting...' : 'Start Training'}</span>
              </button>
            ) : (
              <button
                onClick={stopTraining}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Square className="h-4 w-4" />
                <span>{isLoading ? 'Stopping...' : 'Stop Training'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Stats Panel */}
      <StatsPanel
        title="Training Statistics"
        stats={[
          {
            label: 'Total Events',
            value: stats.totalEvents.toString(),
            icon: Activity,
            color: 'text-blue-500'
          },
          {
            label: 'Event Types',
            value: Object.keys(stats.eventCounts).length.toString(),
            icon: Database,
            color: 'text-green-500'
          },
          {
            label: 'Session Duration',
            value: `${Math.round(stats.sessionDuration)}m`,
            icon: Brain,
            color: 'text-purple-500'
          }
        ]}
        eventCounts={stats.eventCounts}
      />

      {/* Event Log */}
      <div className="bg-card border border-border rounded-lg">
        <div className="p-4 border-b border-border">
          <h3 className="text-lg font-semibold">Live Event Stream</h3>
          <p className="text-sm text-muted-foreground">
            {isTraining 
              ? 'Monitoring system events in real-time...' 
              : 'Start training to begin event collection'
            }
          </p>
        </div>
        
        <EventLog
          events={events}
          showAnomalies={false}
          isLive={isTraining}
          emptyMessage={
            isTraining 
              ? 'Waiting for system events...' 
              : 'Start training to begin collecting events'
          }
        />
      </div>

      {/* Instructions */}
      <div className="bg-muted/50 border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-3">Training Instructions</h3>
        <div className="space-y-2 text-sm text-muted-foreground">
          <p>1. Click "Start Training" to begin collecting system events</p>
          <p>2. Perform normal system activities (browse files, run commands, etc.)</p>
          <p>3. Let the system collect at least 50-100 events for good training data</p>
          <p>4. Click "Stop Training" to train the anomaly detection model</p>
          <p>5. Once training is complete, you can switch to Live Mode</p>
        </div>
      </div>
    </div>
  )
}
