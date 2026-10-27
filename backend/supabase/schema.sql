-- =====================================================================
-- TrustHire database tables
-- How to use: Supabase dashboard -> SQL Editor -> New query ->
--             paste this whole file -> Run.   (Safe to run more than once.)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. analyses: one row per job posting analysed.
--    For privacy we do NOT store the posting text or the recruiter's
--    e-mails / phone numbers — only the score, the model's input
--    features (needed to retrain the model later) and the reasons.
-- ---------------------------------------------------------------------
create table if not exists public.analyses (
  id             uuid primary key,                        -- created by the backend
  created_at     timestamptz not null default now(),
  job_url        text,
  company_name   text,
  website_domain text,
  trust_score    smallint not null check (trust_score between 1 and 99),
  trust_level    text not null check (trust_level in ('high', 'medium', 'low')),
  features       jsonb not null default '{}'::jsonb,       -- e.g. {"domain_age": -3.3, "upfront_payment": 1}
  reasons        jsonb not null default '[]'::jsonb        -- the explanation shown to the user
);

-- ---------------------------------------------------------------------
-- 2. scam_reports: user feedback on an analysis ("this was a scam" /
--    "this was genuine"). These become training labels for the ML phase.
-- ---------------------------------------------------------------------
create table if not exists public.scam_reports (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  analysis_id   uuid not null references public.analyses (id) on delete cascade,
  user_verdict  text not null check (user_verdict in ('scam', 'genuine')),
  comment       text check (char_length(comment) <= 1000)
);

-- Index on the link column, so finding all reports for an analysis stays fast
-- (Supabase's advisor warns about foreign keys without an index).
create index if not exists scam_reports_analysis_id_idx on public.scam_reports (analysis_id);

-- ---------------------------------------------------------------------
-- 3. Security (Row Level Security).
--    The backend connects with the PUBLISHABLE key, which acts as the
--    "anon" role. These rules let it ADD rows only — the publishable key
--    can never read, change or delete stored data.
-- ---------------------------------------------------------------------
alter table public.analyses     enable row level security;
alter table public.scam_reports enable row level security;

grant insert on public.analyses     to anon;
grant insert on public.scam_reports to anon;

drop policy if exists "backend can insert analyses" on public.analyses;
create policy "backend can insert analyses"
  on public.analyses for insert to anon with check (true);

drop policy if exists "backend can insert reports" on public.scam_reports;
create policy "backend can insert reports"
  on public.scam_reports for insert to anon with check (true);

-- ---------------------------------------------------------------------
-- 4. Tell Supabase's API about the new tables straight away.
-- ---------------------------------------------------------------------
notify pgrst, 'reload schema';

-- To view the data, use the Supabase dashboard (Table Editor), which is
-- not limited by these rules.
