/**
 * JobAnalysisPortal — the large input card in the middle of the page.
 *
 * It accepts written text, a job link (typed into the text box or into the
 * optional "Job link" field), and a .txt attachment. On "Analyze Job" it
 * checks the input, builds the exact body for POST /api/analyze (see
 * utils/input.js) and hands it to the parent through onAnalyze().
 *
 * The typed input lives here, so it is kept when an analysis fails. The
 * parent gives this component a new `key` for "Analyze another job",
 * which starts it fresh and empty.
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { ChevronDown, FileText, Link2, MessageSquareText, ShieldCheck } from 'lucide-react'
import AttachmentButton, { AttachmentChip } from './AttachmentButton.jsx'
import DetailsFields from './DetailsFields.jsx'
import PortalActions from './PortalActions.jsx'
import Alert from '../ui/Alert.jsx'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import Spinner from '../ui/Spinner.jsx'
import { SAMPLE_POSTING } from '../../data/samples.js'
import { LIMITS, buildPayload, findUrls, hostOf, isHttpUrl, normalizeUrl, siteHint, validatePayload } from '../../utils/input.js'

const MAX_TEXTAREA_HEIGHT = 420 // px; after this the text box scrolls

export default function JobAnalysisPortal({ onAnalyze, loading, autoFocus = false, showSuggestions = true }) {
  const [text, setText] = useState('')
  const [details, setDetails] = useState({ link: '', companyName: '', companyWebsite: '' })
  const [showDetails, setShowDetails] = useState(false)
  const [attachment, setAttachment] = useState(null)
  const [error, setError] = useState('')
  const [focusLinkSoon, setFocusLinkSoon] = useState(false)
  const textareaRef = useRef(null)
  const linkRef = useRef(null)

  const payload = buildPayload({ text, ...details, attachment })
  const hasInput = Boolean(payload.job_text || payload.job_url)
  const textLength = payload.job_text?.length || 0
  const isSample = text === SAMPLE_POSTING.text
  const linkNotes = describeLinks(text, details.link, payload.job_url)

  // Grow the text box with its content (up to a limit).
  useLayoutEffect(() => {
    const box = textareaRef.current
    if (!box) return
    box.style.height = 'auto'
    box.style.height = `${Math.min(box.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`
  }, [text])

  useEffect(() => {
    if (autoFocus) textareaRef.current?.focus()
  }, [autoFocus])

  // "Add a job link" opens the details first; focus the field once it exists.
  useEffect(() => {
    if (focusLinkSoon && showDetails) {
      linkRef.current?.focus()
      setFocusLinkSoon(false)
    }
  }, [focusLinkSoon, showDetails])

  function submit(event) {
    event?.preventDefault()
    if (loading) return // no duplicate submissions
    const problem = validatePayload(payload, { link: details.link })
    if (problem) {
      setError(problem)
      return
    }
    setError('')
    onAnalyze(payload)
  }

  function handleKeyDown(event) {
    // Ctrl + Enter (Cmd + Enter on a Mac) analyses without leaving the keyboard.
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) submit(event)
  }

  function clearAll() {
    setText('')
    setDetails({ link: '', companyName: '', companyWebsite: '' })
    setAttachment(null)
    setError('')
    textareaRef.current?.focus()
  }

  function loadSample() {
    setText(SAMPLE_POSTING.text)
    setError('')
    textareaRef.current?.focus()
  }

  function addLink() {
    setShowDetails(true)
    setFocusLinkSoon(true)
  }

  return (
    <div className="mx-auto w-full max-w-3xl">
      <form
        onSubmit={submit}
        noValidate // our own inline messages replace the browser's validation pop-ups
        aria-label="Analyze a job posting"
        aria-busy={loading}
        className="rounded-2xl border border-line bg-white shadow-portal transition-shadow duration-200 focus-within:border-brand-200 focus-within:ring-4 focus-within:ring-brand-50"
      >
        {isSample && (
          <div className="flex flex-wrap items-center gap-2 px-5 pt-4 sm:px-6">
            <Badge tone="brand">Sample</Badge>
            <span className="text-xs text-ink-muted">
              {SAMPLE_POSTING.label} — the analysis itself will be real.
            </span>
          </div>
        )}

        <label htmlFor="job-input" className="sr-only">
          Job description, recruiter message or job link
        </label>
        <textarea
          id="job-input"
          ref={textareaRef}
          value={text}
          onChange={(event) => {
            setText(event.target.value)
            if (error) setError('')
          }}
          onKeyDown={handleKeyDown}
          rows={5}
          disabled={loading}
          placeholder="Paste the job description, recruiter message, or offer details here…"
          className="block min-h-36 w-full resize-none bg-transparent px-5 pt-5 pb-3 text-base leading-relaxed text-ink placeholder:text-ink-muted/70 focus:outline-none disabled:text-ink-soft sm:min-h-40 sm:px-6 sm:text-[15px]"
        />

        <div className="space-y-3 px-5 pb-4 sm:px-6">
          {linkNotes.map((note) => (
            <LinkNote key={note.url} note={note} />
          ))}

          {attachment && (
            <AttachmentChip attachment={attachment} onRemove={() => setAttachment(null)} disabled={loading} />
          )}

          <button
            type="button"
            onClick={() => setShowDetails((value) => !value)}
            aria-expanded={showDetails}
            aria-controls="portal-details"
            className="inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-brand-600 hover:text-brand-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
          >
            <ChevronDown
              className={`h-4 w-4 transition-transform ${showDetails ? 'rotate-180' : ''}`}
              aria-hidden="true"
            />
            {showDetails ? 'Hide details' : 'Add job link or company details (optional)'}
          </button>
          {showDetails && (
            <div id="portal-details">
              <DetailsFields values={details} onChange={setDetails} linkRef={linkRef} disabled={loading} />
            </div>
          )}

          {error && (
            <Alert tone="danger" role="alert">
              {error}
            </Alert>
          )}
        </div>

        {/* Bottom toolbar: tools on the left, the main action on the right. */}
        <div className="flex flex-wrap items-center gap-2 border-t border-line px-3 py-3 sm:px-4">
          <div className="flex items-center gap-1">
            <AttachmentButton onAttach={setAttachment} onError={setError} disabled={loading} />
            <PortalActions
              onAddLink={addLink}
              onLoadSample={loadSample}
              onClear={clearAll}
              canClear={Boolean(text || attachment || details.link || details.companyName || details.companyWebsite)}
              disabled={loading}
            />
          </div>
          <div className="ml-auto flex items-center gap-3">
            {textLength > 0 && (
              <span
                className={`hidden text-xs tabular-nums sm:inline ${textLength > LIMITS.jobText ? 'font-medium text-red-600' : 'text-ink-muted'}`}
              >
                {textLength.toLocaleString('en-IN')} / {LIMITS.jobText.toLocaleString('en-IN')}
              </span>
            )}
            <Button
              type="submit"
              variant="primary"
              icon={loading ? Spinner : ShieldCheck}
              disabled={!hasInput || loading}
              aria-keyshortcuts="Control+Enter"
            >
              {loading ? 'Checking available evidence…' : 'Analyze Job'}
            </Button>
          </div>
        </div>
      </form>

      {showSuggestions && !hasInput && !loading && <Suggestions onLoadSample={loadSample} />}
    </div>
  )
}

/** Notes about the links we found: which one will be read, and honest site hints. */
function describeLinks(text, linkField, sentUrl) {
  const fieldUrl = isHttpUrl(normalizeUrl(linkField)) ? normalizeUrl(linkField) : null
  const urls = [...new Set([fieldUrl, ...findUrls(text)].filter(Boolean))].slice(0, 3)
  return urls.map((url) => ({
    url,
    host: hostOf(url),
    willRead: url === sentUrl,
    hint: siteHint(url),
  }))
}

function LinkNote({ note }) {
  return (
    <div className="rounded-lg border border-line bg-canvas px-3 py-2 text-sm">
      <p className="flex flex-wrap items-center gap-2">
        <Link2 className="h-4 w-4 text-brand-600" aria-hidden="true" />
        <span className="font-medium text-ink">{note.host}</span>
        <span className="text-ink-muted">
          {note.willRead ? '— TrustHire will open and read this page' : '— link found in the text'}
        </span>
        {note.hint && <Badge tone="neutral">{note.hint.name}</Badge>}
      </p>
      {note.hint && <p className="mt-1 text-xs text-ink-muted">{note.hint.note}</p>}
    </div>
  )
}

/** Shown under the empty portal: what can be pasted, and a labelled sample. */
function Suggestions({ onLoadSample }) {
  const ideas = [
    { icon: FileText, title: 'Job description', text: 'From a job site, company page or PDF.' },
    { icon: MessageSquareText, title: 'Recruiter message', text: 'WhatsApp, Telegram, SMS or e-mail text.' },
    { icon: Link2, title: 'Job link', text: 'A posting URL — TrustHire tries to read the page.' },
  ]
  return (
    <div className="mt-5">
      <ul className="grid gap-3 sm:grid-cols-3">
        {ideas.map(({ icon: Icon, title, text }) => (
          <li key={title} className="rounded-xl border border-line bg-white/70 px-4 py-3">
            <p className="flex items-center gap-2 text-sm font-medium text-ink">
              <Icon className="h-4 w-4 text-brand-500" aria-hidden="true" />
              {title}
            </p>
            <p className="mt-1 text-xs text-ink-muted">{text}</p>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-center text-sm text-ink-muted">
        Just exploring?{' '}
        <button
          type="button"
          onClick={onLoadSample}
          className="rounded font-medium text-brand-600 underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          Load a sample scam-style posting
        </button>{' '}
        (fictional) and analyze it.
      </p>
    </div>
  )
}
