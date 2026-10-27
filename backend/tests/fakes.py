"""
Fake SerpApi and Gemini replies shared by the tests, so no test ever spends
the free search / AI quota. The shapes copy the real APIs' JSON.
"""

import json

from app import config
from app.services import gemini_client, web_search


class FakeResponse:
    """Stands in for a `requests` response."""

    def __init__(self, status_code: int = 200, data=None, text: str | None = None):
        self.status_code = status_code
        self._data = data
        self.text = text if text is not None else json.dumps(data)

    def json(self):
        if self._data is None:
            raise ValueError("not JSON")
        return self._data


def serp_result(title: str, link: str, snippet: str = "") -> dict:
    """One item of SerpApi's "organic_results" list."""
    return {"position": 1, "title": title, "link": link, "snippet": snippet}


def serp_reply(*results: dict) -> dict:
    return {"search_metadata": {"status": "Success"}, "organic_results": list(results)}


def gemini_reply(answer: dict) -> dict:
    """Gemini's generateContent reply, carrying `answer` as its JSON text."""
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}, "finishReason": "STOP"}]}


def ai_answer(evidence: list[dict], risk_score: int = 20) -> dict:
    return {
        "risk_score": risk_score,
        "summary": "Test summary.",
        "risk_signals": [],
        "reassuring_signals": [],
        "evidence": evidence,
        "limitations": [],
    }


def label(source_id: str, category: str, signal: str = "neutral", verification: str = "allegation") -> dict:
    return {"source_id": source_id, "relevance": "test", "category": category,
            "signal": signal, "verification": verification}


def enable_search(monkeypatch, reply_for_query) -> list[str]:
    """Turn web search on with a fake key. `reply_for_query(query)` returns SerpApi JSON or raises."""
    monkeypatch.setattr(config, "SERPAPI_API_KEY", "fake-serpapi-key")
    queries = []

    def fake_call(query):
        queries.append(query)
        return reply_for_query(query)

    monkeypatch.setattr(web_search, "call_serpapi", fake_call)
    return queries  # lets a test see which searches were "sent"


def enable_ai(monkeypatch, reply_for_body) -> list[dict]:
    """Turn Gemini on with a fake key. `reply_for_body(body)` returns Gemini JSON or raises."""
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "test-model")
    bodies = []

    def fake_call(body):
        bodies.append(body)
        return reply_for_body(body)

    monkeypatch.setattr(gemini_client, "call_gemini", fake_call)
    return bodies  # lets a test read the prompt that was "sent"
