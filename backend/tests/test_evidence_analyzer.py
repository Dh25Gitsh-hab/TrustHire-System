"""Tests for gemini_client.py + evidence_analyzer.py — the AI part (network faked)."""

import pytest
import requests

from app import config
from app.services import evidence_analyzer, gemini_client
from app.services.gemini_client import GeminiError
from app.services.web_search import SearchResult
from tests.fakes import FakeResponse, ai_answer, enable_ai, gemini_reply, label


def results(count: int) -> list[SearchResult]:
    return [
        SearchResult(title=f"Title {n}", url=f"https://site{n}.com/page", domain=f"site{n}.com",
                     snippet=f"Snippet {n}", date=None, query="q")
        for n in range(1, count + 1)
    ]


# --- Reading Gemini's reply ---------------------------------------------------------
def test_json_answer_is_read_and_thoughts_ignored():
    reply = {"candidates": [{
        "content": {"parts": [{"text": "thinking...", "thought": True}, {"text": '{"risk_score": 5}'}]},
        "finishReason": "STOP",
    }]}
    assert gemini_client.parse_json_answer(reply) == {"risk_score": 5}


def test_invalid_json_can_be_retried():
    reply = {"candidates": [{"content": {"parts": [{"text": "Sure! Here is"}]}, "finishReason": "STOP"}]}
    with pytest.raises(GeminiError) as error:
        gemini_client.parse_json_answer(reply)
    assert error.value.retryable


@pytest.mark.parametrize("reply", [
    {"promptFeedback": {"blockReason": "SAFETY"}},
    {"candidates": [{"content": {"parts": [{"text": "{}"}]}, "finishReason": "SAFETY"}]},
])
def test_blocked_or_cut_off_answers_are_errors(reply):
    with pytest.raises(GeminiError):
        gemini_client.parse_json_answer(reply)


# --- HTTP errors ----------------------------------------------------------------------
@pytest.mark.parametrize("status, text, expected, retryable", [
    (429, '{"error": {"status": "RESOURCE_EXHAUSTED"}}', "free AI limit is used up", False),
    (400, '{"error": {"details": [{"reason": "API_KEY_INVALID"}]}}', "rejected the server's API key", False),
    (404, '{"error": {"status": "NOT_FOUND"}}', "GEMINI_MODEL is not available", False),
    (503, '{"error": {"status": "UNAVAILABLE"}}', "temporary problem", True),
])
def test_http_errors(monkeypatch, status, text, expected, retryable):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "secret-gemini-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "test-model")
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse(status, None, text=text))
    with pytest.raises(GeminiError) as error:
        gemini_client.call_gemini({})
    assert expected in str(error.value)
    assert error.value.retryable == retryable
    assert "secret-gemini-key" not in str(error.value)


def test_key_is_sent_in_a_header_not_the_url(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "secret-gemini-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "test-model")
    sent = {}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, headers=headers)
        return FakeResponse(200, gemini_reply({}))

    monkeypatch.setattr(requests, "post", fake_post)
    gemini_client.call_gemini({})
    assert "secret-gemini-key" not in sent["url"]
    assert sent["headers"]["x-goog-api-key"] == "secret-gemini-key"
    assert sent["url"].endswith("/models/test-model:generateContent")


# --- Checking the AI's answer -----------------------------------------------------------
def test_invented_and_unrelated_sources_are_dropped(monkeypatch):
    enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([
        label("S1", "scam_report", "suspicious"),
        label("S99", "scam_report", "suspicious"),  # we never sent S99 -> invented
        label("S2", "unrelated"),  # a different company -> hidden
        label("S1", "official"),  # repeat of S1 -> ignored
    ], risk_score=75)))
    analysis = evidence_analyzer.analyze("Acme", "acme.com", None, results(2))
    assert [item.url for item in analysis.evidence] == ["https://site1.com/page"]
    # Title and link come from the search results, never from the AI.
    assert analysis.evidence[0].title == "Title 1"
    assert analysis.risk_level == "High"  # worked out from the score by fixed bands
    assert analysis.model == "test-model"


def test_malformed_answer_is_retried_once(monkeypatch):
    answers = [{"summary": "missing risk_score"}, ai_answer([])]
    bodies = enable_ai(monkeypatch, lambda body: gemini_reply(answers.pop(0)))
    analysis = evidence_analyzer.analyze("Acme", None, None, results(1))
    assert analysis.status == "completed"
    assert len(bodies) == 2


def test_out_of_range_score_counts_as_malformed(monkeypatch):
    enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([], risk_score=150)))
    with pytest.raises(GeminiError, match="not in the expected format"):
        evidence_analyzer.analyze("Acme", None, None, results(1))


def test_used_up_quota_is_not_retried(monkeypatch):
    def reply(body):
        raise GeminiError("the free AI limit is used up for now (per-minute or daily limit)")

    bodies = enable_ai(monkeypatch, reply)
    with pytest.raises(GeminiError, match="limit is used up"):
        evidence_analyzer.analyze("Acme", None, None, results(1))
    assert len(bodies) == 1  # asked only once


def test_same_evidence_twice_uses_the_cache(monkeypatch):
    bodies = enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([])))
    evidence_analyzer.analyze("Acme", None, None, results(2))
    evidence_analyzer.analyze("Acme", None, None, results(2))
    assert len(bodies) == 1


def test_prompt_treats_search_results_as_data(monkeypatch):
    bodies = enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([])))
    evidence_analyzer.analyze("Acme", "acme.com", 20, results(1))
    system = bodies[0]["systemInstruction"]["parts"][0]["text"]
    assert "UNTRUSTED DATA" in system
    assert bodies[0]["generationConfig"]["responseMimeType"] == "application/json"


def test_thinking_level_is_sent_only_when_set(monkeypatch):
    bodies = enable_ai(monkeypatch, lambda body: gemini_reply(ai_answer([])))
    monkeypatch.setattr(config, "GEMINI_THINKING_LEVEL", "low")
    evidence_analyzer.analyze("Acme", None, None, results(1))
    assert bodies[0]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}

    monkeypatch.setattr(config, "GEMINI_THINKING_LEVEL", "")
    evidence_analyzer.analyze("Other", None, None, results(1))  # different input -> not cached
    assert "thinkingConfig" not in bodies[1]["generationConfig"]
