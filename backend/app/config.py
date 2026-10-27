"""
config.py — central place for all backend settings.

Values are read from environment variables (or from a local .env file),
so that secrets such as API keys never have to be written into the code.
"""

import os

from dotenv import load_dotenv

# Read backend/.env (if it exists) into the environment.
load_dotenv()

# Frontend addresses that are allowed to call this API from the browser (CORS).
# Vite's dev server runs on http://localhost:5173 by default.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# How long (in seconds) to wait for an external website or WHOIS server.
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))

# How we introduce ourselves to other websites. Some sites (including
# data.gov.in) stall requests that use Python's default "python-requests" name.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrustHire/0.1 (student project)"

# Largest job-posting web page we are willing to download (2 MB).
MAX_PAGE_BYTES = 2_000_000

# Longest job description text we accept (characters).
MAX_JOB_TEXT_CHARS = 20_000

# ------------------------------------------------------------------
# Third-party services. Each one is OPTIONAL: if its keys are empty,
# that feature is switched off and the rest of the API still works.
# ------------------------------------------------------------------

# Supabase (PostgreSQL database) — Project Settings -> API.
# Use the SECRET key (or the legacy "service_role" key). It must only ever
# live here on the server, never in the frontend code.
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

# SerpApi — Google search results as JSON (serpapi.com). Free plan: 250
# searches per month and 50 per hour. Used by the online-reputation check.
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()
# Each analysis uses at most this many searches (each one costs 1 free search).
MAX_SEARCHES_PER_ANALYSIS = int(os.getenv("MAX_SEARCHES_PER_ANALYSIS", "3"))

# Google Gemini API — reads the search results and sorts them into reports,
# warnings and official sources. Key from aistudio.google.com (free tier,
# NO billing). The model name has no default on purpose: pick one that your
# account's free tier lists, e.g. gemini-3.5-flash-lite.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()
# How much the model "thinks" before answering. Gemini 3 models think at
# "medium" by default, which made answers too slow; "low" is enough for sorting
# search results. Allowed values depend on the model (see Google's "thinking"
# docs); leave it empty to use the model's default.
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "low").strip()
# The AI needs longer than a normal website to answer.
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))

# How long search results and AI answers are remembered (in memory), so
# checking the same company twice does not spend the free quota twice.
EVIDENCE_CACHE_HOURS = float(os.getenv("EVIDENCE_CACHE_HOURS", "24"))

# data.gov.in (Open Government Data) — MCA "Company Master Data".
# Free API key: register on data.gov.in -> My Account -> API key.
DATAGOVIN_API_KEY = os.getenv("DATAGOVIN_API_KEY", "").strip()
# Resource = "Registrars of Companies (RoC)-wise Company Master Data".
MCA_RESOURCE_ID = os.getenv("MCA_RESOURCE_ID", "4dbe5667-7b6b-41d7-82af-211562424d9a").strip()
# Company-name column used for the (exact, case-sensitive) name filter.
MCA_NAME_FIELD = os.getenv("MCA_NAME_FIELD", "CompanyName").strip()
