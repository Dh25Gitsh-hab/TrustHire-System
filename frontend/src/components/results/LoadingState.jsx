/**
 * LoadingState — shown while the backend analyses a posting.
 * It does not fake progress: it names the checks that run (all at the same
 * time on the server), shows the real elapsed time, and allows cancelling.
 */
import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import Button from '../ui/Button.jsx'

const CHECKS = [
  'Website registration (WHOIS)',
  'Company registry (MCA)',
  'Public web reports (search + AI)',
  'Hiring red flags in the text',
]

export default function LoadingState({ onCancel }) {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <section
      aria-live="polite"
      aria-busy="true"
      className="rounded-xl border border-line bg-white px-5 py-6 shadow-card sm:px-6"
    >
      <div className="flex items-start gap-4">
        <Loader2 className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-brand-600" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-ink">Checking available evidence…</p>
          <p className="mt-1 text-sm text-ink-muted">
            These checks run at the same time and usually take 10–30 seconds.
          </p>
          <ul className="mt-4 grid gap-2 text-sm text-ink-soft sm:grid-cols-2">
            {CHECKS.map((check) => (
              <li key={check} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500" aria-hidden="true" />
                {check}
              </li>
            ))}
          </ul>
        </div>
        <span className="text-sm tabular-nums text-ink-muted" aria-label={`${seconds} seconds elapsed`}>
          {seconds}s
        </span>
      </div>
      <div className="mt-5 flex justify-end">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </section>
  )
}
