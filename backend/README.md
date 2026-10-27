# TrustHire — Backend (Python 3.10+ / FastAPI)

The backend receives a job posting (pasted text or a link), checks **the company
behind it**, and returns an explainable **trust score (1–99)**.

## Run it

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # then fill in the keys (macOS/Linux: cp)
uvicorn app.main:app --reload
```

Open **<http://localhost:8000/docs>**. It shows every endpoint, and the example posting is already filled in so you can try it straight away.

Run the tests with `pytest` from the `backend` folder. The tests switch every third-party
service off (see `tests/conftest.py`), so they never use real keys or write to the
database.

## Third-party services (all optional)

Each service reads its keys from `backend/.env`, which is **never committed**. If a key is
empty, that feature switches itself off and everything else keeps working.

| Service                      | Used for                                                      | `.env` keys                                      | Status             |
|------------------------------|---------------------------------------------------------------|--------------------------------------------------|--------------------|
| WHOIS (python-whois)         | domain age                                                    | – (no key)                                       | live               |
| data.gov.in (MCA data)       | company registration                                          | `DATAGOVIN_API_KEY`                              | live               |
| Supabase                     | saving analyses + reports                                     | `SUPABASE_URL`, `SUPABASE_KEY`                   | live               |
| SerpApi (free plan)          | Google results as JSON (incl. public Reddit / LinkedIn pages) | `SERPAPI_API_KEY`                                | needs key          |
| Google Gemini (free tier)    | AI labels the search results                                  | `GEMINI_API_KEY`, `GEMINI_MODEL`                 | needs key          |
| Glassdoor / AmbitionBox      | reviews                                                       | – (no free API)                                  | manual links       |

**Adding the SerpApi and Gemini keys.** Open `backend/.env` and add:

```text
SERPAPI_API_KEY=<from serpapi.com -> Dashboard -> Your Private API Key>
GEMINI_API_KEY=<from aistudio.google.com -> Get API key>
GEMINI_MODEL=gemini-3.5-flash-lite
```

Do **not** set up billing in AI Studio. Without billing the key stays on the free tier.
Then run `python check_services.py`. It checks both keys with free calls (SerpApi's Account
API and Gemini's model list), spends no quota, and never prints the keys. Restart `uvicorn`
after changing `.env`.

**Free quota.** SerpApi's free plan gives 250 searches a month (50 an hour). Each analysis uses
at most `MAX_SEARCHES_PER_ANALYSIS` searches (default 3, so about 80 analyses a month). Results
and AI answers are cached in memory for `EVIDENCE_CACHE_HOURS` (default 24). When a quota runs
out, the reputation card says so and **the signal is left out**. A failure is never counted as
suspicious.

**Supabase setup (one time):** open the Supabase dashboard, go to **SQL Editor**, paste
`supabase/schema.sql`, and click **Run**. This creates the `analyses` and `scam_reports`
tables. Row-level security lets the backend's publishable key *insert only*. To see the
data, use the dashboard's Table Editor.

## API

| Method   | Path              | What it does                                                                |
|----------|-------------------|-----------------------------------------------------------------------------|
| GET      | `/api/health`     | server status, and which services (database, web search, AI) are configured |
| POST     | `/api/analyze`    | `{job_text?, job_url?, company_name?, company_website?}` → trust report     |
| POST     | `/api/reports`    | `{analysis_id, user_verdict: "scam"/"genuine", comment?}` → saves feedback  |

## Folder structure

```text
backend/
├── app/
│   ├── main.py                 # starts FastAPI, enables CORS for the React app
│   ├── routes.py               # the API endpoints
│   ├── schemas.py              # request / response shapes (Pydantic)
│   ├── config.py               # settings + keys read from .env
│   ├── database.py             # Supabase: save analyses and user reports
│   ├── services/
│   │   ├── analyzer.py         # the pipeline: fetch → extract → checks → score → save
│   │   ├── posting_fetcher.py  # downloads a posting from a URL (with safety checks)
│   │   ├── feature_extractor.py# finds company, domain, salary, e-mails ... in text
│   │   ├── web_search.py       # SerpApi: Google results as JSON (queries, parsing, de-duplication)
│   │   ├── gemini_client.py    # Gemini REST call that returns JSON
│   │   ├── evidence_analyzer.py# prompt + safety rules + checking the AI's answer
│   │   └── cache.py            # in-memory cache that saves free quota
│   ├── checks/                 # one file per verification signal family
│   │   ├── domain_check.py     # 1. WHOIS domain age
│   │   ├── reputation_check.py # 2. web reputation (SerpApi search + Gemini labels)
│   │   ├── review_check.py     # 3. Glassdoor / AmbitionBox (manual links)
│   │   ├── registry_check.py   # 4. MCA registration via data.gov.in
│   │   ├── red_flags.py        # 5. hiring-process red flags
│   │   └── links.py            # builds the "verify it yourself" links
│   └── scoring/
│       ├── weights.py          # model weights (starting values)
│       └── trust_score.py      # logistic formula + plain-language reasons
├── supabase/schema.sql         # database tables (run once in Supabase)
├── check_services.py           # checks the SerpApi / Gemini keys without using quota
└── tests/                      # pytest tests (no internet, no real keys)
```

## How a posting is analysed

1. **Get the text.** If the user pasted text, we use it. If they gave only a link,
   `posting_fetcher` downloads the page. Many job boards embed structured
   `JobPosting` data, which gives us a reliable company name, website and salary.
2. **Extract the key facts.** These are the company name, website domain, e-mails,
   phone numbers, salary in ₹ per month, experience, and claims like "established in 2005".
3. **Run the 5 checks in parallel.** Each check returns a status
   (`completed` / `skipped` / `not_configured` / `error`) and a list of **signals**.
   A signal is a feature name, a number and a sentence for the user.
4. **Score the posting** with logistic regression (research paper, Section V-B):

   ```text
   impact  = weight[feature] × value        (+ raises trust, − lowers trust)
   z       = bias + Σ impacts
   trust   = sigmoid(z) = 1 / (1 + e^−z)    → score = trust × 100, kept in 1..99
   ```

   Each impact is simply weight × value, so the **reasons** list shows exactly how
   much each signal moved the score. This is the paper's explainability layer
   (Section V-C).
5. **Save the result** in Supabase if it is configured. We store the score, the features
   and the reasons, but **not** the posting text or the recruiter's contact details.

| Score    | Level    | Meaning                                      |
|----------|----------|----------------------------------------------|
| 70–99    | high     | no major warning signs                       |
| 40–69    | medium   | some warning signs or missing information    |
| 1–39     | low      | strong scam warning signs                    |

The weights in `scoring/weights.py` are **hand-set starting values**. In the ML
phase (weeks 9–10) they will be replaced by weights learned from labelled data,
and XGBoost + SHAP will be compared against this model.

`trust_score` is a **trust** score: higher means more trustworthy. It is a
logistic formula with hand-set weights, so it is **not a calibrated probability**.
A score of 80 does not mean "80% chance the job is real".

### Online reputation: web search + AI (signal family 2)

1. `web_search.py` runs up to 3 Google searches through SerpApi:
   - scam reports about the company,
   - what other sites say about its website,
   - public Reddit / LinkedIn pages about it,
   - its official website (used when the posting gives no website).

   We never log in to or scrape Reddit or LinkedIn. We only see the top results that Google
   has publicly indexed.
2. `evidence_analyzer.py` sends Gemini the results (title, link, snippet) plus the company
   name, website and "years in business" claim. **Not** sent: the posting text, e-mails,
   phone numbers, or the other checks' results (so nothing is counted twice).
   - Gemini labels each result: `official` / `scam_report` / `impersonation_warning` /
     `neutral_info`, and `verified_fact` / `allegation` / `weak_signal` / `unknown`.
   - Search results are treated as untrusted data.
   - The AI can only point to results by id. Unknown ids are dropped, and titles and links
     always come from SerpApi.
3. **One** number enters the formula:

   ```text
   web_scam_reports = min(independent websites with scam reports about the company, 3) / 3
   weight = -1.2      →  0 sites: no effect · 1: -0.4 · 2: -0.8 · 3+: -1.2
   ```

   Independent means different domains, not counting the company's own site. Impersonation
   warnings don't count.
4. Gemini's own `risk_score` (0–100, **higher = more concerning**) is returned in
   `evidence_analysis` for the user to read. It **never** changes `trust_score`.

## Signals

| Feature                    | From             | Meaning                                                             |
|----------------------------|------------------|---------------------------------------------------------------------|
| `domain_age`               | WHOIS            | log(1+days) − log(366): below 0 if under a year old                 |
| `domain_age_hidden`        | WHOIS            | registration date not shown                                         |
| `domain_unregistered`      | WHOIS            | the posting's website does not exist                                |
| `age_claim_mismatch`       | WHOIS + text     | "20 years in business" but the domain is under a year old           |
| `web_scam_reports`         | SerpApi + Gemini | independent sites reporting the company as a scam, 0..1 (see above) |
| `registry_match`           | MCA              | a registered company with that exact name exists                    |
| `incorporation_age`        | MCA              | same log scale as domain age                                        |
| `registry_inactive`        | MCA              | registered, but struck off / dormant / liquidated                   |
| `registry_not_found`       | MCA              | no exact name match (weak signal)                                   |
| `upfront_payment`          | red flags        | registration fee / security deposit                                 |
| `offplatform_contact`      | red flags        | WhatsApp / Telegram                                                 |
| `no_interview`             | red flags        | "direct joining", "100% job guarantee"                              |
| `sensitive_info_request`   | red flags        | Aadhaar / PAN / bank details / OTP                                  |
| `free_email`               | red flags        | recruiter uses gmail.com etc.                                       |
| `salary_too_high`          | red flags        | ≥1.5× the reference salary for the experience level                 |

Phrases are ignored when a negation comes just before them in the same sentence.
For example, *"we never charge a registration fee"* is not flagged.

## Notes and limitations

- **MCA lookup:** the data.gov.in name filter is exact and case-sensitive. We convert names
  to MCA style ("Pvt. Ltd." → "PRIVATE LIMITED", in capitals) and try the common endings.
  A name written differently in the posting will show as "not found", which is why that
  signal is weak.
- **data.gov.in stalls Python's default User-Agent,** so requests send `config.USER_AGENT`.
- The salary reference table in `checks/red_flags.py` uses **placeholder values**.
  Replace them with figures from a cited source before evaluation.
