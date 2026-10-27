"""Tests for saving analyses and reports (Supabase replaced by a fake client)."""

import uuid

from fastapi.testclient import TestClient

from app import config, database
from app.main import app
from app.schemas import EXAMPLE_JOB_TEXT
from tests.fakes import ai_answer, enable_ai, enable_search, gemini_reply, label, serp_reply, serp_result

client = TestClient(app)


class FakeTable:
    """Records every insert instead of sending it to Supabase."""

    def __init__(self, store: dict, name: str):
        self.store, self.name = store, name

    def insert(self, row, returning=None):
        self.store.setdefault(self.name, []).append(row)
        return self

    def execute(self):
        return None


class FakeSupabase:
    def __init__(self):
        self.store = {}

    def table(self, name):
        return FakeTable(self.store, name)


def enable_fake_database(monkeypatch) -> FakeSupabase:
    fake = FakeSupabase()
    monkeypatch.setattr(config, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_KEY", "fake-key")
    monkeypatch.setattr(database, "_client", fake)
    return fake


def test_analysis_is_saved_without_personal_details(monkeypatch):
    fake = enable_fake_database(monkeypatch)
    body = client.post("/api/analyze", json={"job_text": EXAMPLE_JOB_TEXT}).json()

    saved = fake.store["analyses"][0]
    assert body["analysis_id"] == saved["id"]
    assert saved["trust_level"] == "low"
    assert saved["features"]["upfront_payment"] == 1.0
    # Privacy: no posting text, e-mails or phone numbers are stored.
    assert "job_text" not in saved and "emails" not in saved and "phone_numbers" not in saved


def test_without_database_analysis_still_works():
    body = client.post("/api/analyze", json={"job_text": EXAMPLE_JOB_TEXT}).json()
    assert body["analysis_id"] is None
    assert body["trust_level"] == "low"


def test_report_is_saved(monkeypatch):
    fake = enable_fake_database(monkeypatch)
    analysis_id = str(uuid.uuid4())
    response = client.post("/api/reports", json={"analysis_id": analysis_id, "user_verdict": "scam"})
    assert response.json() == {"saved": True}
    assert fake.store["scam_reports"][0]["analysis_id"] == analysis_id


def test_report_needs_database():
    response = client.post("/api/reports", json={"analysis_id": str(uuid.uuid4()), "user_verdict": "scam"})
    assert response.status_code == 503


def test_report_rejects_bad_verdict(monkeypatch):
    enable_fake_database(monkeypatch)
    response = client.post("/api/reports", json={"analysis_id": str(uuid.uuid4()), "user_verdict": "maybe"})
    assert response.status_code == 422


def test_web_evidence_is_saved_without_full_links(monkeypatch):
    fake = enable_fake_database(monkeypatch)
    reply = serp_reply(serp_result("Recruiter profile", "https://in.linkedin.com/in/some-person"))
    enable_search(monkeypatch, lambda query: reply)
    enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([label("S1", "neutral_info")])))
    client.post("/api/analyze", json={"job_text": EXAMPLE_JOB_TEXT})

    evidence = fake.store["analyses"][0]["features"]["evidence"]
    assert evidence["status"] == "completed"
    assert evidence["sources"] == [
        {"domain": "linkedin.com", "category": "neutral_info", "signal": "neutral", "verification": "allegation"}
    ]
    assert "some-person" not in str(fake.store["analyses"][0])  # no full links stored
