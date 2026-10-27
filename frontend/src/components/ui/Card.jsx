/**
 * Card — a white surface with a subtle border. Optional header:
 * an icon, a title, a one-line description and something on the right (`aside`).
 */
export default function Card({ title, description, icon: Icon, aside, children, className = '', as: Tag = 'section', ...props }) {
  return (
    <Tag className={`rounded-xl border border-line bg-white shadow-card ${className}`} {...props}>
      {(title || aside) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4 sm:px-6">
          <div className="flex min-w-0 items-start gap-3">
            {Icon && (
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </span>
            )}
            <div className="min-w-0">
              {title && <h3 className="text-base font-semibold text-ink">{title}</h3>}
              {description && <p className="mt-0.5 text-sm text-ink-muted">{description}</p>}
            </div>
          </div>
          {aside}
        </header>
      )}
      <div className="px-5 py-5 sm:px-6">{children}</div>
    </Tag>
  )
}
