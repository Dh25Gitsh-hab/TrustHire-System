/**
 * input.js — helpers for what the user types into the analysis portal:
 * finding links, recognising job sites, checking the input and building
 * the exact JSON body the backend's POST /api/analyze expects.
 */

// Same limits as the backend (backend/app/schemas.py), so we can warn early.
export const LIMITS = {
  jobText: 20_000,
  jobUrl: 2_000,
  companyName: 200,
  companyWebsite: 500,
}

const URL_IN_TEXT_RE = /https?:\/\/[^\s<>"']+/gi

/** True if `value` is a complete http:// or https:// web address. */
export function isHttpUrl(value) {
  try {
    const url = new URL(String(value).trim())
    return (url.protocol === 'http:' || url.protocol === 'https:') && url.hostname.includes('.')
  } catch {
    return false
  }
}

/** "www.naukri.com/job/1" -> "https://www.naukri.com/job/1". Text with spaces is left alone. */
export function normalizeUrl(value) {
  const trimmed = String(value || '').trim()
  if (!trimmed || /^https?:\/\//i.test(trimmed) || /\s/.test(trimmed)) return trimmed
  return /^[\w-]+(\.[\w-]+)+/.test(trimmed) ? `https://${trimmed}` : trimmed
}

/** All web links inside a piece of text, without duplicates. */
export function findUrls(text) {
  const matches = String(text || '').match(URL_IN_TEXT_RE) || []
  // Drop punctuation that usually ends a sentence rather than the link: "visit https://x.com."
  return [...new Set(matches.map((link) => link.replace(/[.,;:!?)\]}]+$/, '')))]
}

/** The website name of a link: "https://www.naukri.com/x" -> "naukri.com". */
export function hostOf(link) {
  try {
    return new URL(link).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

// Sites we recognise, with an honest note about whether the backend can read them.
const KNOWN_SITES = [
  { match: ['linkedin.com'], name: 'LinkedIn', note: 'LinkedIn usually shows job pages only after login, so this link probably cannot be read. Paste the job description as well.' },
  { match: ['facebook.com', 'instagram.com'], name: 'Social media', note: 'Social media posts usually need a login, so this link probably cannot be read. Paste the post text as well.' },
  { match: ['wa.me', 'whatsapp.com', 't.me', 'telegram.me'], name: 'Chat app', note: 'This is a chat link, not a job page. Paste the message you received instead.' },
  { match: ['naukri.com'], name: 'Naukri' },
  { match: ['indeed.com', 'indeed.co.in'], name: 'Indeed' },
  { match: ['internshala.com'], name: 'Internshala' },
  { match: ['glassdoor.com', 'glassdoor.co.in'], name: 'Glassdoor' },
  { match: ['foundit.in', 'monsterindia.com'], name: 'foundit' },
  { match: ['shine.com'], name: 'Shine' },
  { match: ['apna.co'], name: 'apna' },
  { match: ['unstop.com'], name: 'Unstop' },
]

const DEFAULT_JOB_SITE_NOTE =
  'TrustHire will try to read this page. Some job sites build their pages with JavaScript or need a login — if it cannot be read, paste the description as well.'

/** A short hint for a link, or null for an ordinary company website. */
export function siteHint(link) {
  const host = hostOf(link)
  const site = KNOWN_SITES.find((entry) => entry.match.some((domain) => host === domain || host.endsWith(`.${domain}`)))
  if (!site) return null
  return { name: site.name, note: site.note || DEFAULT_JOB_SITE_NOTE }
}

/**
 * Build the body for POST /api/analyze from the portal's fields.
 * If the text box holds nothing but a link, that link is sent as job_url,
 * so the backend downloads and reads the page.
 */
export function buildPayload({ text, link, companyName, companyWebsite, attachment }) {
  let typed = String(text || '').trim()
  let jobUrl = normalizeUrl(link)

  if (!jobUrl && isHttpUrl(typed)) {
    jobUrl = typed
    typed = ''
  }
  const jobText = [typed, attachment?.text?.trim()].filter(Boolean).join('\n\n')

  const payload = {}
  if (jobText) payload.job_text = jobText
  if (jobUrl) payload.job_url = jobUrl
  if (companyName?.trim()) payload.company_name = companyName.trim()
  if (companyWebsite?.trim()) payload.company_website = companyWebsite.trim()
  return payload
}

/** Check the body before sending it. Returns a message for the user, or null if it is fine. */
export function validatePayload(payload, { link } = {}) {
  if (!payload.job_text && !payload.job_url) {
    return 'Paste a job description or a job link first.'
  }
  if (link?.trim() && !isHttpUrl(normalizeUrl(link))) {
    return 'The job link does not look like a web address. It should start with http:// or https://.'
  }
  if (payload.job_url && payload.job_url.length > LIMITS.jobUrl) {
    return 'The job link is too long.'
  }
  if (payload.job_text && payload.job_text.length > LIMITS.jobText) {
    return `The text is too long (${payload.job_text.length.toLocaleString('en-IN')} characters). Keep it under ${LIMITS.jobText.toLocaleString('en-IN')} — the main job description is enough.`
  }
  if (payload.company_name && payload.company_name.length > LIMITS.companyName) {
    return `The company name is too long (max ${LIMITS.companyName} characters).`
  }
  if (payload.company_website && payload.company_website.length > LIMITS.companyWebsite) {
    return 'The company website is too long.'
  }
  return null
}
