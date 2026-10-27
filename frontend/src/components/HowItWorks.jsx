/**
 * HowItWorks — a plain explanation of what TrustHire checks and how the
 * score is made. Every sentence describes what the backend really does.
 */
import { ClipboardPaste, Gauge, Lock, ScanSearch } from 'lucide-react'
import { CHECK_ICONS } from '../utils/labels.js'

const STEPS = [
  { icon: ClipboardPaste, title: 'Paste the posting', text: 'A job description, a recruiter message, or a link to the job page.' },
  { icon: ScanSearch, title: 'Five checks run at once', text: 'TrustHire looks at the company behind the posting, not just the wording.' },
  { icon: Gauge, title: 'Explainable score', text: 'A trust score from 1 to 99, with every reason and how much it counted.' },
]

const CHECKS = [
  { key: 'domain_age', title: 'Website age (WHOIS)', text: 'When the company website was registered — and whether claims like “20 years in business” fit.' },
  { key: 'reputation', title: 'Online reputation', text: 'Google results (via SerpApi), including public Reddit and LinkedIn pages. AI separates scam reports from impersonation warnings.' },
  { key: 'registry', title: 'Company registration (MCA)', text: 'Looks the company up in the Ministry of Corporate Affairs data published on data.gov.in.' },
  { key: 'red_flags', title: 'Hiring red flags', text: 'Fees, WhatsApp-only contact, “no interview”, requests for Aadhaar / PAN / bank details, free e-mail, unrealistic pay.' },
  { key: 'reviews', title: 'Employee reviews', text: 'Quick links to AmbitionBox and Glassdoor (they offer no free API), so you can read reviews yourself.' },
]

export default function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-heading" className="scroll-mt-20">
      <div className="mx-auto max-w-2xl text-center">
        <h2 id="how-heading" className="text-2xl font-semibold tracking-tight text-ink">
          How TrustHire works
        </h2>
        <p className="mt-3 text-ink-soft">
          Scam postings often copy real wording. So TrustHire checks the evidence around the company as well.
        </p>
      </div>

      <ol className="mt-10 grid gap-4 md:grid-cols-3">
        {STEPS.map(({ icon: Icon, title, text }, index) => (
          <li key={title} className="rounded-xl border border-line bg-white p-5 shadow-card">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Icon className="h-5 w-5" aria-hidden="true" />
            </span>
            <p className="mt-4 text-xs font-medium text-ink-muted">Step {index + 1}</p>
            <h3 className="mt-1 font-semibold text-ink">{title}</h3>
            <p className="mt-1 text-sm text-ink-soft">{text}</p>
          </li>
        ))}
      </ol>

      <div className="mt-8 rounded-xl border border-line bg-white p-5 shadow-card sm:p-6">
        <h3 className="font-semibold text-ink">The five checks</h3>
        <ul className="mt-4 grid gap-x-8 gap-y-5 md:grid-cols-2">
          {CHECKS.map(({ key, title, text }) => {
            const Icon = CHECK_ICONS[key]
            return (
              <li key={key} className="flex gap-3">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-brand-500" aria-hidden="true" />
                <div>
                  <p className="font-medium text-ink">{title}</p>
                  <p className="mt-0.5 text-sm text-ink-soft">{text}</p>
                </div>
              </li>
            )
          })}
        </ul>
        <div className="mt-6 grid gap-4 border-t border-line pt-5 text-sm text-ink-soft md:grid-cols-2">
          <p>
            <span className="font-medium text-ink">How the score works. </span>
            Each signal has a weight, and the score combines them with a logistic formula — so every reason shows
            exactly how much it moved the score. The weights are starting values that will be learned from labelled
            data.
          </p>
          <p className="flex gap-2">
            <Lock className="mt-0.5 h-4 w-4 shrink-0 text-ink-muted" aria-hidden="true" />
            <span>
              <span className="font-medium text-ink">Privacy. </span>
              The AI only sees the company name, website and public search results — never the posting text, e-mails
              or phone numbers. We store scores and signals, not the posting.
            </span>
          </p>
        </div>
      </div>
    </section>
  )
}
