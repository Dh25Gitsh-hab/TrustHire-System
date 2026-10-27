/**
 * Hero — the headline above the analysis portal, plus four small indicators
 * naming the evidence TrustHire really examines (the backend's checks).
 */
import { AlertTriangle, Globe, Landmark, Search } from 'lucide-react'

const INDICATORS = [
  { icon: Globe, text: 'Website age' },
  { icon: Landmark, text: 'Company registry' },
  { icon: Search, text: 'Public web reports' },
  { icon: AlertTriangle, text: 'Hiring red flags' },
]

export default function Hero() {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="text-sm font-medium tracking-wide text-brand-600">Know the opportunity before you trust it.</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-balance text-ink sm:text-[2.6rem] sm:leading-tight">
        Is this job opportunity trustworthy?
      </h1>
      <p className="mx-auto mt-4 max-w-xl text-base text-pretty text-ink-soft sm:text-lg">
        Analyze job postings, verify company signals, and identify potential recruitment scams.
      </p>
      <ul className="mt-6 flex flex-wrap justify-center gap-x-5 gap-y-2 text-sm text-ink-muted" aria-label="What TrustHire checks">
        {INDICATORS.map(({ icon: Icon, text }) => (
          <li key={text} className="inline-flex items-center gap-1.5">
            <Icon className="h-4 w-4 text-brand-500" aria-hidden="true" />
            {text}
          </li>
        ))}
      </ul>
    </div>
  )
}
