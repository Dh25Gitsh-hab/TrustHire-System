"""
analyzer.py — runs the whole TrustHire pipeline for one job posting.

    job text / URL
        │
        ▼
    1. get the text        (posting_fetcher, only if no text was pasted)
        ▼
    2. extract key facts   (feature_extractor: company, domain, salary ...)
        ▼
    3. run all checks      (checks/*: domain, reputation, reviews, registry, red flags)
        ▼                  (reputation = web search via SerpApi + AI reading via Gemini)
    4. trust score         (scoring/trust_score: logistic model + reasons)
        ▼
    5. save the result     (database: Supabase, optional)
        ▼
    AnalyzeResponse  ->  shown to the user
"""

from concurrent.futures import ThreadPoolExecutor

from app import database
from app.checks import domain_check, red_flags, registry_check, reputation_check, review_check
from app.schemas import AnalyzeRequest, AnalyzeResponse, CheckResult
from app.scoring.trust_score import calculate_trust_score
from app.services.feature_extractor import extract_info
from app.services.posting_fetcher import fetch_posting

# The verification modules, in the order they are shown to the user
# (same order as the system architecture diagram).
CHECK_MODULES = [domain_check, reputation_check, review_check, registry_check, red_flags]

DISCLAIMER = (
    "TrustHire is a decision-support tool, not a guarantee. A high score does not prove a job is real, "
    "and a low score is not a legal finding about any company. Never pay money to get a job."
)


def analyze_posting(request: AnalyzeRequest) -> AnalyzeResponse:
    # --- Step 1: get the posting text ------------------------------------
    # If the user pasted text, we analyse that text and use the link only for
    # its domain. If they gave only a link, we download the page.
    # (A PostingFetchError raised here is turned into a friendly 422 by the route.)
    text = (request.job_text or "").strip()
    posting_url = (request.job_url or "").strip() or None
    structured: dict = {}

    if not text and posting_url:
        fetched = fetch_posting(posting_url)
        text, posting_url, structured = fetched.text, fetched.url, fetched.structured

    # --- Step 2: extract the key facts -----------------------------------
    info = extract_info(
        text,
        posting_url=posting_url,
        structured=structured,
        company_name=request.company_name,
        company_website=request.company_website,
    )

    # --- Step 3: run every check at the same time ------------------------
    # The checks wait on slow network calls (WHOIS, APIs), so running them in
    # parallel threads makes the total wait about as long as the slowest one.
    with ThreadPoolExecutor(max_workers=len(CHECK_MODULES)) as pool:
        futures = [pool.submit(_run_safely, module, info, text) for module in CHECK_MODULES]
        checks = [future.result() for future in futures]

    # The reputation check also returns the full web evidence (search results +
    # AI analysis). Move it out of the card into its own response field.
    evidence = None
    for check in checks:
        evidence = check.details.pop("evidence_analysis", evidence)

    # --- Step 4: combine everything into the trust score -----------------
    result = calculate_trust_score(checks)

    response = AnalyzeResponse(
        trust_score=result.score,
        trust_level=result.level,
        verdict=result.verdict,
        reasons=result.reasons,
        checks=checks,
        checks_completed=sum(1 for check in checks if check.status == "completed"),
        checks_total=len(checks),
        extracted=info,
        disclaimer=DISCLAIMER,
        evidence_analysis=evidence,
    )

    # --- Step 5: save it (skipped automatically if Supabase is not set up) -
    response.analysis_id = database.save_analysis(response, posting_url)
    return response


def _run_safely(module, info, text) -> CheckResult:
    """Run one check. If it crashes, report an error card instead of failing the whole analysis."""
    try:
        return module.run(info, text)
    except Exception as error:
        return CheckResult(
            key=module.KEY,
            title=module.TITLE,
            status="error",
            summary=f"This check failed unexpectedly ({type(error).__name__}).",
        )
