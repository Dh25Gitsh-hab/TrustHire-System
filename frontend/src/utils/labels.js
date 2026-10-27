/**
 * labels.js — turns the backend's codes into words, colours and icons.
 * Keeping them in one place means every component uses the same wording.
 */
import {
  AlertTriangle,
  CircleHelp,
  Globe,
  Landmark,
  MessagesSquare,
  Search,
} from 'lucide-react'

// trust_level comes from the backend (high >= 70, medium 40-69, low < 40).
export const TRUST_LEVELS = {
  high: { label: 'High trust', tone: 'positive', ring: '#0f8a7e' },
  medium: { label: 'Medium trust', tone: 'warning', ring: '#b7791f' },
  low: { label: 'Low trust', tone: 'danger', ring: '#c2413b' },
}

// CheckResult.status
export const CHECK_STATUS = {
  completed: { label: 'Completed', tone: 'positive' },
  not_configured: { label: 'Not connected', tone: 'neutral' },
  skipped: { label: 'Skipped', tone: 'neutral' },
  error: { label: "Couldn't run", tone: 'warning' },
}

// One icon per verification module (CheckResult.key).
export const CHECK_ICONS = {
  domain_age: Globe,
  reputation: Search,
  reviews: MessagesSquare,
  registry: Landmark,
  red_flags: AlertTriangle,
}
export const FallbackCheckIcon = CircleHelp

// Which signal family a reason's feature belongs to (shown as a small tag).
export function featureFamily(feature) {
  if (feature.startsWith('domain_') || feature === 'age_claim_mismatch') return 'Domain'
  if (feature.startsWith('registry_') || feature === 'incorporation_age') return 'Registry'
  if (feature === 'web_scam_reports') return 'Web reports'
  return 'Red flag'
}

// EvidenceAnalysis.status
export const EVIDENCE_STATUS = {
  completed: { tone: 'info', title: 'Analysed by AI from public search results' },
  partial: { tone: 'warning', title: 'Search worked, but the AI analysis is unavailable' },
  unavailable: { tone: 'warning', title: 'Web evidence is unavailable right now' },
  not_configured: { tone: 'neutral', title: 'Web evidence is not connected on this server' },
  skipped: { tone: 'neutral', title: 'Nothing to search for' },
}

// EvidenceItem.category
export const EVIDENCE_CATEGORY = {
  scam_report: { label: 'Scam report', tone: 'danger' },
  impersonation_warning: { label: 'Impersonation warning', tone: 'warning' },
  official: { label: 'Official source', tone: 'brand' },
  neutral_info: { label: 'General information', tone: 'neutral' },
  not_analysed: { label: 'Not analysed', tone: 'neutral' },
}

// EvidenceItem.verification — allegations are always labelled as unverified.
export const EVIDENCE_VERIFICATION = {
  verified_fact: { label: 'Official / verified source', tone: 'positive' },
  allegation: { label: 'Unverified allegation', tone: 'warning' },
  weak_signal: { label: 'Weak signal', tone: 'neutral' },
  unknown: { label: 'Not verified', tone: 'neutral' },
}

// EvidenceItem.signal -> colour of the item's left edge.
export const SIGNAL_EDGE = {
  suspicious: 'border-l-red-400',
  reassuring: 'border-l-teal-500',
  neutral: 'border-l-line-strong',
}

// Readable names for the facts in each check's `details` (backend/app/checks/*.py).
const DETAIL_LABELS = {
  // domain_check
  domain: 'Domain',
  domain_source: 'Found in',
  registrar: 'Registrar',
  creation_date: 'Registered on',
  expiration_date: 'Expires on',
  age_days: 'Age (days)',
  // registry_check
  registered_name: 'Registered name',
  cin: 'CIN',
  status: 'Status',
  registration_date: 'Incorporated on',
  company_class: 'Company class',
  state: 'State',
  roc: 'Registrar of Companies',
  names_tried: 'Names tried',
  // reputation_check
  results_found: 'Search results',
  report_sites: 'Scam-report websites',
  ai_risk_score: 'AI concern (0–100)',
  // red_flags
  salary_monthly_inr: 'Salary per month',
  reference_monthly_inr: 'Typical per month',
  ratio: 'Salary vs typical',
}

/** Label for a detail key; unknown keys: "registration_date" -> "Registration date". */
export function detailLabel(key) {
  if (DETAIL_LABELS[key]) return DETAIL_LABELS[key]
  const text = String(key).replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Readable value for the facts list of a check card. */
export function formatDetail(key, value) {
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'number') {
    if (key.endsWith('_inr')) return `₹${value.toLocaleString('en-IN')}`
    if (key === 'ratio') return `${value}×`
    return value.toLocaleString('en-IN')
  }
  return String(value)
}

/** 2048 -> "2 KB" */
export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  return `${Math.round(bytes / 1024).toLocaleString('en-IN')} KB`
}
