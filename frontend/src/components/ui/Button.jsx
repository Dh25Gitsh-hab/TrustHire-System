/**
 * Button — the one button style used across TrustHire.
 *
 * variant: 'primary' (the main action), 'secondary' (bordered), 'ghost' (quiet)
 * size:    'md' | 'sm' | 'icon' (square, for icon-only buttons — give it an aria-label)
 * icon:    a Lucide icon component shown before the text
 * ref:     React 19 passes `ref` like any other prop (used to move keyboard focus).
 */
const VARIANTS = {
  primary:
    'bg-brand-600 text-white shadow-sm hover:bg-brand-700 disabled:bg-brand-200 disabled:text-white/90 disabled:shadow-none',
  secondary:
    'border border-line bg-white text-ink hover:border-line-strong hover:bg-canvas disabled:text-ink-muted/60',
  ghost: 'text-ink-soft hover:bg-canvas hover:text-ink disabled:text-ink-muted/50',
}

const SIZES = {
  md: 'h-10 gap-2 px-4 text-sm',
  sm: 'h-8 gap-1.5 px-3 text-sm',
  icon: 'h-9 w-9 justify-center',
}

export default function Button({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  className = '',
  children,
  type = 'button',
  ref,
  ...props
}) {
  return (
    <button
      ref={ref}
      type={type}
      className={[
        'inline-flex shrink-0 items-center rounded-lg font-medium transition-colors duration-150',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500',
        'disabled:cursor-not-allowed',
        VARIANTS[variant],
        SIZES[size],
        className,
      ].join(' ')}
      {...props}
    >
      {Icon && <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />}
      {children}
    </button>
  )
}
