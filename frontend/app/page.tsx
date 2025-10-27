'use client'

import { useState, useEffect } from 'react'
import { useWebSocket } from '@/lib/websocket'
import { useSystemStatus } from '@/lib/websocket'
import TrainingMode from '@/components/TrainingMode'
import LiveMode from '@/components/LiveMode'
import AdminMode from '@/components/AdminMode'
import { Activity, Shield, Settings, AlertTriangle } from 'lucide-react'

const WS_URL = process.env.WS_URL || 'ws://localhost:8000/ws'

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<'training' | 'live' | 'admin'>('training')
  const [systemStatus, setSystemStatus] = useState<any>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  
  const websocket = useWebSocket(WS_URL)
  const { status, isLoading, error } = useSystemStatus()
  
  useEffect(() => {
    if (status) {
      setSystemStatus(status)
    }
  }, [status])
  
  // Handle WebSocket messages
  useEffect(() => {
    if (websocket.lastMessage) {
      const { type, data } = websocket.lastMessage
      
      switch (type) {
        case 'alert':
          setAlerts(prev => [...prev, { ...data, id: Date.now(), timestamp: new Date() }])
          break
          case 'session_update':
            setSystemStatus((prev: any) => ({ ...prev, ...data }))
          break
        case 'trust_update':
          // Trust score updates are handled in LiveMode component
          break
        case 'anomaly':
          // Anomaly notifications are handled in LiveMode component
          break
      }
    }
  }, [websocket.lastMessage])
  
  // Auto-remove alerts after 10 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setAlerts(prev => prev.filter(alert => Date.now() - alert.id < 10000))
    }, 1000)
    
    return () => clearInterval(timer)
  }, [])
  
  const tabs = [
    {
      id: 'training',
      label: 'Training Mode',
      icon: Activity,
      description: 'Collect and learn from system events'
    },
    {
      id: 'live',
      label: 'Live Mode',
      icon: Shield,
      description: 'Monitor and detect anomalies in real-time'
    },
    {
      id: 'admin',
      label: 'Admin Mode',
      icon: Settings,
      description: 'Manage anomalies and system settings'
    }
  ]
  
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading system status...</p>
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-destructive mb-2">Connection Error</h1>
          <p className="text-muted-foreground mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Shield className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold">Zero Trust Architecture</h1>
                <p className="text-sm text-muted-foreground">AI-based behavior tracking system</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Connection Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${
                  websocket.isConnected ? 'bg-green-500' : 'bg-red-500'
                }`} />
                <span className="text-sm text-muted-foreground">
                  {websocket.isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {/* System Status */}
              {systemStatus && (
                <div className="text-sm text-muted-foreground">
                  {systemStatus.training_active && <span className="text-blue-500">Training</span>}
                  {systemStatus.live_active && <span className="text-green-500">Live</span>}
                  {!systemStatus.training_active && !systemStatus.live_active && (
                    <span className="text-muted-foreground">Idle</span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
      
      {/* Navigation Tabs */}
      <nav className="border-b border-border bg-card">
        <div className="container mx-auto px-4">
          <div className="flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center space-x-2 py-4 px-2 border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <div className="text-left">
                    <div className="font-medium">{tab.label}</div>
                    <div className="text-xs text-muted-foreground">{tab.description}</div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </nav>
      
      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        {activeTab === 'training' && <TrainingMode websocket={websocket} />}
        {activeTab === 'live' && <LiveMode websocket={websocket} systemStatus={systemStatus} />}
        {activeTab === 'admin' && <AdminMode websocket={websocket} systemStatus={systemStatus} />}
      </main>
      
      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="fixed top-4 right-4 space-y-2 z-50">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 rounded-md shadow-lg max-w-sm ${
                alert.type === 'trust_score_low'
                  ? 'bg-destructive text-destructive-foreground'
                  : 'bg-card text-card-foreground border border-border'
              }`}
            >
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-5 w-5" />
                <div>
                  <div className="font-medium">{alert.message}</div>
                  {alert.trust_score && (
                    <div className="text-sm opacity-90">
                      Trust Score: {alert.trust_score}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
