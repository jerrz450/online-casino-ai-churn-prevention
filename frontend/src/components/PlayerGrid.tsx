import { useMemo, useState } from 'react'
import { PlayerState } from '../types'
import { PlayerDetailModal } from './PlayerDetailModal'
import { PlayerCard } from './PlayerCard'
import { getRiskScore, resolvePlayerStatus } from '../utils/player'

type StatusFilter = 'all' | 'active' | 'flagged' | 'intervened' | 'churned'
type SortKey = 'risk' | 'id'

const statusOptions: Array<{ key: StatusFilter; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'flagged', label: 'Flagged' },
  { key: 'intervened', label: 'Interventions' },
  { key: 'churned', label: 'Churned' },
  { key: 'active', label: 'Active' }
]

interface PlayerGridProps {
  players: PlayerState[]
}

export function PlayerGrid({ players }: PlayerGridProps) {
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerState | null>(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sort, setSort] = useState<SortKey>('risk')

  const filteredPlayers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    let list = players
    if (normalizedQuery) {
      list = list.filter(player =>
        player.player_id.toString().includes(normalizedQuery)
      )
    }

    if (statusFilter !== 'all') {
      list = list.filter(player => resolvePlayerStatus(player).key === statusFilter)
    }

    const sorted = [...list]
    sorted.sort((a, b) => {
      if (sort === 'risk') {
        const diff = getRiskScore(b) - getRiskScore(a)
        if (diff !== 0) return diff
      }
      return a.player_id - b.player_id
    })

    return sorted
  }, [players, query, statusFilter, sort])

  return (
    <>
      <div className="toolbar">
        <div className="toolbar-left">
          <div className="search-input">
            <input
              type="search"
              placeholder="Search player id"
              value={query}
              onChange={event => setQuery(event.target.value)}
            />
          </div>
          <div className="filter-group">
            {statusOptions.map(option => (
              <button
                key={option.key}
                type="button"
                className="filter-chip"
                data-active={statusFilter === option.key}
                onClick={() => setStatusFilter(option.key)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
        <div className="toolbar-right">
          <label htmlFor="sort-select">Sort by</label>
          <select
            id="sort-select"
            className="sort-select"
            value={sort}
            onChange={event => setSort(event.target.value as SortKey)}
          >
            <option value="risk">Risk</option>
            <option value="id">Player ID</option>
          </select>
        </div>
      </div>

      {filteredPlayers.length === 0 ? (
        <div className="empty-state">
          No players match the selected filters.
        </div>
      ) : (
        <div className="player-grid">
          {filteredPlayers.map(player => (
            <PlayerCard
              key={player.player_id}
              player={player}
              onSelect={() => setSelectedPlayer(player)}
            />
          ))}
        </div>
      )}

      {selectedPlayer && (
        <PlayerDetailModal
          player={selectedPlayer}
          onClose={() => setSelectedPlayer(null)}
        />
      )}
    </>
  )
}
