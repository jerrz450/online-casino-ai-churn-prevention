import { SimulationStats } from '../types'
import { useState, useEffect } from 'react'

interface StatsProps {
  stats: SimulationStats
  connected: boolean
  snapshot: {
    tracked: number
    highRisk: number
    flagged: number
    interventions: number
    avgRisk: number
    churned: number
  }
}

export function Stats({ stats, connected, snapshot }: StatsProps) {
  const [isSimulatorRunning, setIsSimulatorRunning] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const apiUrl = window.location.protocol + '//' + window.location.host

  useEffect(() => {
    // Check simulator status on mount
    fetch(`${apiUrl}/simulator/status`)
      .then(res => res.json())
      .then(data => setIsSimulatorRunning(data.running))
      .catch(() => {})
  }, [apiUrl])

  const handleStartStop = async () => {
    setIsLoading(true)
    try {
      const endpoint = isSimulatorRunning ? '/simulator/stop' : '/simulator/start'
      const response = await fetch(`${apiUrl}${endpoint}`, { method: 'POST' })
      const data = await response.json()

      if (data.status === 'started' || data.status === 'stopped') {
        setIsSimulatorRunning(!isSimulatorRunning)
      }
    } catch (error) {
      console.error('Failed to toggle simulator:', error)
    }
    setIsLoading(false)
  }
  const cards = [
    {
      label: 'Active Players',
      value: stats.active_players.toLocaleString(),
      description: 'Currently playing'
    },
    {
      label: 'High Risk Players',
      value: snapshot.highRisk.toLocaleString(),
      description: 'At risk of churning'
    },
    {
      label: 'AI Interventions Sent',
      value: snapshot.interventions.toLocaleString(),
      description: 'Offers being processed'
    }
  ]

  return (
    <section className="stats-panel">
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px' }}>
        <span className="connection-pill" data-state={connected ? 'online' : 'offline'}>
          <span className="pill-dot" />
          {connected ? 'Live stream' : 'Offline'}
        </span>
        <button
          onClick={handleStartStop}
          disabled={isLoading}
          style={{
            padding: '8px 16px',
            backgroundColor: isSimulatorRunning ? '#ef4444' : '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontWeight: '500',
            opacity: isLoading ? 0.6 : 1
          }}
        >
          {isLoading ? 'Loading...' : isSimulatorRunning ? 'Stop Simulator' : 'Start Simulator'}
        </button>
      </div>
      <div className="stats-grid">
        {cards.map(card => (
          <div key={card.label} className="stat-card">
            <span className="stat-label">{card.label}</span>
            <span className="stat-value">{card.value}</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{card.description}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
