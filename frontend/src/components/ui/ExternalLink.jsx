/**
 * ExternalLink — opens a link from the analysis in a new tab, safely:
 *  * only http:// and https:// links become clickable (never "javascript:" etc.),
 *  * rel="noopener noreferrer" stops the other site from controlling this tab
 *    and from seeing which page sent the visitor; "nofollow" marks it as untrusted.
 */
import { ExternalLink as ExternalIcon } from 'lucide-react'

export function isSafeUrl(url) {
  try {
    const { protocol } = new URL(url)
    return protocol === 'http:' || protocol === 'https:'
  } catch {
    return false
  }
}

export default function ExternalLink({ href, children, className = '', showIcon = true }) {
  if (!isSafeUrl(href)) return <span className={className}>{children}</span>
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className={`inline-flex items-start gap-1 rounded text-brand-600 underline-offset-2 hover:text-brand-700 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 ${className}`}
    >
      <span className="min-w-0 wrap-break-word">{children}</span>
      {showIcon && <ExternalIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  )
}
