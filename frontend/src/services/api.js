/**
 * api.js — every call to the TrustHire backend goes through this file.
 *
 * The backend's real contract (backend/app/routes.py and schemas.py):
 *
 *   GET  /api/health   -> { status, database, web_search, ai_analysis }
 *   POST /api/analyze  -> body { job_text?, job_url?, company_name?, company_website? }
 *                         reply: trust_score (1-99, HIGHER = MORE trustworthy), trust_level,
 *                         verdict, reasons, checks, extracted, evidence_analysis, analysis_id ...
 *   POST /api/reports  -> body { analysis_id, user_verdict: "scam" | "genuine", comment? }
 *                         reply: { saved: true }
 *
 * We use the browser's built-in fetch() — no extra library needed.
 * Only the backend's PUBLIC address is configured here; every API key
 * (SerpApi, Gemini, Supabase ...) stays on the server.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

// An analysis runs web searches and an AI step, so it can take up to about a minute.
const ANALYZE_TIMEOUT_MS = 120_000
const DEFAULT_TIMEOUT_MS = 15_000

// Friendly names for the fields the backend may complain about.
const FIELD_NAMES = {
  job_text: 'Job description',
  job_url: 'Job link',
  company_name: 'Company name',
  company_website: 'Company website',
  comment: 'Comment',
  analysis_id: 'Analysis id',
  user_verdict: 'Feedback choice',
}

/** An error whose message is safe to show to the user. */
export class ApiError extends Error {
  /**
   * @param {string} message  shown to the user
   * @param {object} info     kind: 'network' | 'timeout' | 'cancelled' | 'http'; status: HTTP code
   */
  constructor(message, { kind = 'http', status = null } = {}) {
    super(message)
    this.kind = kind
    this.status = status
    // Retrying helps for network problems, timeouts and server errors — not for invalid input.
    this.retryable = kind === 'network' || kind === 'timeout' || (status !== null && status >= 500)
  }
}

// ------------------------------------------------------------------
// The three endpoints
// ------------------------------------------------------------------
export function getHealth() {
  return request('/api/health')
}

export function analyzeJob(payload, { signal } = {}) {
  return request('/api/analyze', { method: 'POST', body: payload, timeoutMs: ANALYZE_TIMEOUT_MS, signal })
}

export function sendReport({ analysisId, verdict, comment }) {
  const body = { analysis_id: analysisId, user_verdict: verdict }
  if (comment && comment.trim()) body.comment = comment.trim()
  return request('/api/reports', { method: 'POST', body })
}

// ------------------------------------------------------------------
// Shared request helper
// ------------------------------------------------------------------
async function request(path, { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS, signal } = {}) {
  // One AbortController lets us stop the request on a timeout OR when the user cancels.
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const cancel = () => controller.abort()
  signal?.addEventListener('abort', cancel)

  let response
  try {
    response = await fetch(API_BASE_URL + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
  } catch {
    if (timedOut) {
      throw new ApiError('The server took too long to answer. Please try again in a moment.', { kind: 'timeout' })
    }
    if (signal?.aborted) {
      throw new ApiError('The request was cancelled.', { kind: 'cancelled' })
    }
    throw new ApiError(
      "Can't reach the TrustHire server. Check that the backend is running, then try again.",
      { kind: 'network' },
    )
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', cancel)
  }

  const data = await response.json().catch(() => null) // some error replies are not JSON
  if (!response.ok) {
    throw new ApiError(errorMessage(response.status, data), { status: response.status })
  }
  return data
}

/** Turn an HTTP error into one clear sentence (never a stack trace). */
function errorMessage(status, data) {
  const detail = data?.detail

  if (status === 422) {
    // The backend writes plain-language messages for links it cannot read.
    if (typeof detail === 'string') return detail
    // FastAPI validation errors: a list of { loc: [...], msg }.
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) => {
          const message = String(item?.msg || 'Invalid value').replace(/^Value error,\s*/i, '')
          const field = FIELD_NAMES[item?.loc?.[item.loc.length - 1]]
          return field ? `${field}: ${message}` : message
        })
        .join(' ')
    }
    return 'Some of the information sent was not valid. Please check it and try again.'
  }
  // 502 / 503 replies from our own routes carry a sentence meant for users.
  if ((status === 502 || status === 503) && typeof detail === 'string') return detail
  if (status >= 500) return 'The server ran into a problem. Please try again in a moment.'
  return `The server answered with an unexpected error (${status}).`
}
