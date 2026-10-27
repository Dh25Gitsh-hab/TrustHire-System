/**
 * EvidenceItem — one web search result about the company.
 *
 * Title, link and snippet come from the search engine (never from the AI).
 * The AI adds a short note and two labels: what kind of source it is, and
 * whether the claim is verified or only an UNVERIFIED ALLEGATION.
 * The coloured left edge shows the signal: red = suspicious, teal = reassuring.
 */
import Badge from '../ui/Badge.jsx'
import ExternalLink from '../ui/ExternalLink.jsx'
import { EVIDENCE_CATEGORY, EVIDENCE_VERIFICATION, SIGNAL_EDGE } from '../../utils/labels.js'

export default function EvidenceItem({ item }) {
  const category = EVIDENCE_CATEGORY[item.category] || EVIDENCE_CATEGORY.neutral_info
  const verification = EVIDENCE_VERIFICATION[item.verification] || EVIDENCE_VERIFICATION.unknown
  const analysed = item.category !== 'not_analysed'

  return (
    <li className={`rounded-lg border border-l-4 border-line bg-white px-4 py-3 ${SIGNAL_EDGE[item.signal] || SIGNAL_EDGE.neutral}`}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={category.tone}>{category.label}</Badge>
        {analysed && <Badge tone={verification.tone}>{verification.label}</Badge>}
        <span className="text-xs text-ink-muted">
          {item.source_domain}
          {item.date ? ` · ${item.date}` : ''}
        </span>
      </div>
      <p className="mt-2 text-sm font-medium">
        <ExternalLink href={item.url}>{item.title}</ExternalLink>
      </p>
      {item.snippet && <p className="mt-1 line-clamp-3 text-sm text-ink-muted">“{item.snippet}”</p>}
      {item.relevance && (
        <p className="mt-2 text-sm text-ink-soft">
          <span className="font-medium text-ink">AI note: </span>
          {item.relevance}
        </p>
      )}
    </li>
  )
}
