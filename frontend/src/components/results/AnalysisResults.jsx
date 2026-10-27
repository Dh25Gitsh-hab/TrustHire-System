/**
 * AnalysisResults — everything the backend returned for one posting, in order:
 *   1. trust score + level   2. what moved the score   3. each verification check
 *   4. web evidence          5. feedback                6. the backend's disclaimer
 */
import { RotateCcw } from 'lucide-react'
import CheckGrid from './CheckGrid.jsx'
import EvidencePanel from './EvidencePanel.jsx'
import FeedbackActions from './FeedbackActions.jsx'
import ReasonList from './ReasonList.jsx'
import TrustScore from './TrustScore.jsx'
import Alert from '../ui/Alert.jsx'
import Button from '../ui/Button.jsx'

export default function AnalysisResults({ result, headingRef, onAnalyzeAnother }) {
  const partial = result.checks_completed < result.checks_total

  return (
    <section aria-labelledby="results-heading" className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="results-heading" ref={headingRef} tabIndex={-1} className="scroll-mt-24 text-xl font-semibold text-ink focus:outline-none">
            Analysis result
          </h2>
          <p className="mt-1 text-sm text-ink-muted">Based on the evidence that was available for this posting.</p>
        </div>
        <Button icon={RotateCcw} onClick={onAnalyzeAnother}>
          Analyze another job
        </Button>
      </div>

      <TrustScore result={result} />

      {partial && (
        <Alert tone="neutral" title="Partial analysis">
          {result.checks_completed} of {result.checks_total} checks could run. The score only uses the checks that
          completed — see “Verification checks” below for the others.
        </Alert>
      )}

      <ReasonList reasons={result.reasons} />
      <CheckGrid checks={result.checks} />
      <EvidencePanel evidence={result.evidence_analysis} />
      <FeedbackActions analysisId={result.analysis_id} />

      {result.disclaimer && <p className="text-center text-xs text-ink-muted">{result.disclaimer}</p>}

      <div className="flex justify-center">
        <Button variant="primary" icon={RotateCcw} onClick={onAnalyzeAnother}>
          Analyze another job
        </Button>
      </div>
    </section>
  )
}
