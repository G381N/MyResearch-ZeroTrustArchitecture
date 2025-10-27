'use client'

import { useEffect, useState } from 'react'

interface TrustScoreGaugeProps {
  score: number
  size?: number
  strokeWidth?: number
}

export default function TrustScoreGauge({ score, size = 200, strokeWidth = 8 }: TrustScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0)
  
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const strokeDasharray = circumference
  const strokeDashoffset = circumference - (score / 100) * circumference
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedScore(score)
    }, 100)
    
    return () => clearTimeout(timer)
  }, [score])
  
  const getColor = (score: number) => {
    if (score >= 80) return '#10b981' // green
    if (score >= 60) return '#f59e0b' // yellow
    if (score >= 40) return '#f97316' // orange
    return '#ef4444' // red
  }
  
  const getStatus = (score: number) => {
    if (score >= 80) return 'Excellent'
    if (score >= 60) return 'Good'
    if (score >= 40) return 'Fair'
    if (score >= 20) return 'Poor'
    return 'Critical'
  }
  
  return (
    <div className="flex flex-col items-center space-y-4">
      <div className="relative" style={{ width: size, height: size }}>
        {/* Background circle */}
        <svg
          width={size}
          height={size}
          className="transform -rotate-90"
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="none"
            className="text-muted"
          />
          
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={getColor(animatedScore)}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-1000 ease-out"
            style={{
              strokeDasharray,
              strokeDashoffset: circumference - (animatedScore / 100) * circumference
            }}
          />
        </svg>
        
        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div 
            className="text-4xl font-bold transition-colors duration-1000"
            style={{ color: getColor(animatedScore) }}
          >
            {Math.round(animatedScore)}
          </div>
          <div className="text-sm text-muted-foreground">
            {getStatus(animatedScore)}
          </div>
        </div>
      </div>
      
      {/* Status indicator */}
      <div className="flex items-center space-x-2">
        <div 
          className="w-3 h-3 rounded-full"
          style={{ backgroundColor: getColor(animatedScore) }}
        />
        <span className="text-sm text-muted-foreground">
          Trust Score: {getStatus(animatedScore)}
        </span>
      </div>
    </div>
  )
}
