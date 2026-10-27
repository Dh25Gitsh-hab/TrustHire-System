/**
 * DetailsFields — the optional extra fields of the portal:
 * a dedicated job link, the company name and the company website.
 * They map 1-to-1 to the backend's job_url, company_name and company_website,
 * and help it find the right company when the text does not say clearly.
 */
import { LIMITS } from '../../utils/input.js'

export default function DetailsFields({ values, onChange, linkRef, disabled }) {
  const update = (field) => (event) => onChange({ ...values, [field]: event.target.value })

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Field
        id="job-link"
        label="Job link"
        hint="The page TrustHire should read"
        className="sm:col-span-2"
        inputRef={linkRef}
        type="url"
        inputMode="url"
        placeholder="https://company.com/careers/job-123"
        value={values.link}
        onChange={update('link')}
        maxLength={LIMITS.jobUrl}
        disabled={disabled}
      />
      <Field
        id="company-name"
        label="Company name"
        placeholder="e.g. Acme Analytics Pvt Ltd"
        value={values.companyName}
        onChange={update('companyName')}
        maxLength={LIMITS.companyName}
        disabled={disabled}
      />
      <Field
        id="company-website"
        label="Company website"
        placeholder="e.g. acme-analytics.in"
        value={values.companyWebsite}
        onChange={update('companyWebsite')}
        maxLength={LIMITS.companyWebsite}
        disabled={disabled}
      />
    </div>
  )
}

function Field({ id, label, hint, className = '', inputRef, ...inputProps }) {
  return (
    <div className={className}>
      <label htmlFor={id} className="flex items-baseline justify-between gap-2 text-xs font-medium text-ink-soft">
        {label}
        {hint && <span className="font-normal text-ink-muted">{hint}</span>}
      </label>
      <input
        id={id}
        ref={inputRef}
        autoComplete="off"
        spellCheck={false}
        className="mt-1 block h-10 w-full rounded-lg border border-line bg-white px-3 text-base text-ink sm:text-[15px] placeholder:text-ink-muted/60 focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100 disabled:bg-canvas"
        {...inputProps}
      />
    </div>
  )
}
