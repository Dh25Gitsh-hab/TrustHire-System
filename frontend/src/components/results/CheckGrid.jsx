/**
 * CheckGrid — one small card per verification module the backend ran
 * (domain age, online reputation, reviews, company registry, red flags):
 * its status, one-line summary, key facts, and "verify it yourself" links.
 * Checks that could not run are shown honestly and do not affect the score.
 */
import { ListChecks } from 'lucide-react'
import Badge from '../ui/Badge.jsx'
import Card from '../ui/Card.jsx'
import ExternalLink from '../ui/ExternalLink.jsx'
import { CHECK_ICONS, CHECK_STATUS, FallbackCheckIcon, detailLabel, formatDetail } from '../../utils/labels.js'

export default function CheckGrid({ checks = [] }) {
  return (
    <Card
      title="Verification checks"
      description="The result of each module. Checks that could not run do not change the score."
      icon={ListChecks}
    >
      {/* items-start: each card keeps its own height instead of stretching to its neighbour's */}
      <ul className="grid gap-4 md:grid-cols-2 md:items-start">
        {checks.map((check) => (
          <CheckCard key={check.key} check={check} />
        ))}
      </ul>
    </Card>
  )
}

function CheckCard({ check }) {
  const Icon = CHECK_ICONS[check.key] || FallbackCheckIcon
  const status = CHECK_STATUS[check.status] || CHECK_STATUS.error
  const facts = Object.entries(check.details || {}).filter(([, value]) => isSimpleFact(value))

  return (
    <li className="flex flex-col rounded-lg border border-line p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="flex min-w-0 items-start gap-2 font-medium text-ink">
          <Icon className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
          <span>{check.title}</span>
        </p>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>
      <p className="mt-2 text-sm text-ink-soft">{check.summary}</p>

      {facts.length > 0 && (
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-md bg-canvas px-3 py-2 text-xs">
          {facts.map(([key, value]) => (
            <div key={key} className="contents">
              <dt className="text-ink-muted">{detailLabel(key)}</dt>
              <dd className="min-w-0 wrap-break-word font-medium text-ink-soft">{formatDetail(key, value)}</dd>
            </div>
          ))}
        </dl>
      )}

      {check.manual_links?.length > 0 && (
        <div className="mt-3 border-t border-line pt-3">
          <p className="text-xs font-medium text-ink-muted">Verify it yourself</p>
          <ul className="mt-1.5 space-y-1 text-sm">
            {check.manual_links.map((link) => (
              <li key={link.url}>
                <ExternalLink href={link.url}>{link.label}</ExternalLink>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  )
}

/** Only simple facts are listed: text, numbers, or a list of them. Empty values are skipped. */
function isSimpleFact(value) {
  if (value === null || value === undefined || value === '') return false
  if (Array.isArray(value)) return value.length > 0 && value.every((item) => typeof item !== 'object')
  return typeof value !== 'object'
}
