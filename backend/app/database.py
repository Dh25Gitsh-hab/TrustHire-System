"""
database.py — saves results in Supabase (a hosted PostgreSQL database).

Tables (created by backend/supabase/schema.sql):
  analyses      one row per analysed posting: score, level, the model's
                input features and the reasons. features["evidence"] holds a
                short summary of the web evidence (website names + labels).
                For privacy we do NOT store the posting text, the recruiter's
                e-mails / phone numbers, or full links to web pages.
  scam_reports  user feedback ("scam" / "genuine") on an analysis — these
                become training labels for the ML phase.

The backend uses Supabase's publishable key, and the database rules allow
that key to INSERT rows only (it cannot read them back). That is why we
create each row's id here with uuid4() instead of asking the database for it.

Saving is optional and never breaks an analysis: if Supabase is not
configured or is unreachable, we log a warning and carry on.
"""

import logging
import uuid

from postgrest.types import ReturnMethod
from supabase import Client, create_client

from app import config
from app.schemas import AnalyzeResponse, ReportRequest

logger = logging.getLogger("trusthire.database")

_client: Client | None = None  # created once, on first use


def is_configured() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_KEY)


def get_client() -> Client | None:
    """Return the Supabase client, or None if the keys are not set."""
    global _client
    if _client is None and is_configured():
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


def save_analysis(response: AnalyzeResponse, job_url: str | None) -> str | None:
    """Store one analysis. Returns its id, or None if it was not saved."""
    client = get_client()
    if client is None:
        return None

    analysis_id = str(uuid.uuid4())
    row = {
        "id": analysis_id,
        "job_url": job_url,
        "company_name": response.extracted.company_name,
        "website_domain": response.extracted.website_domain,
        "trust_score": response.trust_score,
        "trust_level": response.trust_level,
        # The numbers the model saw — together with user reports, this is future training data.
        "features": {
            signal.feature: signal.value
            for check in response.checks
            if check.status == "completed"
            for signal in check.signals
        },
        "reasons": [reason.model_dump() for reason in response.reasons],
    }
    evidence = response.evidence_analysis
    if evidence is not None:
        # Web-evidence summary, kept inside the existing "features" column (no
        # schema change). It is NOT a model input. Only website names are kept,
        # not full links — a link such as linkedin.com/in/<name> can identify a person.
        row["features"]["evidence"] = {
            "status": evidence.status,
            "ai_risk_score": evidence.risk_score,
            "ai_risk_level": evidence.risk_level,
            "model": evidence.model,
            "sources": [
                {"domain": item.source_domain, "category": item.category,
                 "signal": item.signal, "verification": item.verification}
                for item in evidence.evidence
            ],
        }
    try:
        client.table("analyses").insert(row, returning=ReturnMethod.minimal).execute()
        return analysis_id
    except Exception as error:
        logger.warning("Could not save analysis to Supabase (%s)", type(error).__name__)
        return None


def save_report(report: ReportRequest) -> bool:
    """Store a user's "scam" / "genuine" report. Returns True if it was saved."""
    client = get_client()
    if client is None:
        return False

    row = {
        "analysis_id": str(report.analysis_id),
        "user_verdict": report.user_verdict,
        "comment": report.comment,
    }
    try:
        client.table("scam_reports").insert(row, returning=ReturnMethod.minimal).execute()
        return True
    except Exception as error:
        logger.warning("Could not save report to Supabase (%s)", type(error).__name__)
        return False
