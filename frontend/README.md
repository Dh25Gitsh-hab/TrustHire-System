# TrustHire — Frontend (React + Vite + Tailwind CSS)

The web app where users paste a job posting (or its link) and see TrustHire's
explainable trust score. It talks only to the TrustHire backend. **All API keys
stay on the server.**

## Run it

The backend must be running first (see `../backend/README.md`), on <http://localhost:8000>.

```bash
cd frontend
npm install        # first time only
npm run dev        # opens on http://localhost:5173
```

| Command           | What it does                                     |
|-------------------|--------------------------------------------------|
| `npm run dev`     | development server with live reload (port 5173)  |
| `npm run build`   | production build into `dist/`                    |
| `npm run preview` | serves the production build locally              |

Port 5173 is fixed (`strictPort`) because the backend only accepts browser requests from
`http://localhost:5173` (`ALLOWED_ORIGINS` in `backend/.env`).

`.npmrc` sets `legacy-peer-deps=true`. This works around an npm 10.8 crash ("reading
'edgesOut'") with Vite 8's plugins. The peer versions were checked by hand and are compatible.

## Settings

Copy `.env.example` to `.env` only if you need to change something:

| Variable            | Default                 | Meaning                     |
|---------------------|-------------------------|-----------------------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | address of the backend API  |

Every `VITE_` variable is **public**: it is built into the JavaScript that every visitor
downloads. Never put SerpApi, Gemini, Supabase or data.gov.in keys here.

## Backend endpoints used (`src/services/api.js`)

| Method | Path           | Used for                                                  |
|--------|----------------|-----------------------------------------------------------|
| GET    | `/api/health`  | "Server online" indicator in the header                   |
| POST   | `/api/analyze` | `{ job_text?, job_url?, company_name?, company_website? }` |
| POST   | `/api/reports` | "Report as suspicious" / "Mark as genuine"                |

The backend has no history endpoint (its database key can only *add* rows), so the app has
no "recent analyses" page.

## What the portal accepts

- **Text:** a job description, recruiter message or offer (up to 20,000 characters).
- **A link:** if the box holds only a link, it is sent as `job_url` and the backend reads the
  page. LinkedIn, social media and chat links get an honest "probably can't be read" note.
  There is also an optional "Job link" field.
- **A `.txt` file** (paperclip, up to 200 KB). It is read in the browser and sent as text.
  The backend has no upload endpoint, so PDF, Word and image files are not accepted; the user
  is asked to paste the text instead.

## Folder structure

```text
src/
├── main.jsx, App.jsx          # start-up; page layout and the analysis flow
├── index.css                  # Tailwind v4 + design tokens (@theme)
├── services/api.js            # the only place that calls the backend
├── hooks/useHealth.js         # GET /api/health
├── utils/input.js             # link detection, validation, request body
├── utils/labels.js            # backend codes -> words, colours, icons
├── data/samples.js            # the fictional sample posting
└── components/
    ├── layout/                # Header, Footer, BrandMark
    ├── Hero.jsx, HowItWorks.jsx
    ├── portal/                # JobAnalysisPortal, AttachmentButton, PortalActions, DetailsFields
    ├── results/               # TrustScore, ReasonList, CheckGrid, EvidencePanel, EvidenceItem,
    │                          # FeedbackActions, LoadingState, AnalysisResults
    └── ui/                    # Button, Badge, Card, Alert, ExternalLink, Spinner
```

## How results are shown

- **`trust_score`** is shown exactly as sent: 1–99, and higher means **more** trustworthy.
  The colour follows the backend's `trust_level`; the app adds no thresholds of its own.
- **Reasons** are split into warning signs and reassuring signs. Each bar shows its share of
  the score.
- **Web evidence:** the AI's own concern score (higher = more concerning) is shown for context
  only and does not change the trust score. Allegations are labelled **Unverified**. Links open
  in a new tab with `rel="noopener noreferrer nofollow"`, and only `http(s)` links are clickable.
- **Partial results** (a check that couldn't run, search quota used up, AI unavailable) are
  stated plainly and never shown as suspicious.
