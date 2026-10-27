/**
 * PortalActions — the share-style button next to the paperclip. It opens a
 * small menu of REAL actions only:
 *   * Add a job link        -> opens the optional details and focuses the link field
 *   * Load a sample posting -> fills in a clearly labelled, fictional example
 *   * Clear input           -> empties everything
 *   * Share TrustHire       -> the browser's native share sheet, when it has one;
 *                              otherwise "Copy link to TrustHire" (clipboard)
 */
import { useEffect, useRef, useState } from 'react'
import { Copy, Eraser, FileText, Link2, Share, Share2 } from 'lucide-react'
import Button from '../ui/Button.jsx'

export default function PortalActions({ onAddLink, onLoadSample, onClear, canClear, disabled }) {
  const [open, setOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const wrapperRef = useRef(null)
  const toggleRef = useRef(null)
  const menuRef = useRef(null)

  const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'
  const canCopy = typeof navigator !== 'undefined' && Boolean(navigator.clipboard?.writeText)
  const appUrl = typeof window !== 'undefined' ? window.location.origin : ''

  // While open: close on a click outside or on Escape, and move focus into the menu.
  useEffect(() => {
    if (!open) return
    menuRef.current?.querySelector('button:not(:disabled)')?.focus()
    function onPointerDown(event) {
      if (!wrapperRef.current?.contains(event.target)) setOpen(false)
    }
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        setOpen(false)
        toggleRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  // Hide the "Link copied" note after a moment.
  useEffect(() => {
    if (!notice) return
    const timer = setTimeout(() => setNotice(''), 2500)
    return () => clearTimeout(timer)
  }, [notice])

  function run(action) {
    setOpen(false)
    action()
  }

  async function shareApp() {
    try {
      await navigator.share({ title: 'TrustHire', text: 'Check a job posting before you trust it.', url: appUrl })
    } catch {
      // The user closed the share sheet — nothing to do.
    }
  }

  async function copyAppLink() {
    try {
      await navigator.clipboard.writeText(appUrl)
      setNotice('Link copied')
    } catch {
      setNotice('Could not copy the link')
    }
  }

  return (
    <div ref={wrapperRef} className="relative">
      <Button
        ref={toggleRef}
        variant="ghost"
        size="icon"
        icon={Share2}
        onClick={() => setOpen((value) => !value)}
        disabled={disabled}
        aria-label="More options"
        title="More options"
        aria-haspopup="true"
        aria-expanded={open}
        aria-controls="portal-actions-menu"
      />
      {open && (
        <div
          ref={menuRef}
          id="portal-actions-menu"
          className="absolute bottom-full left-0 z-20 mb-2 w-64 rounded-xl border border-line bg-white p-1.5 shadow-portal"
        >
          <MenuItem icon={Link2} onClick={() => run(onAddLink)}>
            Add a job link
          </MenuItem>
          <MenuItem icon={FileText} onClick={() => run(onLoadSample)} hint="Fictional example for demonstration">
            Load a sample posting
          </MenuItem>
          <MenuItem icon={Eraser} onClick={() => run(onClear)} disabled={!canClear}>
            Clear input
          </MenuItem>
          {(canShare || canCopy) && <div className="my-1.5 border-t border-line" role="separator" />}
          {canShare ? (
            <MenuItem icon={Share} onClick={() => run(shareApp)}>
              Share TrustHire
            </MenuItem>
          ) : (
            canCopy && (
              <MenuItem icon={Copy} onClick={() => run(copyAppLink)}>
                Copy link to TrustHire
              </MenuItem>
            )
          )}
        </div>
      )}
      <span className="sr-only" aria-live="polite">
        {notice}
      </span>
      {notice && (
        <span className="absolute bottom-full left-0 mb-2 whitespace-nowrap rounded-md bg-ink px-2 py-1 text-xs text-white">
          {notice}
        </span>
      )}
    </div>
  )
}

function MenuItem({ icon: Icon, children, hint, ...props }) {
  return (
    <button
      type="button"
      className="flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-canvas focus-visible:bg-canvas focus-visible:outline-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:text-ink-muted/60 disabled:hover:bg-transparent"
      {...props}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-ink-muted" aria-hidden="true" />
      <span>
        {children}
        {hint && <span className="block text-xs text-ink-muted">{hint}</span>}
      </span>
    </button>
  )
}
