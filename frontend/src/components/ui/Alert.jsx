/**
 * Alert — an inline message box (used instead of browser alert() pop-ups).
 * tone: info | warning | danger | positive | neutral
 * action: optional button(s) shown under the text, e.g. "Try again".
 */
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'
import { TONE_CLASSES } from './tones.js'

const ICONS = { info: Info, neutral: Info, warning: AlertTriangle, danger: XCircle, positive: CheckCircle2 }

export default function Alert({ tone = 'info', title, children, action, className = '', role }) {
  const Icon = ICONS[tone]
  return (
    <div
      role={role || (tone === 'danger' ? 'alert' : 'status')}
      className={`flex gap-3 rounded-lg border px-4 py-3 text-sm ${TONE_CLASSES[tone]} ${className}`}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={title ? 'mt-0.5 opacity-90' : ''}>{children}</div>}
        {action && <div className="mt-3 flex flex-wrap gap-2">{action}</div>}
      </div>
    </div>
  )
}
