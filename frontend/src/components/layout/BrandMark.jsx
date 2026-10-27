/**
 * BrandMark — TrustHire's logo: a shield with a check mark (Lucide icon)
 * next to the wordmark. No image file needed.
 */
import { ShieldCheck } from 'lucide-react'

export default function BrandMark({ size = 'md' }) {
  const box = size === 'lg' ? 'h-11 w-11 rounded-xl' : 'h-8 w-8 rounded-lg'
  const icon = size === 'lg' ? 'h-6 w-6' : 'h-[18px] w-[18px]'
  return (
    <span className="inline-flex items-center gap-2.5">
      <span className={`flex items-center justify-center bg-brand-600 text-white shadow-sm ${box}`}>
        <ShieldCheck className={icon} strokeWidth={2.2} aria-hidden="true" />
      </span>
      {size !== 'lg' && <span className="text-[17px] font-semibold tracking-tight text-ink">TrustHire</span>}
    </span>
  )
}
