"""
registry_check.py — Signal family 4: Company registration (MCA, India).

Data source: data.gov.in — "Registrars of Companies (RoC)-wise Company
Master Data", the Ministry of Corporate Affairs' public list of ~3.7 million
registered companies (CIN, name, status, registration date, address ...).

API quirk we must handle: the CompanyName filter is EXACT and CASE-SENSITIVE.
"INFOSYS LIMITED" is found, but "Infosys Limited" or "INFOSYS" are not.
Names are stored in capitals with their full legal ending, so we:
  1. convert the name to MCA style: capitals, "Pvt. Ltd." -> "PRIVATE LIMITED",
     "Ltd" -> "LIMITED";
  2. if it has no legal ending, try "<NAME> PRIVATE LIMITED", then "<NAME> LIMITED".

Signals produced:
  registry_match      1 when a registered company with that exact name exists
  incorporation_age   log(1 + days since registration) - log(1 + 365),
                      same idea as domain age
  registry_inactive   1 when found but its status is not "Active"
                      (e.g. Strike Off, Dormant, Under Liquidation)
  registry_not_found  1 when there is no exact match. A WEAK signal: the posting
                      may write the name differently, and sole proprietors,
                      LLPs and foreign firms are not in this list.

A match is "necessary but not sufficient" (research paper, Section IV-D):
a fraudster can copy the name of a real, registered company.
"""

import math
import re
from datetime import date

import requests

from app import config
from app.checks.links import google_search
from app.schemas import CheckResult, ExtractedInfo, ManualLink, Signal

KEY = "registry"
TITLE = "Company Registration (MCA)"

DATAGOVIN_URL = "https://api.data.gov.in/resource/{resource_id}"
MCA_MASTER_DATA_URL = "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html"

# Spelling fixes to turn a name into MCA style (applied in this order).
LEGAL_ENDING_FIXES = [
    (r"\bPVT\.?\s*LTD\b\.?", "PRIVATE LIMITED"),
    (r"\bPRIVATE\s+LTD\b\.?", "PRIVATE LIMITED"),
    (r"\bPVT\.?\s+LIMITED\b", "PRIVATE LIMITED"),
    (r"\bLTD\b\.?", "LIMITED"),
]


def run(info: ExtractedInfo, text: str) -> CheckResult:
    company = info.company_name
    if not company:
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="skipped",
            summary="No company name was found, so registration could not be checked.",
        )

    links = [
        ManualLink(label="MCA Master Data search (enter the company name)", url=MCA_MASTER_DATA_URL),
        google_search(f"Find the CIN of '{company}'", f'"{company}" CIN company registration India'),
    ]

    if not config.DATAGOVIN_API_KEY:
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="not_configured",
            summary="Automatic MCA lookup is not connected. Use the links below to check registration yourself.",
            manual_links=links,
        )

    # --- 1. Look the name up, trying each MCA-style spelling ---------------
    tried = mca_name_variants(company)
    try:
        record = None
        for name in tried:
            records = fetch_mca_records(name)
            if records:
                record = records[0]
                break
    except Exception as error:  # network problem, bad key, rate limit ...
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="error",
            summary=f"The MCA lookup failed ({type(error).__name__}). Use the links below to check manually.",
            manual_links=links,
        )

    # --- 2. Not found -------------------------------------------------------
    if record is None:
        return CheckResult(
            key=KEY,
            title=TITLE,
            status="completed",
            summary=f"No company named exactly '{tried[0]}' was found in MCA records.",
            signals=[Signal(
                feature="registry_not_found",
                value=1.0,
                message=(
                    f"No registered company named exactly '{tried[0]}' was found in MCA records. "
                    "The name may be written differently, so check the CIN yourself."
                ),
            )],
            details={"names_tried": tried},
            manual_links=links,
        )

    # --- 3. Found: turn the record into signals ----------------------------
    registered_name = record.get("CompanyName", "")
    status = record.get("CompanyStatus") or "Unknown"
    registered_on = _parse_date(record.get("CompanyRegistrationdate_date"))

    details = {
        "registered_name": registered_name,
        "cin": record.get("CIN"),
        "status": status,
        "registration_date": registered_on.isoformat() if registered_on else None,
        "company_class": record.get("CompanyClass"),
        "state": record.get("CompanyStateCode"),
        "roc": record.get("CompanyROCcode"),
    }

    match_message = f"Registered with MCA as {registered_name} (CIN {details['cin']})"
    if registered_on:
        match_message += f", incorporated on {registered_on.isoformat()}"
    signals = [Signal(feature="registry_match", value=1.0, message=match_message + ".")]

    if registered_on:
        age_days = max(0, (date.today() - registered_on).days)
        signals.append(Signal(
            feature="incorporation_age",
            value=round(math.log(1 + age_days) - math.log(1 + 365), 3),
            message=f"The company was incorporated {age_days // 365} year(s) ago ({registered_on.isoformat()}).",
        ))

    if not status.lower().startswith("active"):
        signals.append(Signal(
            feature="registry_inactive",
            value=1.0,
            message=f"The registered company's status is '{status}', not Active.",
        ))

    return CheckResult(
        key=KEY,
        title=TITLE,
        status="completed",
        summary=f"Found in MCA records: {registered_name} — status {status}.",
        signals=signals,
        details=details,
        manual_links=links,
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def fetch_mca_records(company_name: str) -> list[dict]:
    """One exact-name search on data.gov.in. Kept separate so tests can replace it."""
    response = requests.get(
        DATAGOVIN_URL.format(resource_id=config.MCA_RESOURCE_ID),
        params={
            "api-key": config.DATAGOVIN_API_KEY,
            "format": "json",
            "limit": 5,
            f"filters[{config.MCA_NAME_FIELD}]": company_name,
        },
        headers={"User-Agent": config.USER_AGENT},  # data.gov.in stalls the default python-requests name
        timeout=config.HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json().get("records") or []


def mca_name_variants(name: str) -> list[str]:
    """
    'Acme Analytics Pvt. Ltd.' -> ['ACME ANALYTICS PRIVATE LIMITED']
    'Acme Analytics'           -> ['ACME ANALYTICS PRIVATE LIMITED', 'ACME ANALYTICS LIMITED']
    """
    upper = " ".join(name.upper().split())
    for pattern, replacement in LEGAL_ENDING_FIXES:
        upper = re.sub(pattern, replacement, upper)
    upper = " ".join(upper.split()).rstrip(" .,")

    if upper.endswith("LIMITED"):
        return [upper]
    return [f"{upper} PRIVATE LIMITED", f"{upper} LIMITED"]


def _parse_date(value: str | None) -> date | None:
    """'2025-08-26' -> date(2025, 8, 26); anything else -> None."""
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None
