"""
red_flags.py — Signal family 5: Hiring-process red flags (rule engine).

These are warning signs about HOW the hiring is done, not how well the text
is written — so an AI-polished scam posting still trips them:

  upfront_payment         asks for a registration fee / security deposit
  offplatform_contact     pushes the chat to WhatsApp / Telegram
  no_interview            "no interview", "direct joining", "100% job guarantee"
  sensitive_info_request  asks for Aadhaar / PAN / bank details / OTP up front
  free_email              recruiter writes from gmail.com, yahoo.com ...
  salary_too_high         salary far above normal for the experience asked

Negation handling: genuine companies often write warnings like "We NEVER
charge a registration fee". Before counting a match we look at the words
just before it (in the same sentence) and skip it if they contain a
negation such as "no", "never", "not" or "without".
"""

import math
import re
from dataclasses import dataclass

from app.schemas import CheckResult, ExtractedInfo, Signal
from app.services.feature_extractor import FREE_EMAIL_DOMAINS

KEY = "red_flags"
TITLE = "Hiring Process Red Flags"


# ------------------------------------------------------------------
# Rules: each rule = one feature + the phrases that trigger it
# ------------------------------------------------------------------
@dataclass
class Rule:
    feature: str
    patterns: list[str]
    message: str  # "{match}" is replaced with the phrase we found


RULES = [
    Rule(
        feature="upfront_payment",
        patterns=[
            r"registration\s+(?:fee|fees|charges?|amount)",
            r"security\s+(?:deposit|amount|money)",
            r"refundable\s+(?:fee|deposit|amount)",
            r"(?:training|joining|processing|kit|verification|interview|documentation|onboarding|"
            r"id\s*card|laptop|uniform)\s+(?:fee|fees|charges?)",
            r"pay\s+(?:a|an|the)?\s*(?:small|nominal|one[\s-]time|minimal)?\s*(?:fee|amount|charges?|deposit)",
            r"(?:deposit|fee)\s+of\s+(?:₹|rs\.?|inr)\s*\d",
        ],
        message='Asks the candidate to pay money ("{match}"). Genuine employers never charge you to get a job.',
    ),
    Rule(
        feature="offplatform_contact",
        patterns=[r"whats\s*app", r"telegram", r"\bt\.me/", r"\bwa\.me/", r"signal\s+app"],
        message='Moves the conversation to a chat app ("{match}") instead of a formal application process.',
    ),
    Rule(
        feature="no_interview",
        patterns=[
            r"no\s+interview",
            r"without\s+(?:any\s+)?interview",
            r"(?:direct|instant|spot)\s+(?:joining|selection|hiring|offer)",
            r"(?:offer|joining|appointment)\s+letter\s+(?:within|in)\s+\d+\s*(?:hours?|hrs?|minutes?|mins?)",
            r"100\s*%\s*(?:job\s+)?(?:guarantee|guaranteed|placement)",
            r"guaranteed\s+(?:job|selection|placement)",
        ],
        message='Promises a job without a normal selection process ("{match}").',
    ),
    Rule(
        feature="sensitive_info_request",
        patterns=[
            r"aadh?aa?r",
            r"\bpan\s*(?:card|number|no\b)",
            r"bank\s+(?:account|details|a/c|statement|passbook)",
            r"\botp\b",
            r"\b(?:atm|upi)\s*pin\b",
            r"(?:debit|credit)\s+card\s+(?:number|details)",
            r"\bcvv\b",
        ],
        message='Asks for sensitive personal or financial details up front ("{match}").',
    ),
]

# Words that cancel a match when they appear just before it in the same sentence.
NEGATION_RE = re.compile(
    r"\b(?:no|never|not|without|zero|nil|don'?t|doesn'?t|won'?t|free\s+of)\b", re.IGNORECASE
)
SENTENCE_BREAK_RE = re.compile(r"[.!?\n]")


# ------------------------------------------------------------------
# Salary reference table (rupees per month, by years of experience)
# ------------------------------------------------------------------
# PLACEHOLDER VALUES for the prototype: rough upper-typical monthly salaries
# in India. Replace with figures from a cited source (e.g. AmbitionBox or
# Naukri salary reports) before the evaluation phase, and cite it in the report.
SALARY_REFERENCE = [
    # (min years, max years, reference ₹ per month)
    (0, 1, 50_000),  # freshers  (~6 LPA)
    (1, 3, 85_000),  # (~10 LPA)
    (3, 6, 150_000),  # (~18 LPA)
    (6, 99, 250_000),  # (~30 LPA)
]
# Only flag salaries at least this many times the reference ("wide margin",
# research paper Section IV-E), because the reference data is approximate.
SALARY_FLAG_RATIO = 1.5


def reference_salary(experience_years: float | None) -> int:
    """
    Reference monthly salary for the experience asked for.
    If the posting does not say, we assume an entry-level role, because
    TrustHire's users are mainly students and freshers.
    """
    years = experience_years or 0
    for low, high, salary in SALARY_REFERENCE:
        if low <= years < high:
            return salary
    return SALARY_REFERENCE[-1][2]


# ------------------------------------------------------------------
# Main function
# ------------------------------------------------------------------
def run(info: ExtractedInfo, text: str) -> CheckResult:
    signals: list[Signal] = []

    # 1. Phrase rules (payment, WhatsApp, no interview, Aadhaar ...)
    for rule in RULES:
        phrase = find_phrase(text, rule.patterns)
        if phrase:
            signals.append(Signal(feature=rule.feature, value=1.0, message=rule.message.format(match=phrase)))

    # 2. Free e-mail provider (only if NO company e-mail is given)
    free_emails = [e for e in info.emails if e.split("@")[-1].lower() in FREE_EMAIL_DOMAINS]
    if info.emails and len(free_emails) == len(info.emails):
        signals.append(Signal(
            feature="free_email",
            value=1.0,
            message=f"The recruiter's e-mail ({free_emails[0]}) uses a free provider instead of a company domain.",
        ))

    # 3. Salary far above normal for the experience asked
    details = {}
    if info.salary_monthly_inr:
        reference = reference_salary(info.experience_min_years)
        ratio = info.salary_monthly_inr / reference
        details = {"salary_monthly_inr": info.salary_monthly_inr, "reference_monthly_inr": reference, "ratio": round(ratio, 2)}
        if ratio >= SALARY_FLAG_RATIO:
            signals.append(Signal(
                feature="salary_too_high",
                # log2: every doubling above the reference adds 1 (keeps huge numbers from dominating)
                value=round(math.log2(ratio), 3),
                message=(
                    f"The salary (about ₹{info.salary_monthly_inr:,.0f}/month) is {ratio:.1f}x the typical "
                    f"₹{reference:,}/month for this experience level."
                ),
            ))

    count = len(signals)
    summary = f"{count} warning sign{'s' if count != 1 else ''} found in the hiring process." if count else (
        "No hiring-process warning signs were found."
    )
    return CheckResult(key=KEY, title=TITLE, status="completed", summary=summary, signals=signals, details=details)


def find_phrase(text: str, patterns: list[str]) -> str | None:
    """Return the first non-negated phrase matching any pattern, or None."""
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if not _is_negated(text, match.start()):
                return match.group(0)
    return None


def _is_negated(text: str, position: int) -> bool:
    """True if a negation word appears shortly before `position` in the same sentence."""
    window = text[max(0, position - 40) : position]
    sentence_breaks = list(SENTENCE_BREAK_RE.finditer(window))
    if sentence_breaks:
        window = window[sentence_breaks[-1].end() :]  # keep only the current sentence
    return bool(NEGATION_RE.search(window))
