'use client'

import { useState, useEffect } from 'react'
import { adminAPI } from '@/lib/api'
import { useWebSocketMessage } from '@/lib/websocket'
import { AlertTriangle, CheckCircle, RotateCcw, Settings, Database, Brain, Shield, Power } from 'lucide-react'

interface AdminModeProps {
  websocket: any
  systemStatus: any
}

interface Anomaly {
  id: number
  event_id: number
  confidence_score: number
  is_resolved: boolean
  created_at: string
  event: {
    id: number
    timestamp: string
    event_type: string
    metadata: any
    trust_impact: number
  }
}

interface AdminStats {
  sessions: {
    training_sessions: number
    live_sessions: number
    total_sessions: number
  }
  events: {
    total_events: number
    anomaly_events: number
    normal_events: number
  }
  anomalies: {
    total_anomalies: number
    resolved_anomalies: number
    unresolved_anomalies: number
  }
  model: {
    is_trained: boolean
    training_data_count: number
  }
  trust_score: {
    current_score: number
  }
  accuracy: {
    admin_accuracy: number
    precision: number
  }
}

interface PerformanceMetrics {
  attack_categories: {
    [key: string]: {
      precision: number
      recall: number
      f1_score: number
      total_detected: number
      true_positives: number
      false_positives: number
    }
  }
  overall: {
    precision: number
    recall: number
    f1_score: number
    total_anomalies: number
    admin_corrections: number
  }
  metadata: {
    calculation_method: string
    note: string
    timestamp: string
  }
}

export default function AdminMode({ websocket, systemStatus }: AdminModeProps) {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [showExitConfirm, setShowExitConfirm] = useState(false)
  const [showMetrics, setShowMetrics] = useState(false)
  const [testMode, setTestMode] = useState(false)

  // Handle WebSocket messages
  useWebSocketMessage(websocket, 'anomaly', (data) => {
    // Add new anomaly to the list
    setAnomalies(prev => [data, ...prev])
  })

  useWebSocketMessage(websocket, 'session_update', (data) => {
    if (data.type === 'anomaly_resolved') {
      // Remove resolved anomaly from the list
      setAnomalies(prev => prev.filter(anomaly => anomaly.id !== data.anomaly_id))
      setSuccess(`Anomaly ${data.anomaly_id} marked as normal`)
    }
  })

  // Handle admin alerts
  useWebSocketMessage(websocket, 'alert', (data) => {
    if (data.type === 'trust_threshold_breach') {
      setError(`CRITICAL ALERT: ${data.message}`)
      
      // Show browser notification if permission granted
      if (Notification.permission === 'granted') {
        new Notification('Zero Trust CRITICAL ALERT', {
          body: data.message,
          icon: '/favicon.ico',
          requireInteraction: true // Keep notification until user interacts
        })
      }
      
      console.error('Critical Trust Alert:', data)
    }
  })

  // Handle trust score updates in stats
  useWebSocketMessage(websocket, 'trust_update', (data) => {
    if (stats) {
      setStats(prev => ({
        ...prev,
        trust_score: {
          current_score: data.current_score
        }
      }))
    }
  })

  const fetchAnomalies = async () => {
    try {
      setIsLoading(true)
      // Fetch all anomalies (both resolved and unresolved) so admin can see everything
      const response = await adminAPI.anomalies({})
      setAnomalies(response.data)
    } catch (err: any) {
      setError('Failed to fetch anomalies')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await adminAPI.stats()
      setStats(response.data)
    } catch (err: any) {
      console.error('Error fetching admin stats:', err)
    }
  }

  const fetchPerformanceMetrics = async () => {
    try {
      setIsLoading(true)
      setError(null) // Clear any previous errors
      const response = await adminAPI.performanceMetrics()
      
      // Validate response structure
      if (response.data && typeof response.data === 'object') {
        setPerformanceMetrics(response.data)
        setShowMetrics(true)
      } else {
        setError('Invalid performance metrics data received')
      }
    } catch (err: any) {
      console.error('Performance metrics error:', err)
      let errorMessage = 'Failed to fetch performance metrics'
      
      if (err.response?.data) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail
        } else if (typeof err.response.data.message === 'string') {
          errorMessage = err.response.data.message
        }
      }
      
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const toggleTestMode = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const response = await adminAPI.toggleTestMode(!testMode)
      
      if (response.data) {
        setTestMode(!testMode)
        setSuccess(`Test mode ${!testMode ? 'enabled' : 'disabled'}. ${!testMode ? 'Time-based anomaly detection disabled.' : 'Time-based anomaly detection enabled.'}`)
      }
    } catch (err: any) {
      const errorMessage = typeof err.response?.data?.detail === 'string' 
        ? err.response.data.detail 
        : 'Failed to toggle test mode'
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const markAsNormal = async (anomalyId: number) => {
    try {
      setIsLoading(true)
      setError(null)
      
      const response = await adminAPI.markNormal(anomalyId)
      
      if (response.data) {
        setSuccess(`Anomaly ${anomalyId} marked as normal. Trust restored: ${response.data.trust_restored}`)
        // Update the anomaly in local list to show as resolved instead of removing it
        setAnomalies(prev => prev.map(anomaly => 
          anomaly.id === anomalyId 
            ? { ...anomaly, is_resolved: true, resolved_by: 'admin', resolved_at: new Date().toISOString() }
            : anomaly
        ))
      }
    } catch (err: any) {
      const errorMessage = typeof err.response?.data?.detail === 'string' 
        ? err.response.data.detail 
        : 'Failed to mark anomaly as normal'
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const resetSystem = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const response = await adminAPI.reset()
      
      if (response.data) {
        setSuccess('System reset completed successfully')
        setAnomalies([])
        setShowResetConfirm(false)
        // Refresh stats
        fetchStats()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset system')
    } finally {
      setIsLoading(false)
    }
  }

  const exitSystem = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      const response = await adminAPI.exit()
      
      if (response.data) {
        setSuccess('System shutdown initiated')
        setShowExitConfirm(false)
        // Show shutdown message
        setTimeout(() => {
          alert('System has been shut down. Please run ./start.sh to restart.')
        }, 2000)
      }
    } catch (err: any) {
      setError('Failed to exit system')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchTestModeStatus = async () => {
    try {
      const response = await adminAPI.systemStatus()
      if (response.data && response.data.test_mode !== undefined) {
        setTestMode(response.data.test_mode)
      }
    } catch (err) {
      console.error('Error fetching test mode status:', err)
    }
  }

  useEffect(() => {
    fetchAnomalies()
    fetchStats()
    fetchTestModeStatus()
    
    const interval = setInterval(() => {
      fetchStats()
    }, 10000) // Update stats every 10 seconds
    
    return () => clearInterval(interval)
  }, [])

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Settings className="h-8 w-8 text-purple-500" />
          <div>
            <h2 className="text-2xl font-bold">Admin Mode</h2>
            <p className="text-muted-foreground">
              Manage anomalies and system configuration
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <button
            onClick={fetchPerformanceMetrics}
            disabled={isLoading}
            className="px-3 py-1 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
          >
            {isLoading ? 'Loading...' : 'View Performance Metrics'}
          </button>
          <div className="text-sm text-muted-foreground">
            {anomalies.filter(a => !a.is_resolved).length} unresolved / {anomalies.length} total anomalies
          </div>
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

      {/* System Statistics */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <Database className="h-5 w-5 text-blue-500" />
              <div>
                <div className="text-2xl font-bold">{stats.sessions.total_sessions}</div>
                <div className="text-sm text-muted-foreground">Total Sessions</div>
              </div>
            </div>
          </div>
          
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              <div>
                <div className="text-2xl font-bold">{stats.anomalies.total_anomalies}</div>
                <div className="text-sm text-muted-foreground">Total Anomalies</div>
              </div>
            </div>
          </div>
          
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <Brain className="h-5 w-5 text-green-500" />
              <div>
                <div className="text-2xl font-bold">
                  {Math.round((stats.accuracy.admin_accuracy || 0) * 100)}%
                </div>
                <div className="text-sm text-muted-foreground">Admin Accuracy</div>
              </div>
            </div>
          </div>
          
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <Shield className="h-5 w-5 text-purple-500" />
              <div>
                <div className="text-2xl font-bold">{stats.trust_score.current_score}</div>
                <div className="text-sm text-muted-foreground">Current Trust Score</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      {showMetrics && performanceMetrics && (
        <div className="bg-card border border-border rounded-lg">
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Real Performance Metrics</h3>
              <button
                onClick={() => setShowMetrics(false)}
                className="px-3 py-1 text-sm bg-muted text-muted-foreground rounded-md hover:bg-muted/80"
              >
                Hide
              </button>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              {performanceMetrics.metadata?.note || 'Performance metrics based on system data and admin feedback.'}
            </p>
          </div>
          
          <div className="p-4">
            {/* Overall Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-muted/50 rounded-lg p-4">
                <div className="text-2xl font-bold text-blue-500">
                  {((performanceMetrics.overall?.precision || 0) * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-muted-foreground">Overall Precision</div>
              </div>
              <div className="bg-muted/50 rounded-lg p-4">
                <div className="text-2xl font-bold text-green-500">
                  {((performanceMetrics.overall?.recall || 0) * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-muted-foreground">Overall Recall</div>
              </div>
              <div className="bg-muted/50 rounded-lg p-4">
                <div className="text-2xl font-bold text-purple-500">
                  {((performanceMetrics.overall?.f1_score || 0) * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-muted-foreground">Overall F1-Score</div>
              </div>
            </div>

            {/* Attack Categories Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border">
                  <tr>
                    <th className="text-left p-3 font-medium">Attack Category</th>
                    <th className="text-center p-3 font-medium">Precision</th>
                    <th className="text-center p-3 font-medium">Recall</th>
                    <th className="text-center p-3 font-medium">F1-Score</th>
                    <th className="text-center p-3 font-medium">Total Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {performanceMetrics.attack_categories && Object.keys(performanceMetrics.attack_categories).length > 0 ? (
                    Object.entries(performanceMetrics.attack_categories).map(([category, metrics]) => (
                      <tr key={category} className="border-b border-border hover:bg-muted/50">
                        <td className="p-3 font-medium">{category}</td>
                        <td className="p-3 text-center">
                          <span className="inline-block px-2 py-1 rounded bg-blue-100 text-blue-800">
                            {((metrics?.precision || 0) * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="p-3 text-center">
                          <span className="inline-block px-2 py-1 rounded bg-green-100 text-green-800">
                            {((metrics?.recall || 0) * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="p-3 text-center">
                          <span className="inline-block px-2 py-1 rounded bg-purple-100 text-purple-800">
                            {((metrics?.f1_score || 0) * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="p-3 text-center">{metrics?.total_detected || 0}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="text-center p-8 text-muted-foreground">
                        No attack category data available yet. Generate some anomalies first.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Summary Stats */}
            <div className="mt-4 p-4 bg-muted/30 rounded-lg">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="font-medium">Total Anomalies</div>
                  <div className="text-muted-foreground">{performanceMetrics.overall?.total_anomalies || 0}</div>
                </div>
                <div>
                  <div className="font-medium">Admin Corrections</div>
                  <div className="text-muted-foreground">{performanceMetrics.overall?.admin_corrections || 0}</div>
                </div>
                <div>
                  <div className="font-medium">Calculation Method</div>
                  <div className="text-muted-foreground">Admin Feedback</div>
                </div>
                <div>
                  <div className="font-medium">Last Updated</div>
                  <div className="text-muted-foreground">
                    {performanceMetrics.metadata?.timestamp 
                      ? new Date(performanceMetrics.metadata.timestamp).toLocaleString()
                      : 'Just now'
                    }
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Anomalies Table */}
      <div className="bg-card border border-border rounded-lg">
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Detected Anomalies</h3>
            <button
              onClick={fetchAnomalies}
              disabled={isLoading}
              className="px-3 py-1 text-sm bg-muted text-muted-foreground rounded-md hover:bg-muted/80 disabled:opacity-50"
            >
              {isLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border">
              <tr>
                <th className="text-left p-4 font-medium">Event</th>
                <th className="text-left p-4 font-medium">Type</th>
                <th className="text-left p-4 font-medium">Confidence</th>
                <th className="text-left p-4 font-medium">Trust Impact</th>
                <th className="text-left p-4 font-medium">Timestamp</th>
                <th className="text-left p-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center p-8 text-muted-foreground">
                    No anomalies detected
                  </td>
                </tr>
              ) : (
                anomalies.map((anomaly) => (
                  <tr key={anomaly.id} className={`border-b border-border hover:bg-muted/50 ${anomaly.is_resolved ? 'opacity-50 bg-muted/30' : ''}`}>
                    <td className="p-4">
                      <div className={`font-medium ${anomaly.is_resolved ? 'line-through text-muted-foreground' : ''}`}>
                        {anomaly.event?.metadata?.process_name || anomaly.event?.metadata?.command || 'Unknown'}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {anomaly.event?.metadata?.user_id || 'System'}
                        {anomaly.is_resolved && (
                          <span className="ml-2 px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                            Marked as Normal by Admin
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`font-medium ${getEventTypeColor(anomaly.event.event_type)}`}>
                        {anomaly.event.event_type}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-muted rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full" 
                            style={{ width: `${anomaly.confidence_score * 100}%` }}
                          />
                        </div>
                        <span className="text-sm">
                          {Math.round(anomaly.confidence_score * 100)}%
                        </span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="text-red-500 font-medium">
                        -{Math.abs(anomaly.event.trust_impact)}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-muted-foreground">
                      {formatTimestamp(anomaly.created_at)}
                    </td>
                    <td className="p-4">
                      {anomaly.is_resolved ? (
                        <div className="flex items-center space-x-1 px-3 py-1 text-sm bg-green-100 text-green-700 rounded-md">
                          <CheckCircle className="h-4 w-4" />
                          <span>Marked Normal</span>
                        </div>
                      ) : (
                        <button
                          onClick={() => markAsNormal(anomaly.id)}
                          disabled={isLoading}
                          className="flex items-center space-x-1 px-3 py-1 text-sm bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50"
                        >
                          <CheckCircle className="h-4 w-4" />
                          <span>Mark Normal</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* System Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Test Mode Toggle */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Test Mode</h3>
              <p className="text-sm text-muted-foreground">
                Disable time-based anomaly detection for testing
              </p>
            </div>
            
            <button
              onClick={toggleTestMode}
              disabled={isLoading}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                testMode 
                  ? 'bg-orange-500 text-white hover:bg-orange-600' 
                  : 'bg-green-500 text-white hover:bg-green-600'
              } disabled:opacity-50`}
            >
              {testMode ? 'Disable Test Mode' : 'Enable Test Mode'}
            </button>
          </div>
          
          {testMode && (
            <div className="mt-3 p-3 bg-orange-100 border border-orange-200 rounded-md">
              <p className="text-sm text-orange-800">
                ⚠️ Test mode enabled. Time-based anomaly detection is disabled.
              </p>
            </div>
          )}
        </div>
        {/* System Reset */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">System Reset</h3>
              <p className="text-sm text-muted-foreground">
                Reset the entire system, including all data, models, and trust scores
              </p>
            </div>
            
            <button
              onClick={() => setShowResetConfirm(true)}
              disabled={isLoading}
              className="flex items-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Reset System</span>
            </button>
          </div>
        </div>

        {/* System Exit */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Exit System</h3>
              <p className="text-sm text-muted-foreground">
                Shutdown all services and exit the Zero Trust Architecture System
              </p>
            </div>
            
            <button
              onClick={() => setShowExitConfirm(true)}
              disabled={isLoading}
              className="flex items-center space-x-2 px-4 py-2 bg-orange-500 text-white rounded-md hover:bg-orange-600 disabled:opacity-50"
            >
              <Power className="h-4 w-4" />
              <span>Exit System</span>
            </button>
          </div>
        </div>
      </div>

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center space-x-2 mb-4">
              <AlertTriangle className="h-6 w-6 text-red-500" />
              <h3 className="text-lg font-semibold">Confirm System Reset</h3>
            </div>
            
            <p className="text-muted-foreground mb-6">
              This will permanently delete all training data, live sessions, anomalies, and reset the ML model. 
              This action cannot be undone.
            </p>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={resetSystem}
                disabled={isLoading}
                className="flex-1 px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50"
              >
                {isLoading ? 'Resetting...' : 'Yes, Reset System'}
              </button>
              
              <button
                onClick={() => setShowResetConfirm(false)}
                disabled={isLoading}
                className="flex-1 px-4 py-2 bg-muted text-muted-foreground rounded-md hover:bg-muted/80"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Exit Confirmation Modal */}
      {showExitConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center space-x-2 mb-4">
              <Power className="h-6 w-6 text-orange-500" />
              <h3 className="text-lg font-semibold">Confirm System Exit</h3>
            </div>
            
            <p className="text-muted-foreground mb-6">
              This will shutdown all services (backend and frontend) and exit the Zero Trust Architecture System. 
              You will need to run ./start.sh again to restart the system.
            </p>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={exitSystem}
                disabled={isLoading}
                className="flex-1 px-4 py-2 bg-orange-500 text-white rounded-md hover:bg-orange-600 disabled:opacity-50"
              >
                {isLoading ? 'Exiting...' : 'Yes, Exit System'}
              </button>
              
              <button
                onClick={() => setShowExitConfirm(false)}
                disabled={isLoading}
                className="flex-1 px-4 py-2 bg-muted text-muted-foreground rounded-md hover:bg-muted/80"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
