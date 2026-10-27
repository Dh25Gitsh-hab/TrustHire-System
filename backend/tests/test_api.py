"""
End-to-end tests of the API. WHOIS is replaced by a fake function, so these
tests never touch the internet and always give the same result.
"""

from datetime import datetime, timedelta, timezone

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.checks import domain_check
from app.main import app
from app.schemas import EXAMPLE_JOB_TEXT
from app.services.posting_fetcher import PostingFetchError, _read_job_posting_json, fetch_posting
from tests.fakes import ai_answer, enable_ai, enable_search, gemini_reply, label, serp_reply, serp_result

client = TestClient(app)


@pytest.fixture
def fake_whois(monkeypatch):
    """Pretend every domain was registered `days_old` days ago."""

    def install(days_old: int):
        created = datetime.now(timezone.utc) - timedelta(days=days_old)  # WHOIS dates are UTC
        monkeypatch.setattr(domain_check, "lookup_whois", lambda domain: {"creation_date": created, "registrar": "Test"})

    return install


def test_health():
    assert client.get("/api/health").json() == {
        "status": "ok",
        "database": "not configured",
        "web_search": "not configured",
        "ai_analysis": "not configured",
    }


def test_without_search_keys_evidence_is_marked_not_configured():
    body = client.post("/api/analyze", json={"job_text": EXAMPLE_JOB_TEXT}).json()
    assert body["evidence_analysis"]["status"] == "not_configured"
    reputation_card = next(check for check in body["checks"] if check["key"] == "reputation")
    assert "evidence_analysis" not in reputation_card["details"]  # moved to its own field


def test_web_scam_reports_lower_trust_by_their_weight(monkeypatch, fake_whois):
    """End to end: 3 independent report sites -> exactly one extra reason of -1.2."""
    fake_whois(days_old=10 * 365)
    text = "Acme Analytics is hiring a Data Analyst in Pune. Apply at https://careers.acme-analytics.in/jobs/42"
    before = client.post("/api/analyze", json={"job_text": text}).json()

    sites = ["reddit.com", "complaints.in", "consumercourt.net"]
    reply = serp_reply(*[serp_result(f"Acme Analytics scam on {site}", f"https://{site}/acme") for site in sites])
    enable_search(monkeypatch, lambda query: reply)
    enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer(
        [label(f"S{n}", "scam_report", "suspicious") for n in (1, 2, 3)], risk_score=90)))
    after = client.post("/api/analyze", json={"job_text": text}).json()

    report_reason = next(r for r in after["reasons"] if r["feature"] == "web_scam_reports")
    assert report_reason["impact"] == -1.2
    assert after["trust_score"] < before["trust_score"]
    # The AI's own risk score is shown, but is not part of trust_score.
    assert after["evidence_analysis"]["risk_score"] == 90
    assert {r["feature"] for r in after["reasons"]} - {r["feature"] for r in before["reasons"]} == {"web_scam_reports"}


def test_scam_example_scores_low():
    response = client.post("/api/analyze", json={"job_text": EXAMPLE_JOB_TEXT})
    assert response.status_code == 200
    body = response.json()
    assert body["trust_level"] == "low"
    assert body["extracted"]["company_name"] == "Brightpath Global Solutions"
    features = {reason["feature"] for reason in body["reasons"]}
    assert {"upfront_payment", "offplatform_contact", "no_interview", "free_email"} <= features
    assert body["checks_total"] == 5


def test_genuine_looking_posting_with_old_domain_scores_high(fake_whois):
    fake_whois(days_old=10 * 365)
    text = (
        "Acme Analytics is hiring a Data Analyst in Pune. 1-3 years of experience.\n"
        "Selection: online test followed by two interview rounds.\n"
        "Apply at https://careers.acme-analytics.in/jobs/42"
    )
    body = client.post("/api/analyze", json={"job_text": text}).json()
    assert body["extracted"]["website_domain"] == "acme-analytics.in"
    assert body["trust_level"] == "high"


def test_brand_new_domain_lowers_trust(fake_whois):
    fake_whois(days_old=12)
    body = client.post("/api/analyze", json={"job_text": "Apply at https://quick-jobs-now.in"}).json()
    domain_reason = next(r for r in body["reasons"] if r["feature"] == "domain_age")
    assert domain_reason["effect"] == "lowers_trust"
    assert "12 days" in domain_reason["message"]


def test_empty_request_is_rejected():
    assert client.post("/api/analyze", json={}).status_code == 422


def test_private_addresses_are_blocked():
    with pytest.raises(PostingFetchError):
        fetch_posting("http://127.0.0.1/admin")


def test_json_ld_job_posting_is_read():
    html = """<script type="application/ld+json">
    {"@type": "JobPosting", "description": "<p>Build things</p>",
     "hiringOrganization": {"name": "Acme Ltd", "sameAs": "https://acme.com"},
     "baseSalary": {"currency": "INR", "value": {"minValue": 25000, "maxValue": 40000, "unitText": "MONTH"}}}
    </script>"""
    data = _read_job_posting_json(BeautifulSoup(html, "html.parser"))
    assert data["company_name"] == "Acme Ltd"
    assert data["company_website"] == "https://acme.com"
    assert data["salary_text"] == "INR 25000 - 40000 per month"
    assert data["description"] == "Build things"
