"""
review_check.py — Signal family 3: Public employee reviews.

Goal (research paper, Section IV-C): combine review count, average rating
and recency from platforms such as Glassdoor and AmbitionBox. A company with
no reviews at all is NOT treated as a rating of zero — new, small, genuine
employers often have none — it is recorded as "missing" instead.

STATUS: not connected yet. Glassdoor and AmbitionBox do not offer a free
public API and restrict automated scraping, so how to collect this signal is
waiting for the team's decision. Until then this check returns search links.
"""

from app.checks.links import google_search
from app.schemas import CheckResult, ExtractedInfo

KEY = "reviews"
TITLE = "Employee Reviews (Glassdoor / AmbitionBox)"


def run(info: ExtractedInfo, text: str) -> CheckResult:
    company = info.company_name
    if not company:
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="skipped",
            summary="No company name was found, so reviews could not be looked up.",
        )

    return CheckResult(
        key=KEY,
        title=TITLE,
        status="not_configured",
        summary="Automatic review lookup is not connected yet. Use the links below to read employee reviews.",
        manual_links=[
            google_search(f"'{company}' on AmbitionBox", f'site:ambitionbox.com "{company}" reviews'),
            google_search(f"'{company}' on Glassdoor", f'site:glassdoor.co.in OR site:glassdoor.com "{company}" reviews'),
        ],
    )
