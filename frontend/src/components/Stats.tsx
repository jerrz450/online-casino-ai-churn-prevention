import { SimulationStats } from '../types'

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
  const cards = [
    {
      label: 'Live Players',
      value: stats.active_players.toLocaleString(),
      trend: `${stats.total_bets.toLocaleString()} bets processed`
    },
    {
      label: 'Tracked Profiles',
      value: snapshot.tracked.toLocaleString(),
      trend: `${snapshot.flagged} flagged`
    },
    {
      label: 'High Risk',
      value: snapshot.highRisk.toLocaleString(),
      trend: `Avg risk ${Math.round(snapshot.avgRisk * 100)}%`
    },
    {
      label: 'Active Interventions',
      value: snapshot.interventions.toLocaleString(),
      trend: `${stats.total_interventions.toLocaleString()} sent`
    },
    {
      label: 'Churned',
      value: stats.churned_players.toLocaleString(),
      trend: `${snapshot.tracked - snapshot.churned} active`
    },
    {
      label: 'Tick',
      value: stats.tick.toLocaleString(),
      trend: 'Simulation clock'
    }
  ]

  return (
    <section className="stats-panel">
      <span className="connection-pill" data-state={connected ? 'online' : 'offline'}>
        <span className="pill-dot" />
        {connected ? 'Live stream' : 'Offline'}
      </span>
      <div className="stats-grid">
        {cards.map(card => (
          <div key={card.label} className="stat-card">
            <span className="stat-label">{card.label}</span>
            <span className="stat-value">{card.value}</span>
            <span className="stat-trend">{card.trend}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
