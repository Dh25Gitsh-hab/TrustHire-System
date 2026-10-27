"""
domain_check.py — Signal family 1: Domain age (WHOIS).

Idea: real companies usually have websites that are years old. Scam
"companies" often register a brand-new domain just for the scam. A WHOIS
lookup tells us when the domain was first registered. (python-whois talks to
the public WHOIS servers directly — no account or API key is needed.)

Signals produced (their weights live in app/scoring/weights.py):
  domain_age           log(1 + age in days) - log(1 + 365)
                       -> below 0 for domains younger than 1 year, above 0 for older
                       (the log means day 10 vs day 40 matters far more than
                        year 8 vs year 9 — research paper, Section IV-A)
  domain_age_hidden    1 when WHOIS gives no registration date (privacy / missing)
  domain_unregistered  1 when the domain does not exist at all
  age_claim_mismatch   1 when the posting claims 3+ years in business
                       but the domain is less than a year old
"""

import math
from datetime import datetime, timezone

import whois
from whois.exceptions import WhoisDomainNotFoundError

from app.config import HTTP_TIMEOUT_SECONDS
from app.schemas import CheckResult, ExtractedInfo, ManualLink, Signal

KEY = "domain_age"
TITLE = "Domain Age (WHOIS)"

# Reference point: a domain exactly one year old contributes 0 to the score.
ONE_YEAR_REFERENCE = math.log(1 + 365)


def lookup_whois(domain: str) -> dict:
    """Ask the WHOIS servers about `domain`. Kept separate so tests can replace it."""
    return whois.whois(domain, timeout=int(HTTP_TIMEOUT_SECONDS))


def run(info: ExtractedInfo, text: str) -> CheckResult:
    domain = info.website_domain
    if not domain:
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="skipped",
            summary="No company website or company e-mail domain was found, so domain age could not be checked.",
        )

    links = [ManualLink(label=f"ICANN WHOIS lookup for {domain}", url=f"https://lookup.icann.org/en/lookup?name={domain}")]

    # --- 1. Ask WHOIS ---------------------------------------------------
    try:
        record = lookup_whois(domain)
    except WhoisDomainNotFoundError:
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="completed",
            summary=f"{domain} does not appear to be a registered domain.",
            signals=[Signal(
                feature="domain_unregistered",
                value=1.0,
                message=f"The website {domain} given in the posting does not appear to be registered at all.",
            )],
            details={"domain": domain},
            manual_links=links,
        )
    except Exception as error:  # network problems, unsupported TLD, rate limits ...
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="error",
            summary=f"The WHOIS lookup for {domain} failed ({type(error).__name__}). Use the link to check manually.",
            details={"domain": domain},
            manual_links=links,
        )

    # --- 2. Read the registration date ----------------------------------
    created = _earliest_date(record.get("creation_date"))
    details = {
        "domain": domain,
        "domain_source": info.domain_source,
        "registrar": record.get("registrar"),
        "creation_date": created.date().isoformat() if created else None,
        "expiration_date": _iso(_earliest_date(record.get("expiration_date"))),
    }

    if created is None:
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="completed",
            summary=f"WHOIS does not show when {domain} was registered.",
            signals=[Signal(
                feature="domain_age_hidden",
                value=1.0,
                message=f"The WHOIS record for {domain} hides or lacks its registration date, so its age could not be confirmed.",
            )],
            details=details,
            manual_links=links,
        )

    # --- 3. Turn the age into signals -----------------------------------
    age_days = max(0, (datetime.now(timezone.utc).replace(tzinfo=None) - created).days)
    age_text = describe_age(age_days)
    details["age_days"] = age_days

    age_message = f"The website domain {domain} was registered {age_text} ago (on {details['creation_date']})."
    if age_days < 180:
        age_message += " Very new domains are common in job scams."

    signals = [Signal(
        feature="domain_age",
        value=round(math.log(1 + age_days) - ONE_YEAR_REFERENCE, 3),
        message=age_message,
    )]

    claimed = info.claimed_years_in_business
    if claimed and claimed >= 3 and age_days < 365:
        signals.append(Signal(
            feature="age_claim_mismatch",
            value=1.0,
            message=f"The posting claims about {claimed} years in business, but its website is only {age_text} old.",
        ))

    return CheckResult(
        key=KEY,
        title=TITLE,
        status="completed",
        summary=f"{domain} was registered {age_text} ago.",
        signals=signals,
        details=details,
        manual_links=links,
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _earliest_date(value) -> datetime | None:
    """
    WHOIS dates come back in different shapes: one datetime, a list of
    datetimes, or nothing. Return the earliest one as a plain UTC datetime.
    """
    values = value if isinstance(value, list) else [value]
    dates = []
    for item in values:
        if isinstance(item, datetime):
            if item.tzinfo is not None:
                item = item.astimezone(timezone.utc).replace(tzinfo=None)
            dates.append(item)
    return min(dates) if dates else None


def _iso(value: datetime | None) -> str | None:
    return value.date().isoformat() if value else None


def describe_age(days: int) -> str:
    """12 -> '12 days', 200 -> '6 months', 2200 -> '6.0 years'."""
    if days < 60:
        return f"{days} day" + ("" if days == 1 else "s")
    if days < 730:
        return f"{days // 30} months"
    return f"{days / 365:.1f} years"
