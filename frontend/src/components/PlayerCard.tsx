import { PlayerState } from '../types'
import { formatCurrency, getRiskScore, resolvePlayerStatus } from '../utils/player'
import { StatusBadge } from './StatusBadge'

interface PlayerCardProps {
  player: PlayerState
  onSelect: () => void
}

export function PlayerCard({ player, onSelect }: PlayerCardProps) {
  const status = resolvePlayerStatus(player)
  const risk = Math.round(getRiskScore(player) * 100)
  const betHistory = player.bet_history || []
  const totalWagered = betHistory.reduce((sum, bet) => sum + bet.amount, 0)
  const wins = betHistory.filter(bet => bet.won).length
  const winRate = betHistory.length ? Math.round((wins / betHistory.length) * 100) : 0

  return (
    <button type="button" className="player-card" data-status={status.key} onClick={onSelect}>
      <div className="player-card__top">
        <div>
          <p className="player-card__eyebrow">Player</p>
          <p className="player-card__title">#{player.player_id}</p>
        </div>
        <StatusBadge label={status.label} tone={status.tone} />
      </div>

      <div className="risk-score">
        <div>
          <div className="metric-label">Risk exposure</div>
          <p className="risk-score-value">{risk}%</p>
        </div>
        <div className="risk-score-label">{status.label}</div>
      </div>

      <div className="player-card__metrics">
        <div className="metric-tile">
          <div className="metric-label">Total wagers</div>
          <div className="metric-value">{formatCurrency(totalWagered)}</div>
        </div>
        <div className="metric-tile">
          <div className="metric-label">Win rate</div>
          <div className="metric-value">
            {betHistory.length ? `${winRate}%` : 'No bets'}
          </div>
        </div>
      </div>

      {player.last_bet && (
        <div className="metric-tile">
          <div className="metric-label">Last bet</div>
          <div className="metric-value">
            {formatCurrency(player.last_bet.amount)} / {player.last_bet.won ? 'Won' : 'Lost'}
          </div>
          <div className="stat-trend">State: {player.last_bet.emotional_state}</div>
        </div>
      )}
    </button>
  )
}
