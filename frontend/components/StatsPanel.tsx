'use client'

import { LucideIcon } from 'lucide-react'

interface StatItem {
  label: string
  value: string
  icon: LucideIcon
  color: string
}

interface StatsPanelProps {
  title: string
  stats: StatItem[]
  eventCounts?: Record<string, number>
}

export default function StatsPanel({ title, stats, eventCounts }: StatsPanelProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      
      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <div key={index} className="flex items-center space-x-3 p-3 bg-muted/50 rounded-lg">
              <Icon className={`h-6 w-6 ${stat.color}`} />
              <div>
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </div>
            </div>
          )
        })}
      </div>
      
      {/* Event Type Breakdown */}
      {eventCounts && Object.keys(eventCounts).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-muted-foreground mb-3">Event Type Breakdown</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(eventCounts).map(([eventType, count]) => (
              <div key={eventType} className="flex items-center justify-between p-2 bg-muted/30 rounded">
                <span className="text-sm font-medium capitalize">
                  {eventType.replace('_', ' ')}
                </span>
                <span className="text-sm text-muted-foreground">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
