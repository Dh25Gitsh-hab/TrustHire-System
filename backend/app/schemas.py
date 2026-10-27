"""
schemas.py — the shapes of data going IN and OUT of the API.

FastAPI uses these Pydantic models to:
  * validate the JSON the frontend sends us (AnalyzeRequest),
  * describe the JSON we send back (AnalyzeResponse),
  * build the interactive API docs at http://localhost:8000/docs.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.config import MAX_JOB_TEXT_CHARS

# A short scam-style posting used as the pre-filled example in /docs.
EXAMPLE_JOB_TEXT = (
    "Urgent hiring! Data Entry Executive (Work From Home) at Brightpath Global Solutions.\n"
    "Freshers can apply. Earn Rs. 3,000 per day. No interview — direct joining.\n"
    "Pay a refundable registration fee of Rs. 999 to confirm your seat.\n"
    "Send your Aadhaar and PAN card on WhatsApp: +91 98765 43210\n"
    "Email: brightpath.hr.jobs@gmail.com"
)


# ------------------------------------------------------------------
# REQUEST: what the frontend sends
# ------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    """A job posting to analyse. Either the text, the URL, or both."""

    job_text: str | None = Field(
        default=None,
        max_length=MAX_JOB_TEXT_CHARS,
        description="The job description pasted by the user.",
    )
    job_url: str | None = Field(
        default=None,
        max_length=2_000,
        description="Link to the job posting. We try to download and read it.",
    )
    # Optional hints. If the user already knows these, they are more
    # reliable than anything we can guess from the text.
    company_name: str | None = Field(default=None, max_length=200)
    company_website: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_text_or_url(self):
        """At least one of job_text / job_url must be filled in."""
        has_text = bool(self.job_text and self.job_text.strip())
        has_url = bool(self.job_url and self.job_url.strip())
        if not (has_text or has_url):
            raise ValueError("Please provide the job description text or a link to the posting.")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [{"job_text": EXAMPLE_JOB_TEXT}],
        }
    }


# ------------------------------------------------------------------
# Building blocks used inside the response
# ------------------------------------------------------------------
class ManualLink(BaseModel):
    """A link the user can open to verify something by hand."""

    label: str
    url: str


class Signal(BaseModel):
    """
    One piece of evidence produced by a check.

    `feature` is the name the scoring model knows (e.g. "domain_age"),
    `value` is the number fed into the model, and `message` is the
    plain-language sentence shown to the user.
    """

    feature: str
    value: float
    message: str


class CheckResult(BaseModel):
    """The outcome of one verification module (domain, reputation, ...)."""

    key: str  # short id, e.g. "domain_age"
    title: str  # human title, e.g. "Domain Age (WHOIS)"
    status: Literal["completed", "skipped", "not_configured", "error"]
    summary: str  # one-line result shown on the card
    signals: list[Signal] = []
    details: dict = {}  # raw facts (registrar, dates, ...) for the curious user
    manual_links: list[ManualLink] = []


class Reason(BaseModel):
    """One line of the explanation: what moved the trust score and by how much."""

    feature: str
    message: str
    impact: float  # weight x value, in model units (+ raises trust, - lowers it)
    effect: Literal["raises_trust", "lowers_trust"]


class ExtractedInfo(BaseModel):
    """What we managed to pull out of the posting."""

    company_name: str | None = None
    website_domain: str | None = None
    domain_source: str | None = None  # where the domain came from
    emails: list[str] = []
    phone_numbers: list[str] = []
    salary_text: str | None = None
    salary_monthly_inr: float | None = None
    experience_min_years: float | None = None
    claimed_years_in_business: int | None = None


class EvidenceItem(BaseModel):
    """
    One web search result about the company, with the AI's label.
    title / url / snippet always come from the search engine, never from the AI.
    """

    title: str
    url: str
    source_domain: str  # e.g. "reddit.com"
    snippet: str = ""
    date: str | None = None
    relevance: str = ""  # the AI's one-line note: why this result matters
    category: Literal[
        "official",  # the company's own site, or a government / registry record
        "scam_report",  # someone says THIS company is a scam
        "impersonation_warning",  # scammers are pretending to be this company
        "neutral_info",  # news, profiles, reviews without fraud claims
        "not_analysed",  # the AI was unavailable, so nobody has sorted it
    ]
    signal: Literal["suspicious", "reassuring", "neutral"]
    verification: Literal[
        "verified_fact",  # stated by an official / authoritative source
        "allegation",  # someone claims it — NOT proven
        "weak_signal",  # hints only
        "unknown",
    ]


class EvidenceAnalysis(BaseModel):
    """
    The online-reputation evidence: web search (SerpApi) + AI reading (Gemini).

    risk_score is the AI's judgement of the SEARCH EVIDENCE only, 0-100 where
    HIGHER = MORE CONCERNING (the opposite direction of trust_score). It is not
    a calibrated probability, and it does NOT change trust_score.
    """

    status: Literal[
        "completed",  # searched and analysed by the AI
        "partial",  # searched, but the AI analysis is unavailable
        "unavailable",  # the web search failed (quota used up, timeout ...)
        "not_configured",  # no SerpApi key on the server
        "skipped",  # nothing to search for (no company name or website)
    ]
    message: str  # one sentence for the user about what worked
    risk_score: int | None = None  # None when there was nothing to analyse or no AI
    risk_level: Literal["Low", "Medium", "High"] | None = None
    summary: str = ""
    risk_signals: list[str] = []
    reassuring_signals: list[str] = []
    evidence: list[EvidenceItem] = []
    limitations: list[str] = []  # what this analysis could NOT see or check
    searches_run: list[str] = []  # the search queries used (transparency)
    model: str | None = None  # the Gemini model that wrote the analysis


# ------------------------------------------------------------------
# RESPONSE: what the frontend receives
# ------------------------------------------------------------------
class AnalyzeResponse(BaseModel):
    trust_score: int  # 1-99, higher = MORE trustworthy (it is a trust score, not a risk score)
    trust_level: Literal["high", "medium", "low"]
    verdict: str  # one-sentence advice
    reasons: list[Reason]  # sorted, strongest first
    checks: list[CheckResult]  # one card per verification module
    checks_completed: int
    checks_total: int
    extracted: ExtractedInfo
    disclaimer: str
    analysis_id: str | None = None  # set when the result was saved in the database
    evidence_analysis: EvidenceAnalysis | None = None  # web search + AI details (see above)


# ------------------------------------------------------------------
# User feedback: "this posting was a scam / was genuine"
# ------------------------------------------------------------------
class ReportRequest(BaseModel):
    analysis_id: UUID  # the id returned by /api/analyze
    user_verdict: Literal["scam", "genuine"]
    comment: str | None = Field(default=None, max_length=1_000)
