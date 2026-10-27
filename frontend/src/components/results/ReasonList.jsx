/**
 * ReasonList — "what moved the score". The backend sends `reasons`, strongest
 * first; each has a message and an impact (+ raises trust, - lowers trust).
 * We split them into warning signs and reassuring signs, and draw a small bar
 * so the strongest ones stand out.
 */
import { ShieldAlert, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import Card from '../ui/Card.jsx'
import { featureFamily } from '../../utils/labels.js'

export default function ReasonList({ reasons = [] }) {
  const strongest = Math.max(...reasons.map((reason) => Math.abs(reason.impact)), 1)
  const columns = [
    { title: 'Warning signs', icon: ShieldAlert, negative: true, items: reasons.filter((r) => r.effect === 'lowers_trust') },
    { title: 'Reassuring signs', icon: ShieldCheck, negative: false, items: reasons.filter((r) => r.effect === 'raises_trust') },
  ]
  // Show only the columns that have something in them; mention the empty one in one line.
  const filled = columns.filter((column) => column.items.length > 0)
  const empty = columns.filter((column) => column.items.length === 0)

  return (
    <Card
      title="What moved the score"
      description="Strongest first. Each bar shows how much a signal changed the score."
      icon={SlidersHorizontal}
    >
      {reasons.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No signal was strong enough to move the score. Add the company name or website, or use the links in the
          checks below to verify it yourself.
        </p>
      ) : (
        <>
          <div className={`grid gap-6 ${filled.length === 2 ? 'md:grid-cols-2' : ''}`}>
            {filled.map((column) => (
              <ReasonColumn key={column.title} column={column} strongest={strongest} wide={filled.length === 1} />
            ))}
          </div>
          {empty.map((column) => (
            <p key={column.title} className="mt-4 text-sm text-ink-muted">
              No {column.title.toLowerCase()} were found.
            </p>
          ))}
        </>
      )}
    </Card>
  )
}

function ReasonColumn({ column, strongest, wide }) {
  const { title, icon: Icon, items: reasons, negative } = column
  return (
    <div>
      <h4 className={`flex items-center gap-2 text-sm font-semibold ${negative ? 'text-red-700' : 'text-teal-800'}`}>
        <Icon className="h-4 w-4" aria-hidden="true" />
        {title}
        <span className="font-normal text-ink-muted">({reasons.length})</span>
      </h4>
      {/* When this is the only column, its cards sit two per row on wide screens. */}
      <ul className={`mt-3 grid gap-3 ${wide ? 'md:grid-cols-2' : ''}`}>
        {reasons.map((reason, index) => (
          <li key={`${reason.feature}-${index}`} className="rounded-lg border border-line px-3.5 py-3">
            <p className="text-sm text-ink">{reason.message}</p>
            <div className="mt-2 flex items-center gap-3">
              <span className="rounded bg-canvas px-1.5 py-0.5 text-[11px] font-medium text-ink-muted">
                {featureFamily(reason.feature)}
              </span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-canvas" aria-hidden="true">
                <div
                  className={`h-full rounded-full ${negative ? 'bg-red-400' : 'bg-teal-500'}`}
                  style={{ width: `${Math.max(6, (Math.abs(reason.impact) / strongest) * 100)}%` }}
                />
              </div>
              <span className="w-12 text-right text-xs tabular-nums text-ink-muted" title="Effect on the score (model units)">
                {formatImpact(reason.impact)}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

// A real minus sign reads better than a hyphen: "−2.00"
function formatImpact(impact) {
  const value = Math.abs(impact).toFixed(2)
  return impact < 0 ? `−${value}` : `+${value}`
}
