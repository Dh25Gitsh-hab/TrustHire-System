"""
reputation_check.py — Signal family 2: Online reputation (web search + AI).

Idea (research paper, Section IV-B): people who were cheated often write
about it online (Reddit, complaint sites, news) before any official action.

How it works:
  1. web_search (SerpApi) runs a few Google searches about the company and
     its website — including Reddit and LinkedIn pages that Google has
     indexed publicly. We never log in to, or scrape, Reddit or LinkedIn.
  2. evidence_analyzer (Gemini) labels each result: official source, scam
     report about THIS company, impersonation warning, or neutral information.
  3. ONE number goes into the trust score (weight in scoring/weights.py):

        web_scam_reports = min(independent websites with scam reports
                               about this company, 3) / 3          -> 0 .. 1

     * "independent" = different domains, and not the company's own site.
       Reddit counts once however many threads it has.
     * capped at 3, so one viral story cannot dominate the score.
     * impersonation warnings do NOT count — they mean scammers copy the
       company, not that the company is a scam.
     Gemini's own risk score is shown to the user but NEVER changes trust_score.

If a service is missing or fails, nothing is guessed: the card says what was
unavailable and the signal is left out ("unknown" is not the same as "0 reports").
"""

import re

from app.checks.links import google_search, reddit_search
from app.schemas import CheckResult, EvidenceAnalysis, EvidenceItem, ExtractedInfo, Signal
from app.services import evidence_analyzer, gemini_client, web_search
from app.services.gemini_client import GeminiError
from app.services.web_search import SearchError, SearchResult

KEY = "reputation"
TITLE = "Online Reputation (Web Search + AI)"

MIN_NAME_LENGTH = 4  # "ABC" would match thousands of unrelated pages
MAX_REPORT_SITES = 3  # cap for web_scam_reports
MAX_UNSORTED_RESULTS = 10  # results listed when the AI is unavailable

# Legal endings removed before searching ("Acme Pvt. Ltd." is discussed online as "Acme").
LEGAL_ENDING_RE = re.compile(
    r"[\s,]+(?:pvt\.?\s*ltd\.?|private\s+limited|limited|ltd\.?|llp|inc\.?|corp\.?)$", re.IGNORECASE
)

SEARCH_LIMITATION = (
    "Only the top Google results that are publicly indexed were checked — not every post, "
    "review or private group."
)
AI_LIMITATION = (
    "The labels and summary were written by an AI (Gemini) from short search snippets and can be wrong. "
    "Reports are unverified allegations unless marked as verified — open the sources to check."
)
NOTHING_FOUND_LIMITATION = (
    "Finding nothing is not evidence of fraud: small or new genuine companies often have little online presence."
)


def run(info: ExtractedInfo, text: str) -> CheckResult:
    company = search_name(info.company_name) if info.company_name else None
    if company and len(company) < MIN_NAME_LENGTH:
        company = None  # too short to search reliably
    domain = info.website_domain
    name = company or domain  # what we call the company in messages

    if not name:
        return _card("skipped", "No company name or website was found, so there is nothing to search for.",
                     EvidenceAnalysis(status="skipped", message="Nothing to search for."))

    links = _manual_links(name)

    if not web_search.is_configured():
        return _card("not_configured",
                     "Automatic web search is not connected. Use the links below to look for scam reports.",
                     EvidenceAnalysis(status="not_configured", message="Web search is not connected on this server."),
                     links=links)

    # --- 1. Search the web ------------------------------------------------
    queries = web_search.build_queries(company, domain)
    try:
        results, search_notes = web_search.search_many(queries)
    except SearchError as error:
        return _card("error", f"The web search did not work ({error}). Use the links below to search yourself.",
                     EvidenceAnalysis(status="unavailable", message=f"Web search unavailable: {error}.",
                                      searches_run=queries),
                     links=links)

    limitations = [SEARCH_LIMITATION, *search_notes]
    details = {"results_found": len(results)}

    if not results:
        evidence = EvidenceAnalysis(
            status="completed",
            message="The web search worked but found no public results.",
            summary=f"No public web results were found about {name}.",
            limitations=[*limitations, NOTHING_FOUND_LIMITATION],
            searches_run=queries,
        )
        return _card("completed", f"No public web results were found about {name}.", evidence,
                     links=links, signals=[_report_signal(0, name)], details=details)

    # --- 2. Let the AI label the results -----------------------------------
    if not gemini_client.is_configured():
        return _card("not_configured",
                     f"{len(results)} web results were found, but the AI analysis is not connected. "
                     "Read the sources yourself.",
                     _unsorted(results, queries, limitations, "AI analysis is not connected on this server."),
                     links=links, details=details)
    try:
        evidence = evidence_analyzer.analyze(company, domain, info.claimed_years_in_business, results)
    except GeminiError as error:
        return _card("error",
                     f"{len(results)} web results were found, but the AI analysis failed ({error}). "
                     "Read the sources yourself.",
                     _unsorted(results, queries, limitations, f"AI analysis unavailable: {error}."),
                     links=links, details=details)

    evidence.searches_run = queries
    evidence.limitations = [*limitations, AI_LIMITATION, *evidence.limitations]

    # --- 3. The one number for the trust score ------------------------------
    sites = count_report_sites(evidence.evidence, domain)
    details.update({"report_sites": sites, "ai_risk_score": evidence.risk_score})
    return _card(
        "completed",
        f"{len(results)} web results checked: {sites} independent site{'' if sites == 1 else 's'} "
        f"with scam reports about {name}.",
        evidence,
        links=links,
        signals=[_report_signal(sites, name)],
        details=details,
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def search_name(company_name: str) -> str:
    """'Acme Analytics Pvt. Ltd.' -> 'Acme Analytics' (how people write it online)."""
    return LEGAL_ENDING_RE.sub("", company_name.strip()).strip() or company_name


def count_report_sites(evidence: list[EvidenceItem], company_domain: str | None) -> int:
    """Independent websites (different domains, not the company's own) with scam reports about it."""
    return len({
        item.source_domain
        for item in evidence
        if item.category == "scam_report" and item.signal == "suspicious" and item.source_domain != company_domain
    })


def _report_signal(sites: int, name: str) -> Signal:
    value = round(min(sites, MAX_REPORT_SITES) / MAX_REPORT_SITES, 3)
    if sites == 0:
        message = f"No web search results report {name} itself as a scam."
    else:
        message = (f"{sites} independent website{'' if sites == 1 else 's'} carry reports that {name} is a scam "
                   "(unverified allegations — open the sources to check).")
    return Signal(feature="web_scam_reports", value=value, message=message)


def _unsorted(results: list[SearchResult], queries: list[str], limitations: list[str], message: str) -> EvidenceAnalysis:
    """Search worked but the AI did not: list the raw results, clearly marked as not analysed."""
    return EvidenceAnalysis(
        status="partial",
        message=message,
        evidence=[
            EvidenceItem(title=r.title, url=r.url, source_domain=r.domain, snippet=r.snippet, date=r.date,
                         category="not_analysed", signal="neutral", verification="unknown")
            for r in results[:MAX_UNSORTED_RESULTS]
        ],
        limitations=[*limitations, "These results were not analysed, so they add nothing to the trust score."],
        searches_run=queries,
    )


def _manual_links(name: str):
    return [
        google_search(f"Search Google for '{name}' complaints", f'"{name}" scam OR fraud OR fake job'),
        reddit_search(f"Search Reddit for '{name}'", f'"{name}" scam OR fraud OR fake'),
        google_search(f"Find '{name}' on LinkedIn", f'site:linkedin.com/company "{name}"'),
    ]


def _card(status, summary, evidence: EvidenceAnalysis, links=(), signals=(), details=None) -> CheckResult:
    """
    Build the reputation card. The full evidence analysis rides along in
    details["evidence_analysis"]; analyzer.py moves it to the top-level
    `evidence_analysis` field of the response.
    """
    return CheckResult(
        key=KEY,
        title=TITLE,
        status=status,
        summary=summary,
        signals=list(signals),
        details={**(details or {}), "evidence_analysis": evidence},
        manual_links=list(links),
    )
