import { PlayerState } from '../types'

export type PlayerStatusKey = 'active' | 'flagged' | 'intervened' | 'churned'
export type StatusTone = 'success' | 'info' | 'warning' | 'critical'

interface PlayerStatusMeta {
  key: PlayerStatusKey
  label: string
  tone: StatusTone
}

const statusMap: Record<PlayerStatusKey, PlayerStatusMeta> = {
  active: { key: 'active', label: 'Active', tone: 'success' },
  flagged: { key: 'flagged', label: 'Flagged', tone: 'info' },
  intervened: { key: 'intervened', label: 'Offer Sent', tone: 'warning' },
  churned: { key: 'churned', label: 'Churned', tone: 'critical' }
}

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0
})

export function resolvePlayerStatus(player: PlayerState): PlayerStatusMeta {
  if (player.churned) return statusMap.churned
  if (player.intervention) return statusMap.intervened
  if (player.flagged_by_monitor) return statusMap.flagged
  return statusMap.active
}

export function getRiskScore(player: PlayerState) {
  if (player.churned) return 1
  if (player.intervention?.risk_score) return clamp(player.intervention.risk_score, 0, 1)
  if (player.flagged_by_monitor) return 0.65
  return 0.25
}

export function formatCurrency(value: number | null | undefined) {
  return currency.format(Math.max(0, value ?? 0))
}

export function getRecentBets(player: PlayerState, limit = 5) {
  const bets = player.bet_history || []
  return bets.slice(-limit).reverse()
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}
