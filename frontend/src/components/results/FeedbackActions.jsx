/**
 * FeedbackActions — "Report as suspicious" / "Mark as genuine", sent to the
 * backend's POST /api/reports with this analysis' id.
 *
 * Feedback is stored as a user REPORT, not as a confirmed fact: it is reviewed
 * before it is ever used to train the model, and it does not change this result.
 */
import { useState } from 'react'
import { Flag, MessageSquarePlus, ThumbsUp } from 'lucide-react'
import Alert from '../ui/Alert.jsx'
import Button from '../ui/Button.jsx'
import Card from '../ui/Card.jsx'
import Spinner from '../ui/Spinner.jsx'
import { sendReport } from '../../services/api.js'

const MAX_COMMENT = 1000 // same limit as the backend

export default function FeedbackActions({ analysisId }) {
  const [state, setState] = useState('idle') // idle | sending | sent | failed
  const [choice, setChoice] = useState(null)
  const [error, setError] = useState('')
  const [comment, setComment] = useState('')
  const [showComment, setShowComment] = useState(false)

  if (!analysisId) {
    return (
      <Card title="Was this analysis right?" icon={MessageSquarePlus}>
        <Alert tone="neutral">
          Feedback is unavailable for this result because it was not saved (the database is not connected).
        </Alert>
      </Card>
    )
  }

  async function submit(verdict) {
    if (state === 'sending' || state === 'sent') return // no duplicate reports
    setChoice(verdict)
    setState('sending')
    setError('')
    try {
      await sendReport({ analysisId, verdict, comment })
      setState('sent')
    } catch (problem) {
      setError(problem.message)
      setState('failed')
    }
  }

  return (
    <Card
      title="Was this analysis right?"
      description="Your feedback is reviewed before it is used to improve TrustHire. It does not change this result."
      icon={MessageSquarePlus}
    >
      {state === 'sent' ? (
        <Alert tone="positive" title="Thank you — your feedback was saved.">
          You marked this posting as {choice === 'scam' ? 'suspicious' : 'genuine'}.
        </Alert>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              icon={state === 'sending' && choice === 'scam' ? Spinner : Flag}
              onClick={() => submit('scam')}
              disabled={state === 'sending'}
            >
              Report as suspicious
            </Button>
            <Button
              icon={state === 'sending' && choice === 'genuine' ? Spinner : ThumbsUp}
              onClick={() => submit('genuine')}
              disabled={state === 'sending'}
            >
              Mark as genuine
            </Button>
            {!showComment && (
              <Button variant="ghost" onClick={() => setShowComment(true)} disabled={state === 'sending'}>
                Add a note
              </Button>
            )}
          </div>

          {showComment && (
            <div>
              <label htmlFor="feedback-comment" className="text-xs font-medium text-ink-soft">
                Note (optional) — please do not include personal details
              </label>
              <textarea
                id="feedback-comment"
                value={comment}
                onChange={(event) => setComment(event.target.value.slice(0, MAX_COMMENT))}
                rows={3}
                disabled={state === 'sending'}
                className="mt-1 block w-full resize-y rounded-lg border border-line px-3 py-2 text-base text-ink focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100 sm:text-sm"
                placeholder="e.g. They asked me to pay a training fee after the interview."
              />
              <p className="mt-1 text-right text-xs tabular-nums text-ink-muted">
                {comment.length} / {MAX_COMMENT}
              </p>
            </div>
          )}

          {state === 'failed' && (
            <Alert tone="danger" title="Your feedback could not be saved.">
              {error} You can try again.
            </Alert>
          )}
        </div>
      )}
    </Card>
  )
}
