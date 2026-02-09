import { PlayerState } from '../types'
import { formatCurrency, getRecentBets, getRiskScore, resolvePlayerStatus } from '../utils/player'
import { StatusBadge } from './StatusBadge'

interface PlayerDetailModalProps {
  player: PlayerState
  onClose: () => void
}

export function PlayerDetailModal({ player, onClose }: PlayerDetailModalProps) {
  const status = resolvePlayerStatus(player)
  const risk = Math.round(getRiskScore(player) * 100)
  const recentBets = getRecentBets(player, 6)
  const betHistory = player.bet_history || []
  const totalWagered = betHistory.reduce((sum, bet) => sum + bet.amount, 0)
  const wins = betHistory.filter(bet => bet.won).length
  const winRate = betHistory.length ? Math.round((wins / betHistory.length) * 100) : 0
  const avgBet = betHistory.length ? totalWagered / betHistory.length : 0

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Player ${player.player_id} detail`}
        onClick={event => event.stopPropagation()}
      >
        <header className="modal-header">
          <div>
            <p className="eyebrow">Player profile</p>
            <h2>Player #{player.player_id}</h2>
          </div>
          <div className="modal-header-actions">
            <StatusBadge label={status.label} tone={status.tone} />
            <button type="button" className="ghost-button" onClick={onClose}>
              Close
            </button>
          </div>
        </header>

        <div className="modal-body">
          <section className="modal-section">
            <h3 className="section-title">Snapshot</h3>
            <div className="info-grid">
              <InfoTile label="Risk" value={`${risk}%`} />
              <InfoTile label="Total wagers" value={formatCurrency(totalWagered)} />
              <InfoTile label="Average bet" value={formatCurrency(avgBet)} />
              <InfoTile label="Win rate" value={betHistory.length ? `${winRate}%` : 'No bets'} />
            </div>
          </section>

          <section className="modal-section">
            <h3 className="section-title">Monitoring</h3>
            <div className="info-grid">
              <InfoTile label="Flagged" value={player.flagged_by_monitor ? 'Yes' : 'No'} />
              <InfoTile label="Churned" value={player.churned ? 'Yes' : 'No'} />
              <InfoTile label="Intervention" value={player.intervention ? 'Scheduled' : 'None'} />
              <InfoTile label="Bets tracked" value={betHistory.length.toString()} />
            </div>
            {player.flagged_by_monitor && (
              <div className="alert" data-tone="info">
                Player flagged by the risk monitor for volatility and loss patterns.
              </div>
            )}
            {player.churned && (
              <div className="alert" data-tone="critical">
                Player marked as churned. Monitor for potential winback opportunities.
              </div>
            )}
          </section>

          {player.intervention && (
            <section className="modal-section">
              <h3 className="section-title">Intervention plan</h3>
              <div className="info-grid">
                <InfoTile label="Type" value={player.intervention.type?.toUpperCase() || 'Offer'} />
                <InfoTile label="Amount" value={formatCurrency(player.intervention.amount)} />
                <InfoTile label="Risk score" value={`${Math.round(player.intervention.risk_score * 100)}%`} />
              </div>
              <div className="alert" data-tone="warning">
                {player.intervention.message}
              </div>
              {player.intervention.reasoning && (
                <div className="alert" data-tone="info">
                  {player.intervention.reasoning}
                </div>
              )}
            </section>
          )}

          <section className="modal-section">
            <h3 className="section-title">Recent bets</h3>
            {recentBets.length === 0 ? (
              <div className="empty-state">No betting history available.</div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Amount</th>
                    <th>Result</th>
                    <th>Emotional state</th>
                    <th>Payout</th>
                  </tr>
                </thead>
                <tbody>
                  {recentBets.map((bet, index) => (
                    <tr key={`${player.player_id}-${index}`}>
                      <td>{formatCurrency(bet.amount)}</td>
                      <td>
                        <span className="tag">{bet.won ? 'Won' : 'Lost'}</span>
                      </td>
                      <td>{bet.emotional_state}</td>
                      <td>{bet.payout ? formatCurrency(bet.payout) : '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {player.activity_log && player.activity_log.length > 0 && (
            <section className="modal-section">
              <h3 className="section-title">Activity log</h3>
              <div className="activity-list">
                {player.activity_log.map((item, index) => (
                  <div key={`${item.timestamp}-${index}`} className="activity-item">
                    <span>{formatTimestamp(item.timestamp)}</span>
                    <span>{item.message}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-tile">
      <div className="info-label">{label}</div>
      <div className="info-value">{value}</div>
    </div>
  )
}

function formatTimestamp(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}
