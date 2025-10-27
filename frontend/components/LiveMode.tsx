'use client'

import { useState, useEffect } from 'react'
import { liveAPI } from '@/lib/api'
import { useWebSocketMessage } from '@/lib/websocket'
import EventLog from './EventLog'
import StatsPanel from './StatsPanel'
import TrustScoreGauge from './TrustScoreGauge'
import { Play, Square, Shield, AlertTriangle, TrendingDown } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface LiveModeProps {
  websocket: any
  systemStatus: any
}

interface LiveStats {
  totalEvents: number
  anomalyCount: number
  trustScore: number
  eventCounts: Record<string, number>
  averageConfidence: number
  sessionDuration: number
}

interface TrustHistory {
  timestamp: string
  score: number
}

export default function LiveMode({ websocket, systemStatus }: LiveModeProps) {
  const [isLive, setIsLive] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [events, setEvents] = useState<any[]>([])
  const [anomalies, setAnomalies] = useState<any[]>([])
  const [trustScore, setTrustScore] = useState(100)
  const [trustHistory, setTrustHistory] = useState<TrustHistory[]>([])
  const [stats, setStats] = useState<LiveStats>({
    totalEvents: 0,
    anomalyCount: 0,
    trustScore: 100,
    eventCounts: {},
    averageConfidence: 0,
    sessionDuration: 0
  })
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Handle WebSocket messages
  useWebSocketMessage(websocket, 'anomaly', (data) => {
    if (isLive) {
      // Add to both events and anomalies lists for Live Mode
      setEvents(prev => [data, ...prev.slice(0, 99)]) // Keep last 100 events
      setAnomalies(prev => [data, ...prev.slice(0, 49)]) // Keep last 50 anomalies
      setStats(prev => ({
        ...prev,
        anomalyCount: prev.anomalyCount + 1,
        totalEvents: prev.totalEvents + 1,
        eventCounts: {
          ...prev.eventCounts,
          [data.event_type]: (prev.eventCounts[data.event_type] || 0) + 1
        }
      }))
    }
  })

  useWebSocketMessage(websocket, 'trust_update', (data) => {
    if (isLive) {
      setTrustScore(data.current_score)
      setTrustHistory(prev => [
        ...prev.slice(-19), // Keep last 20 points
        { timestamp: new Date().toLocaleTimeString(), score: data.current_score }
      ])
      
      // Update stats with new trust score
      setStats(prev => ({
        ...prev,
        trustScore: data.current_score
      }))
    }
  })

  // Handle admin alerts
  useWebSocketMessage(websocket, 'alert', (data) => {
    if (isLive && data.type === 'trust_threshold_breach') {
      // Show browser notification if permission granted
      if (Notification.permission === 'granted') {
        new Notification('Zero Trust Alert', {
          body: data.message,
          icon: '/favicon.ico'
        })
      }
      
      // You could also trigger additional UI alerts here
      console.warn('Admin Alert:', data)
    }
  })

  useWebSocketMessage(websocket, 'session_update', (data) => {
    if (data.mode === 'live') {
      if (data.status === 'started') {
        setIsLive(true)
        setTrustScore(100)
        setTrustHistory([{ timestamp: new Date().toLocaleTimeString(), score: 100 }])
        setSuccess('Live mode started successfully')
        setError(null)
      } else if (data.status === 'stopped') {
        setIsLive(false)
        setSuccess('Live mode stopped')
        setError(null)
      }
    }
  })

  const startLive = async () => {
    try {
      setIsLoading(true)
      setError(null)
      setSuccess(null)
      
      const response = await liveAPI.start()
      
      if (response.data) {
        setIsLive(true)
        setTrustScore(response.data.trust_score)
        setTrustHistory([{ timestamp: new Date().toLocaleTimeString(), score: response.data.trust_score }])
        setEvents([])
        setAnomalies([])
        setSuccess('Live mode started')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start live mode')
    } finally {
      setIsLoading(false)
    }
  }

  const stopLive = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const response = await liveAPI.stop()
      
      if (response.data) {
        setIsLive(false)
        setSuccess('Live mode stopped')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to stop live mode')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await liveAPI.stats()
      const data = response.data
      
      setStats({
        totalEvents: data.total_events,
        anomalyCount: data.anomaly_count,
        trustScore: data.trust_score,
        eventCounts: data.event_counts,
        averageConfidence: data.average_confidence || 0,
        sessionDuration: data.session_duration || 0
      })
    } catch (err) {
      console.error('Error fetching live stats:', err)
    }
  }

  const fetchAnomalies = async () => {
    try {
      const response = await liveAPI.anomalies()
      setAnomalies(response.data)
    } catch (err) {
      console.error('Error fetching anomalies:', err)
    }
  }

  useEffect(() => {
    if (isLive) {
      fetchStats()
      fetchAnomalies()
      const interval = setInterval(() => {
        fetchStats()
        fetchAnomalies()
      }, 5000)
      
      return () => clearInterval(interval)
    }
  }, [isLive])

  const isTrustLow = trustScore < 20
  const trustColor = isTrustLow ? 'text-red-500' : trustScore < 50 ? 'text-yellow-500' : 'text-green-500'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Shield className="h-8 w-8 text-green-500" />
          <div>
            <h2 className="text-2xl font-bold">Live Mode</h2>
            <p className="text-muted-foreground">
              Real-time anomaly detection and trust scoring
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          {isLive && (
            <div className="flex items-center space-x-2 text-green-500">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium">Live Monitoring</span>
            </div>
          )}
          
          {isTrustLow && (
            <div className="flex items-center space-x-2 text-red-500">
              <AlertTriangle className="h-5 w-5" />
              <span className="text-sm font-medium">Low Trust Alert</span>
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

      {/* Trust Score Alert */}
      {isTrustLow && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-md p-4 alert-pulse">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <div>
              <div className="font-medium text-red-500">Critical Trust Score Alert</div>
              <div className="text-sm text-red-500/80">
                Trust score has dropped to {trustScore}. Immediate attention required.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Control Panel */}
      <div className="bg-card border border-border rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <div className={`text-2xl font-bold ${trustColor}`}>
                {trustScore}
              </div>
              <div className="text-sm text-muted-foreground">
                Trust Score
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {stats.anomalyCount} anomalies detected
              </span>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {!isLive ? (
              <button
                onClick={startLive}
                disabled={isLoading || !systemStatus?.model_trained}
                className="flex items-center space-x-2 px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="h-4 w-4" />
                <span>{isLoading ? 'Starting...' : 'Start Live Mode'}</span>
              </button>
            ) : (
              <button
                onClick={stopLive}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Square className="h-4 w-4" />
                <span>{isLoading ? 'Stopping...' : 'Stop Live Mode'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Trust Score Gauge and Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Trust Score</h3>
          <TrustScoreGauge score={trustScore} />
        </div>
        
        <div className="bg-card border border-border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Trust Score Over Time</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trustHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="score" 
                  stroke="#8884d8" 
                  strokeWidth={2}
                  dot={{ fill: '#8884d8', strokeWidth: 2, r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Stats Panel */}
      <StatsPanel
        title="Live Monitoring Statistics"
        stats={[
          {
            label: 'Total Events',
            value: stats.totalEvents.toString(),
            icon: Shield,
            color: 'text-blue-500'
          },
          {
            label: 'Anomalies',
            value: stats.anomalyCount.toString(),
            icon: AlertTriangle,
            color: 'text-red-500'
          },
          {
            label: 'Avg Confidence',
            value: `${Math.round(stats.averageConfidence * 100)}%`,
            icon: TrendingDown,
            color: 'text-yellow-500'
          }
        ]}
        eventCounts={stats.eventCounts}
      />

      {/* Anomalous Events Log */}
      <div className="bg-card border border-border rounded-lg">
        <div className="p-4 border-b border-border">
          <h3 className="text-lg font-semibold">Anomalous Events</h3>
          <p className="text-sm text-muted-foreground">
            {isLive 
              ? 'Real-time anomaly detection results...' 
              : 'Start live mode to begin anomaly detection'
            }
          </p>
        </div>
        
        <EventLog
          events={anomalies}
          showAnomalies={true}
          isLive={isLive}
          emptyMessage={
            isLive 
              ? 'No anomalies detected yet...' 
              : 'Start live mode to begin anomaly detection'
          }
        />
      </div>
    </div>
  )
}
