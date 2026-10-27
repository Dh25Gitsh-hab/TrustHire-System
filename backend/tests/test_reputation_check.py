"""Tests for app/checks/reputation_check.py — web search + AI (network faked)."""

from app.checks import reputation_check
from app.schemas import ExtractedInfo
from app.services.gemini_client import GeminiError
from app.services.web_search import SearchError
from tests.fakes import ai_answer, enable_ai, enable_search, gemini_reply, label, serp_reply, serp_result

INFO = ExtractedInfo(
    company_name="Brightpath Global Pvt. Ltd.",
    website_domain="brightpath.in",
    emails=["hr.brightpath@gmail.com"],
    phone_numbers=["+91 98765 43210"],
)

# Five search results (the fake search returns them for every query; duplicates are removed).
RESULTS = serp_reply(
    serp_result("Brightpath asked me for a fee", "https://www.reddit.com/r/india/comments/a/fee/"),
    serp_result("Brightpath Global scam?", "https://www.reddit.com/r/developersIndia/comments/b/scam/"),
    serp_result("Brightpath Global complaints", "https://www.complaintsboard.in/brightpath"),
    serp_result("Beware: fake offers in Brightpath's name", "https://news.example.com/brightpath-warning"),
    serp_result("Brightpath Global - Careers", "https://brightpath.in/careers"),
)


def evidence_of(result):
    return result.details["evidence_analysis"]


def test_without_keys_shows_manual_links():
    result = reputation_check.run(INFO, "")
    assert result.status == "not_configured"
    assert result.signals == []
    assert evidence_of(result).status == "not_configured"
    assert len(result.manual_links) == 3  # Google, Reddit, LinkedIn


def test_nothing_to_search_for_is_skipped():
    result = reputation_check.run(ExtractedInfo(), "")
    assert result.status == "skipped"
    assert evidence_of(result).status == "skipped"


def test_legal_ending_is_removed_before_searching():
    assert reputation_check.search_name("Acme Analytics Pvt. Ltd.") == "Acme Analytics"
    assert reputation_check.search_name("Infosys Limited") == "Infosys"


def test_reports_are_counted_by_independent_website(monkeypatch):
    enable_search(monkeypatch, lambda query: RESULTS)
    bodies = enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([
        label("S1", "scam_report", "suspicious"),  # reddit.com
        label("S2", "scam_report", "suspicious"),  # reddit.com again -> same website
        label("S3", "scam_report", "suspicious"),  # complaintsboard.in
        label("S4", "impersonation_warning", "neutral"),  # does not count
        label("S5", "official", "reassuring", "verified_fact"),
    ])))
    result = reputation_check.run(INFO, "")

    assert result.status == "completed"
    assert result.details["report_sites"] == 2
    signal = result.signals[0]
    assert signal.feature == "web_scam_reports"
    assert signal.value == round(2 / 3, 3)
    assert evidence_of(result).status == "completed"
    assert len(evidence_of(result).evidence) == 5

    # Privacy: Gemini never sees the recruiter's e-mail or phone number.
    prompt = bodies[0]["contents"][0]["parts"][0]["text"]
    assert "gmail.com" not in prompt and "98765" not in prompt


def test_a_report_on_the_companys_own_website_does_not_count(monkeypatch):
    enable_search(monkeypatch, lambda query: RESULTS)
    enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([label("S5", "scam_report", "suspicious")])))
    result = reputation_check.run(INFO, "")
    assert result.details["report_sites"] == 0
    assert result.signals[0].value == 0


def test_used_up_search_quota_gives_no_signal(monkeypatch):
    def reply(query):
        raise SearchError("the free web-search limit is used up for now (monthly or hourly)")

    enable_search(monkeypatch, reply)
    result = reputation_check.run(INFO, "")
    assert result.status == "error"
    assert result.signals == []  # a failure is never treated as suspicious
    assert evidence_of(result).status == "unavailable"
    assert "limit is used up" in evidence_of(result).message


def test_search_works_but_ai_not_connected(monkeypatch):
    enable_search(monkeypatch, lambda query: RESULTS)
    result = reputation_check.run(INFO, "")
    evidence = evidence_of(result)
    assert result.status == "not_configured"
    assert result.signals == []
    assert evidence.status == "partial"
    assert {item.category for item in evidence.evidence} == {"not_analysed"}


def test_search_works_but_ai_fails(monkeypatch):
    enable_search(monkeypatch, lambda query: RESULTS)

    def reply(body):
        raise GeminiError("the free AI limit is used up for now (per-minute or daily limit)")

    enable_ai(monkeypatch, reply)
    result = reputation_check.run(INFO, "")
    assert result.status == "error"
    assert result.signals == []
    assert evidence_of(result).status == "partial"


def test_no_results_means_zero_reports_without_asking_the_ai(monkeypatch):
    enable_search(monkeypatch, lambda query: serp_reply())
    bodies = enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([])))
    result = reputation_check.run(INFO, "")
    assert result.status == "completed"
    assert result.signals[0].value == 0
    assert bodies == []  # nothing to analyse -> no AI request spent
    assert any("not evidence of fraud" in note for note in evidence_of(result).limitations)
