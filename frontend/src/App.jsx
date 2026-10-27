/**
 * App — builds the page and runs one analysis at a time.
 *
 *   Header
 *   Hero + JobAnalysisPortal        <- the main action
 *   LoadingState | AnalysisResults  <- after "Analyze Job"
 *   HowItWorks
 *   Footer
 *
 * phase: 'idle' -> 'loading' -> 'success' | 'error'
 */
import { useRef, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import Hero from './components/Hero.jsx'
import HowItWorks from './components/HowItWorks.jsx'
import Footer from './components/layout/Footer.jsx'
import Header from './components/layout/Header.jsx'
import JobAnalysisPortal from './components/portal/JobAnalysisPortal.jsx'
import AnalysisResults from './components/results/AnalysisResults.jsx'
import LoadingState from './components/results/LoadingState.jsx'
import Alert from './components/ui/Alert.jsx'
import Button from './components/ui/Button.jsx'
import useHealth from './hooks/useHealth.js'
import { API_BASE_URL, ApiError, analyzeJob } from './services/api.js'

export default function App() {
  const health = useHealth()
  const [phase, setPhase] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [lastPayload, setLastPayload] = useState(null)
  const [portalKey, setPortalKey] = useState(0) // a new key = a fresh, empty portal
  const busyRef = useRef(false) // blocks a second request while one is running
  const abortRef = useRef(null)
  const resultsHeadingRef = useRef(null)
  const portalRef = useRef(null)

  async function analyze(payload) {
    if (busyRef.current) return
    busyRef.current = true
    const controller = new AbortController()
    abortRef.current = controller
    setLastPayload(payload)
    setResult(null)
    setError(null)
    setPhase('loading')

    try {
      const data = await analyzeJob(payload, { signal: controller.signal })
      if (typeof data?.trust_score !== 'number') {
        throw new ApiError('The server sent an answer TrustHire could not understand. Please try again.')
      }
      setResult(data)
      setPhase('success')
      showResults()
    } catch (problem) {
      if (problem.kind === 'cancelled') {
        setPhase('idle')
      } else {
        setError(problem instanceof ApiError ? problem : new ApiError('Something went wrong. Please try again.'))
        setPhase('error')
        if (problem.kind === 'network') health.refresh()
      }
    } finally {
      busyRef.current = false
      abortRef.current = null
    }
  }

  // Scroll the result into view and move keyboard focus to its heading.
  function showResults() {
    requestAnimationFrame(() => {
      const heading = resultsHeadingRef.current
      heading?.focus({ preventScroll: true })
      heading?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
    })
  }

  function analyzeAnother() {
    setResult(null)
    setError(null)
    setPhase('idle')
    setPortalKey((key) => key + 1)
    portalRef.current?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'center' })
  }

  return (
    <div id="top" className="flex min-h-dvh flex-col">
      <a
        href="#job-input"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-ink focus:shadow-portal"
      >
        Skip to the analysis box
      </a>
      <Header health={health} />

      <main className="flex-1">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <section aria-label="Analyze a job" className="pt-12 pb-10 sm:pt-20">
            <Hero />

            {health.state === 'offline' && (
              <Alert
                tone="warning"
                title="The TrustHire server is not reachable"
                className="mx-auto mt-8 max-w-3xl"
                action={
                  <Button size="sm" icon={RefreshCw} onClick={health.refresh}>
                    Check again
                  </Button>
                }
              >
                The app could not connect to {API_BASE_URL}. Start the backend, then check again.
              </Alert>
            )}

            <div ref={portalRef} className="mt-8 sm:mt-10">
              <JobAnalysisPortal
                key={portalKey}
                onAnalyze={analyze}
                loading={phase === 'loading'}
                autoFocus={portalKey > 0}
                showSuggestions={phase !== 'success'}
              />
            </div>

            {phase === 'error' && error && (
              <Alert
                tone="danger"
                title="The analysis could not be completed"
                className="mx-auto mt-4 max-w-3xl"
                action={
                  error.retryable && (
                    <Button size="sm" icon={RefreshCw} onClick={() => analyze(lastPayload)}>
                      Try again
                    </Button>
                  )
                }
              >
                {error.message}
                {!error.retryable && ' Your input is still in the box above — you can edit it and analyze again.'}
              </Alert>
            )}
          </section>

          {phase === 'loading' && (
            <div className="mx-auto max-w-4xl">
              <LoadingState onCancel={() => abortRef.current?.abort()} />
            </div>
          )}

          {phase === 'success' && result && (
            <div className="mx-auto max-w-4xl">
              <AnalysisResults result={result} headingRef={resultsHeadingRef} onAnalyzeAnother={analyzeAnother} />
            </div>
          )}

          <div className="mt-20 sm:mt-28">
            <HowItWorks />
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}
