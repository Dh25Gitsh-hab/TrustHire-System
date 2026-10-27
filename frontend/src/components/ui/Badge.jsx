/**
 * Badge — a small coloured label, e.g. "Completed" or "Unverified allegation".
 * tone: neutral | brand | info | positive | warning | danger (see tones.js)
 */
import { TONE_CLASSES } from './tones.js'

export default function Badge({ tone = 'neutral', icon: Icon, children, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]} ${className}`}
    >
      {Icon && <Icon className="h-3.5 w-3.5" aria-hidden="true" />}
      {children}
    </span>
  )
}
