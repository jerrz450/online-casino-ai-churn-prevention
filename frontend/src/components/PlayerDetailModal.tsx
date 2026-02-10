import { PlayerState } from '../types'
import { formatCurrency, getRiskScore, getRecentBets, resolvePlayerStatus } from '../utils/player'
import { StatusBadge } from './StatusBadge'

interface PlayerDetailModalProps {
  player: PlayerState
  onClose: () => void
}

export function PlayerDetailModal({ player, onClose }: PlayerDetailModalProps) {
  const status = resolvePlayerStatus(player)
  const risk = Math.round(getRiskScore(player) * 100)
  const recentBets = getRecentBets(player, 10)
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
            <p className="eyebrow">Player Profile</p>
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
            <h3 className="section-title">Player Stats</h3>
            <div className="info-grid">
              <InfoTile label="Churn Risk Score" value={`${risk}%`} />
              <InfoTile label="Current Status" value={status.label} />
              <InfoTile label="Total Wagered" value={formatCurrency(totalWagered)} />
              <InfoTile label="Average Bet" value={formatCurrency(avgBet)} />
              <InfoTile label="Win Rate" value={betHistory.length ? `${winRate}% (${wins}/${betHistory.length})` : 'No bets'} />
              <InfoTile label="Total Bets" value={betHistory.length.toString()} />
            </div>
          </section>

          <section className="modal-section">
            <h3 className="section-title">Monitoring Status</h3>
            <div className="info-grid">
              <InfoTile label="Flagged by Monitor" value={player.flagged_by_monitor ? 'Yes' : 'No'} />
              <InfoTile label="Churned" value={player.churned ? 'Yes' : 'No'} />
              <InfoTile label="Intervention Status" value={player.intervention ? 'Active' : 'None'} />
            </div>
          </section>

          {player.intervention && (
            <section className="modal-section">
              <h3 className="section-title">AI Intervention Details</h3>
              <div className="info-grid">
                <InfoTile label="Intervention Type" value={player.intervention.type?.toUpperCase() || 'OFFER'} />
                <InfoTile label="Offer Amount" value={formatCurrency(player.intervention.amount)} />
                <InfoTile label="Risk at Intervention" value={`${Math.round(player.intervention.risk_score * 100)}%`} />
              </div>

              <div style={{ marginTop: '16px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  MESSAGE TO PLAYER
                </div>
                <div className="intervention-message">
                  {player.intervention.message}
                </div>
              </div>

              {player.intervention.reasoning && (
                <div style={{ marginTop: '16px' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    AI REASONING
                  </div>
                  <div className="intervention-message" style={{ borderLeft: '3px solid var(--info)' }}>
                    {player.intervention.reasoning}
                  </div>
                </div>
              )}
            </section>
          )}

          <section className="modal-section">
            <h3 className="section-title">Betting History (Last {Math.min(recentBets.length, 10)} Bets)</h3>
            {recentBets.length === 0 ? (
              <div className="empty-state">No betting history available.</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      <th style={{ textAlign: 'left', padding: '10px 8px', color: 'var(--text-muted)', fontWeight: '500' }}>Amount</th>
                      <th style={{ textAlign: 'left', padding: '10px 8px', color: 'var(--text-muted)', fontWeight: '500' }}>Result</th>
                      <th style={{ textAlign: 'left', padding: '10px 8px', color: 'var(--text-muted)', fontWeight: '500' }}>Payout</th>
                      <th style={{ textAlign: 'left', padding: '10px 8px', color: 'var(--text-muted)', fontWeight: '500' }}>Emotional State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentBets.map((bet, index) => (
                      <tr key={`${player.player_id}-${index}`} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '12px 8px' }}>{formatCurrency(bet.amount)}</td>
                        <td style={{ padding: '12px 8px' }}>
                          <span style={{
                            display: 'inline-block',
                            padding: '4px 10px',
                            borderRadius: '999px',
                            fontSize: '0.8rem',
                            fontWeight: '600',
                            background: bet.won ? 'rgba(82, 196, 26, 0.1)' : 'rgba(255, 77, 79, 0.1)',
                            color: bet.won ? 'var(--success)' : 'var(--critical)'
                          }}>
                            {bet.won ? 'Won' : 'Lost'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 8px' }}>{bet.payout ? formatCurrency(bet.payout) : '—'}</td>
                        <td style={{ padding: '12px 8px', color: 'var(--text-muted)' }}>{bet.emotional_state}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {player.activity_log && player.activity_log.length > 0 && (
            <section className="modal-section">
              <h3 className="section-title">Activity Log</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {player.activity_log.map((item, index) => (
                  <div key={`${item.timestamp}-${index}`} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: '16px',
                    fontSize: '0.85rem',
                    color: 'var(--text-muted)',
                    borderBottom: '1px solid var(--border)',
                    paddingBottom: '8px'
                  }}>
                    <span style={{ fontWeight: '500' }}>{formatTimestamp(item.timestamp)}</span>
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
