import { useMemo } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { Stats } from './components/Stats'
import { PlayerGrid } from './components/PlayerGrid'
import { getRiskScore } from './utils/player'

export default function App() {
  const wsUrl = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws'
  const { connected, players, stats } = useWebSocket(wsUrl)

  const playerList = useMemo(
    () => Object.values(players).sort((a, b) => a.player_id - b.player_id),
    [players]
  )

  const snapshot = useMemo(() => {
    const totals = {
      tracked: playerList.length,
      flagged: 0,
      interventions: 0,
      highRisk: 0,
      churnedLocal: 0,
      avgRisk: 0
    }

    if (!playerList.length) {
      return totals
    }

    let riskSum = 0
    playerList.forEach(player => {
      if (player.flagged_by_monitor) totals.flagged += 1
      if (player.intervention) totals.interventions += 1
      if (player.intervention || player.flagged_by_monitor || player.churned) {
        totals.highRisk += 1
      }
      if (player.churned) totals.churnedLocal += 1
      riskSum += getRiskScore(player)
    })
    totals.avgRisk = riskSum / playerList.length
    return totals
  }, [playerList])

  return (
    <div className="app-shell">
      <div className="app-container">
        <header className="app-header">
          <div>
            <p className="eyebrow">Command Center</p>
            <h1 className="app-title">Casino Churn Detection</h1>
            <p className="app-subtitle">Real-time AI-powered churn prevention</p>
          </div>
          <div className="header-meta">
            <span>Profiles tracked: {snapshot.tracked}</span>
            <span>Tick {stats.tick}</span>
          </div>
        </header>

        <Stats
          stats={stats}
          connected={connected}
          snapshot={{
            tracked: snapshot.tracked,
            highRisk: snapshot.highRisk,
            flagged: snapshot.flagged,
            interventions: snapshot.interventions,
            avgRisk: snapshot.avgRisk,
            churned: snapshot.churnedLocal
          }}
        />

        <section className="panel">
          <h2 className="panel-title">Player Monitoring</h2>
          <PlayerGrid players={playerList} />
        </section>
      </div>
    </div>
  )
}
