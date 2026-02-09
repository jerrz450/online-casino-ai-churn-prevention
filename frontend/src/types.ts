export interface BetEvent {
  player_id: number
  amount: number
  won: boolean
  payout: number
  emotional_state: string
}

export interface Intervention {
  type: string
  amount: number
  message: string
  risk_score: number
  reasoning?: string
}

export interface PlayerState {
  player_id: number
  last_bet: BetEvent | null
  bet_history: BetEvent[]
  intervention: Intervention | null
  churned: boolean
  flagged_by_monitor: boolean
  activity_log?: Array<{
    type: string
    timestamp: string
    message: string
    data?: any
  }>
}

export interface SimulationStats {
  tick: number
  active_players: number
  churned_players: number
  total_bets: number
  total_interventions: number
}

export interface WebSocketMessage {
  type: 'bet_event' | 'bet_batch' | 'monitor_flag' | 'intervention_designed' | 'simulation_stats' | 'player_churned'
  timestamp: string
  [key: string]: any
}
