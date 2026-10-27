/**
 * Spinner — a turning loader icon. It accepts the same props as a Lucide
 * icon, so it can be passed as a Button's `icon` while something is loading.
 */
import { Loader2 } from 'lucide-react'

export default function Spinner({ className = '', ...props }) {
  return <Loader2 {...props} className={`${className} animate-spin`} />
}
