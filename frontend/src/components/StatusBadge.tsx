import { StatusTone } from '../utils/player'

interface StatusBadgeProps {
  label: string
  tone: StatusTone
  subtle?: boolean
}

export function StatusBadge({ label, tone, subtle }: StatusBadgeProps) {
  return (
    <span className={`status-badge${subtle ? ' is-subtle' : ''}`} data-tone={tone}>
      <span className="status-dot" />
      {label}
    </span>
  )
}
