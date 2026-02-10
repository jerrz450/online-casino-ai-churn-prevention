import { useEffect, useRef, useState } from 'react'
import { PlayerState, SimulationStats, WebSocketMessage } from '../types'

export function useWebSocket(url: string) {
  const [connected, setConnected] = useState(false)
  const [players, setPlayers] = useState<Record<number, PlayerState>>({})
  const [stats, setStats] = useState<SimulationStats>({
    tick: 0,
    active_players: 0,
    churned_players: 0,
    total_bets: 0,
    total_interventions: 0
  })

  const socketRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<number>()

  useEffect(() => {
    let active = true

    const handleMessage = (event: MessageEvent) => {
      const data: WebSocketMessage = JSON.parse(event.data)

      switch (data.type) {
        case 'initial_players': {
          setPlayers(prev => {
            const initialPlayers: Record<number, PlayerState> = {}
            data.player_ids.forEach((pid: number) => {
              initialPlayers[pid] = {
                player_id: pid,
                last_bet: null,
                bet_history: [],
                intervention: null,
                churned: false,
                flagged_by_monitor: false
              }
            })
            return initialPlayers
          })
          break
        }
        case 'bet_event': {
          setPlayers(prev => {
            const pid = data.player_id
            const newBet = {
              player_id: pid,
              amount: data.bet_amount,
              won: data.won,
              payout: data.payout,
              emotional_state: data.emotional_state
            }

            if (!prev[pid]) {
              return {
                ...prev,
                [pid]: {
                  player_id: pid,
                  last_bet: newBet,
                  bet_history: [newBet],
                  intervention: null,
                  churned: false,
                  flagged_by_monitor: false
                }
              }
            }

            return {
              ...prev,
              [pid]: {
                ...prev[pid],
                last_bet: newBet,
                bet_history: [...(prev[pid].bet_history || []), newBet]
              }
            }
          })
          break
        }
        case 'bet_batch': {
          setPlayers(prev => {
            const updated = { ...prev }
            data.events.forEach((bet: any) => {
              const newBet = {
                player_id: bet.player_id,
                amount: bet.bet_amount,
                won: bet.won,
                payout: bet.payout,
                emotional_state: bet.emotional_state
              }

              if (!updated[bet.player_id]) {
                updated[bet.player_id] = {
                  player_id: bet.player_id,
                  last_bet: newBet,
                  bet_history: [newBet],
                  intervention: null,
                  churned: false,
                  flagged_by_monitor: false
                }
              } else {
                updated[bet.player_id] = {
                  ...updated[bet.player_id],
                  last_bet: newBet,
                  bet_history: [...(updated[bet.player_id].bet_history || []), newBet]
                }
              }
            })
            return updated
          })
          break
        }
        case 'monitor_flag': {
          setPlayers(prev => {
            const updated = { ...prev }
            data.player_ids.forEach((pid: number) => {
              if (updated[pid]) {
                updated[pid] = {
                  ...updated[pid],
                  flagged_by_monitor: true
                }
              }
            })
            return updated
          })
          break
        }
        case 'intervention_designed': {
          setPlayers(prev => {
            const player = prev[data.player_id]
            if (!player) {
              return prev
            }

            return {
              ...prev,
              [data.player_id]: {
                ...player,
                intervention: {
                  type: data.intervention_type,
                  amount: data.amount,
                  message: data.message,
                  risk_score: data.risk_score,
                  reasoning: data.reasoning
                }
              }
            }
          })
          break
        }
        case 'simulation_stats': {
          setStats({
            tick: data.tick,
            active_players: data.active_players,
            churned_players: data.churned_players,
            total_bets: data.total_bets,
            total_interventions: data.total_interventions
          })
          break
        }
        case 'player_churned': {
          setPlayers(prev => {
            const player = prev[data.player_id]
            if (!player) return prev

            return {
              ...prev,
              [data.player_id]: {
                ...player,
                churned: true
              }
            }
          })
          break
        }
        default:
          break
      }
    }

    function scheduleReconnect() {
      if (!active) return
      if (retryRef.current) {
        window.clearTimeout(retryRef.current)
      }
      retryRef.current = window.setTimeout(connect, 2000)
    }

    function connect() {
      if (!active) return
      const websocket = new WebSocket(url)
      socketRef.current = websocket

      websocket.onopen = () => {
        setConnected(true)
      }

      websocket.onmessage = handleMessage

      websocket.onerror = () => {
        setConnected(false)
      }

      websocket.onclose = () => {
        setConnected(false)
        scheduleReconnect()
      }
    }

    connect()

    return () => {
      active = false
      if (retryRef.current) {
        window.clearTimeout(retryRef.current)
      }
      socketRef.current?.close()
    }
  }, [url])

  return { connected, players, stats }
}
