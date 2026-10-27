/**
 * Header — logo on the left, one real navigation link, and a small live
 * indicator showing whether the backend server is reachable (from /api/health).
 */
import BrandMark from './BrandMark.jsx'

const STATUS = {
  checking: { dot: 'bg-line-strong', text: 'Checking server…' },
  online: { dot: 'bg-teal-500', text: 'Server online' },
  offline: { dot: 'bg-red-500', text: 'Server offline' },
}

export default function Header({ health }) {
  const status = STATUS[health.state]
  return (
    <header className="sticky top-0 z-30 border-b border-line/80 bg-canvas/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <a href="#top" className="rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-500" aria-label="TrustHire home">
          <BrandMark />
        </a>
        <nav className="flex items-center gap-1 sm:gap-3" aria-label="Main">
          <a
            href="#how-it-works"
            className="rounded-lg px-3 py-2 text-sm font-medium text-ink-soft hover:bg-white hover:text-ink focus-visible:outline-2 focus-visible:outline-brand-500"
          >
            How it works
          </a>
          <button
            type="button"
            onClick={health.refresh}
            title="Check the server again"
            aria-label={`${status.text}. Check the server again`}
            className="inline-flex items-center gap-2 rounded-lg border border-line bg-white px-3 py-2 text-xs font-medium text-ink-soft hover:border-line-strong focus-visible:outline-2 focus-visible:outline-brand-500 sm:py-1.5"
          >
            <span className={`h-2 w-2 rounded-full ${status.dot}`} aria-hidden="true" />
            {/* On phones only the coloured dot is shown, to save space. */}
            <span className="hidden sm:inline" aria-live="polite">
              {status.text}
            </span>
          </button>
        </nav>
      </div>
    </header>
  )
}
