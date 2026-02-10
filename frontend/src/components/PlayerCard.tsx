import { PlayerState } from '../types'
import { formatCurrency, getRiskScore, resolvePlayerStatus } from '../utils/player'
import { StatusBadge } from './StatusBadge'
import { useState, useEffect } from 'react'

interface PlayerCardProps {
  player: PlayerState
  onSelect: () => void
}

export function PlayerCard({ player, onSelect }: PlayerCardProps) {
  const status = resolvePlayerStatus(player)
  const risk = Math.round(getRiskScore(player) * 100)
  const [flash, setFlash] = useState(false)

  useEffect(() => {
    // Flash when player state changes
    setFlash(true)
    const timer = setTimeout(() => setFlash(false), 400)
    return () => clearTimeout(timer)
  }, [player.last_bet, player.flagged_by_monitor, player.intervention, player.churned])

  return (
    <button
      type="button"
      className={`player-card ${flash ? 'flash' : ''}`}
      data-status={status.key}
      onClick={onSelect}
    >
      <div className="player-card__header">
        <span className="player-id">Player #{player.player_id}</span>
        <StatusBadge label={status.label} tone={status.tone} />
      </div>

      <div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
          Churn Risk Score
        </div>
        <div className="risk-score-large">{risk}%</div>
      </div>

      {player.last_bet && (
        <div className="last-activity">
          {formatCurrency(player.last_bet.amount)} • {player.last_bet.won ? 'Won' : 'Lost'}
        </div>
      )}

      {!player.last_bet && (
        <div className="last-activity">No recent activity</div>
      )}
    </button>
  )
}
