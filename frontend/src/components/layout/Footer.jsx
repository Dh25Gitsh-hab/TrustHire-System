/**
 * Footer — privacy note and the reminder that results are indicative, not final.
 */
import { Lock } from 'lucide-react'
import BrandMark from './BrandMark.jsx'

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-white/60">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-10 text-sm text-ink-muted sm:px-6 md:grid-cols-[auto_1fr] md:gap-12">
        <div className="space-y-2">
          <BrandMark />
          <p className="max-w-xs">Know the opportunity before you trust it.</p>
        </div>
        <div className="space-y-3 md:justify-self-end md:text-right">
          <p className="inline-flex items-start gap-2 md:justify-end">
            <Lock className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>
              We save the score and the signals behind it — never the posting text or the recruiter's e-mail and
              phone number.
            </span>
          </p>
          <p>
            Results are indicative, not definitive. A high score is not a guarantee, and a low score is not a legal
            finding about any company. Never pay money to get a job.
          </p>
          <p className="text-xs">B.Tech CSE final-year project · JSS Academy of Technical Education, Noida</p>
        </div>
      </div>
    </footer>
  )
}
