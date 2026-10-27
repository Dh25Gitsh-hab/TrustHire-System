/**
 * EvidencePanel — the backend's `evidence_analysis`: public web search results
 * (SerpApi) read by AI (Gemini).
 *
 * Important wording, matching the backend's scoring rule:
 *  * the AI's own "concern" score (0-100, higher = MORE concerning) is shown for
 *    context only — it does NOT change the trust score;
 *  * only the number of independent websites reporting the company as a scam
 *    enters the trust score (it appears in "What moved the score");
 *  * if search or AI failed, we say so — a failure is never shown as suspicious.
 */
import { useState } from 'react'
import { Globe2, Search } from 'lucide-react'
import EvidenceItem from './EvidenceItem.jsx'
import Alert from '../ui/Alert.jsx'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import Card from '../ui/Card.jsx'
import { EVIDENCE_CATEGORY, EVIDENCE_STATUS } from '../../utils/labels.js'

const FIRST_VISIBLE = 6
const CONCERN_TONE = { Low: 'positive', Medium: 'warning', High: 'danger' }

export default function EvidencePanel({ evidence }) {
  const [filter, setFilter] = useState('all')
  const [showAll, setShowAll] = useState(false)

  if (!evidence) {
    return (
      <Card title="Web evidence" icon={Search}>
        <p className="text-sm text-ink-muted">Web evidence was not returned for this analysis.</p>
      </Card>
    )
  }

  const status = EVIDENCE_STATUS[evidence.status] || EVIDENCE_STATUS.unavailable
  const items = evidence.evidence || []
  const categories = [...new Set(items.map((item) => item.category))]
  const filtered = filter === 'all' ? items : items.filter((item) => item.category === filter)
  const visible = showAll ? filtered : filtered.slice(0, FIRST_VISIBLE)

  return (
    <Card
      title="Web evidence"
      description="Public search results (including Reddit and LinkedIn pages indexed by Google), read by AI."
      icon={Globe2}
      aside={
        evidence.risk_level && (
          <Badge tone={CONCERN_TONE[evidence.risk_level] || 'neutral'}>AI concern: {evidence.risk_level}</Badge>
        )
      }
    >
      <div className="space-y-5">
        <Alert tone={status.tone} title={status.title}>
          {evidence.message}
          {evidence.model && <span className="block text-xs opacity-80">AI model: {evidence.model}</span>}
        </Alert>

        {evidence.risk_score !== null && evidence.risk_score !== undefined && (
          <ConcernMeter score={evidence.risk_score} level={evidence.risk_level} />
        )}

        {evidence.summary && <p className="text-[15px] leading-relaxed text-ink">{evidence.summary}</p>}

        {(evidence.risk_signals?.length > 0 || evidence.reassuring_signals?.length > 0) && (
          <div className="grid gap-4 md:grid-cols-2">
            <PointList title="Concerns found online" points={evidence.risk_signals} tone="text-red-700" />
            <PointList title="Reassuring findings" points={evidence.reassuring_signals} tone="text-teal-800" />
          </div>
        )}

        {items.length > 0 && (
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-sm font-semibold text-ink">Sources ({items.length})</h4>
              {categories.length > 1 && (
                <div className="flex flex-wrap gap-1" role="group" aria-label="Filter sources">
                  <FilterButton active={filter === 'all'} onClick={() => setFilter('all')}>
                    All
                  </FilterButton>
                  {categories.map((category) => (
                    <FilterButton key={category} active={filter === category} onClick={() => setFilter(category)}>
                      {EVIDENCE_CATEGORY[category]?.label || category}
                    </FilterButton>
                  ))}
                </div>
              )}
            </div>
            <ul className="mt-3 space-y-3">
              {visible.map((item) => (
                <EvidenceItem key={item.url} item={item} />
              ))}
            </ul>
            {filtered.length > FIRST_VISIBLE && (
              <Button variant="ghost" size="sm" className="mt-3" onClick={() => setShowAll((value) => !value)}>
                {showAll ? 'Show fewer sources' : `Show all ${filtered.length} sources`}
              </Button>
            )}
          </div>
        )}

        {evidence.limitations?.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-ink">What this could not check</h4>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-muted">
              {evidence.limitations.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {evidence.searches_run?.length > 0 && (
          <details className="group text-sm">
            <summary className="cursor-pointer rounded text-ink-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-500">
              Searches used ({evidence.searches_run.length})
            </summary>
            <ul className="mt-2 space-y-1 font-mono text-xs text-ink-soft">
              {evidence.searches_run.map((query) => (
                <li key={query} className="rounded bg-canvas px-2 py-1 wrap-break-word">
                  {query}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </Card>
  )
}

function ConcernMeter({ score, level }) {
  const tone = { Low: 'bg-teal-500', Medium: 'bg-amber-500', High: 'bg-red-500' }[level] || 'bg-ink-muted'
  return (
    <div className="rounded-lg border border-line px-4 py-3">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium text-ink">AI concern about the web evidence</span>
        <span className="tabular-nums text-ink-soft">
          {score}/100 · {level}
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-canvas" aria-hidden="true">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.max(2, score)}%` }} />
      </div>
      <p className="mt-2 text-xs text-ink-muted">
        Higher means more concerning. This is the AI's reading of search results — not a probability — and it does
        not change the trust score. Only the number of independent scam-report websites does.
      </p>
    </div>
  )
}

function PointList({ title, points = [], tone }) {
  if (!points?.length) return null
  return (
    <div>
      <h4 className={`text-sm font-semibold ${tone}`}>{title}</h4>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-soft">
        {points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </div>
  )
}

function FilterButton({ active, children, ...props }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-brand-500 ${
        active ? 'bg-ink text-white' : 'bg-canvas text-ink-soft hover:bg-line'
      }`}
      {...props}
    >
      {children}
    </button>
  )
}
