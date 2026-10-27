/**
 * TrustScore — the headline of a result: the backend's trust_score in a
 * circular gauge, its trust_level, the verdict sentence and what was detected.
 *
 * trust_score is shown exactly as the backend sends it: 1-99, where HIGHER
 * means MORE trustworthy. The colours follow the backend's own trust_level
 * (high / medium / low) — the frontend adds no thresholds of its own.
 */
import Badge from '../ui/Badge.jsx'
import { TRUST_LEVELS } from '../../utils/labels.js'

const SIZE = 136
const STROKE = 10
const RADIUS = (SIZE - STROKE) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export default function TrustScore({ result }) {
  const level = TRUST_LEVELS[result.trust_level] || TRUST_LEVELS.medium
  const score = Math.max(0, Math.min(100, Number(result.trust_score) || 0))
  const { extracted = {} } = result

  const facts = [
    ['Company', extracted.company_name],
    ['Website', extracted.website_domain],
    ['Salary mentioned', extracted.salary_text],
  ].filter(([, value]) => value)

  return (
    <section className="rounded-xl border border-line bg-white shadow-card" aria-label="Trust score">
      <div className="grid gap-6 px-5 py-6 sm:grid-cols-[auto_1fr] sm:items-center sm:gap-8 sm:px-8 sm:py-7">
        <div className="relative mx-auto h-[136px] w-[136px]" role="img" aria-label={`Trust score ${score} out of 100, ${level.label.toLowerCase()}`}>
          <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="-rotate-90" aria-hidden="true">
            <circle cx={SIZE / 2} cy={SIZE / 2} r={RADIUS} fill="none" stroke="var(--color-line)" strokeWidth={STROKE} />
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              fill="none"
              stroke={level.ring}
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={CIRCUMFERENCE * (1 - score / 100)}
              className="transition-[stroke-dashoffset] duration-700 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center" aria-hidden="true">
            <span className="text-4xl font-semibold tracking-tight text-ink tabular-nums">{score}</span>
            <span className="text-xs text-ink-muted">out of 100</span>
          </div>
        </div>

        <div className="min-w-0 text-center sm:text-left">
          <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
            <Badge tone={level.tone} className="text-sm">
              {level.label}
            </Badge>
            <span className="text-sm text-ink-muted">
              {result.checks_completed} of {result.checks_total} checks completed
            </span>
          </div>
          <p className="mt-3 text-lg font-medium text-pretty text-ink">{result.verdict}</p>
          <p className="mt-2 text-sm text-ink-muted">
            A screening score from 1 to 99 — higher means more trustworthy. It is not a guarantee and not a
            probability.
          </p>
          {facts.length > 0 && (
            <dl className="mt-4 flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm sm:justify-start">
              {facts.map(([label, value]) => (
                <div key={label} className="min-w-0">
                  <dt className="text-xs text-ink-muted">{label}</dt>
                  <dd className="wrap-break-word font-medium text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>
    </section>
  )
}
