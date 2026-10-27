"""Tests for app/services/web_search.py — SerpApi client (network faked)."""

import pytest
import requests

from app import config
from app.services import web_search
from app.services.web_search import SearchError
from tests.fakes import FakeResponse, enable_search, serp_reply, serp_result


# --- Which searches -----------------------------------------------------------
def test_queries_are_limited_to_the_free_quota_budget(monkeypatch):
    monkeypatch.setattr(config, "MAX_SEARCHES_PER_ANALYSIS", 3)
    queries = web_search.build_queries("Brightpath Global", "brightpath.in")
    assert queries == [
        '"Brightpath Global" scam OR fraud OR fake job',
        '"brightpath.in" -site:brightpath.in',
        '"Brightpath Global" site:reddit.com OR site:linkedin.com',
    ]


def test_without_domain_the_official_site_search_is_used(monkeypatch):
    monkeypatch.setattr(config, "MAX_SEARCHES_PER_ANALYSIS", 3)
    queries = web_search.build_queries("Brightpath Global", None)
    assert len(queries) == 3
    assert queries[-1] == '"Brightpath Global" official website careers'


# --- Reading SerpApi's JSON -----------------------------------------------------
def test_results_are_parsed_and_bad_items_skipped():
    data = serp_reply(
        serp_result("Brightpath scam?", "https://www.reddit.com/r/india/comments/abc/x/", "They asked for a fee"),
        {"title": "No link here"},  # missing link -> skipped
        {"link": "https://example.com/page"},  # missing title -> skipped
        serp_result("Not a web link", "javascript:alert(1)"),  # not http(s) -> skipped
    )
    data["organic_results"][0]["date"] = "Mar 3, 2026"
    results = web_search.parse_results(data, "q")
    assert len(results) == 1
    assert results[0].domain == "reddit.com"
    assert results[0].snippet == "They asked for a fee"
    assert results[0].date == "Mar 3, 2026"


def test_missing_snippet_and_date_are_fine():
    results = web_search.parse_results(serp_reply(serp_result("Title", "https://acme.co.in/about")), "q")
    assert results[0].snippet == "" and results[0].date is None
    assert results[0].domain == "acme.co.in"


def test_no_results_is_not_an_error(monkeypatch):
    # What SerpApi sends when Google found nothing: HTTP 200, status "Success", no organic_results.
    nothing = {"search_metadata": {"status": "Success"}, "error": "Google hasn't returned any results for this query."}
    monkeypatch.setattr(config, "SERPAPI_API_KEY", "fake-key")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse(200, nothing))
    assert web_search.search('"Nobody Ltd" scam') == []


def test_same_page_from_two_searches_is_kept_once():
    first = web_search.parse_results(serp_reply(serp_result("A", "https://www.acme.com/jobs/")), "q1")
    second = web_search.parse_results(serp_reply(serp_result("A", "http://acme.com/jobs#top")), "q2")
    assert len(web_search.deduplicate(first + second)) == 1


# --- Errors ---------------------------------------------------------------------
@pytest.mark.parametrize("status, expected", [
    (401, "rejected the server's API key"),
    (429, "limit is used up"),
    (503, "returned error 503"),
])
def test_http_errors_become_friendly_messages(monkeypatch, status, expected):
    monkeypatch.setattr(config, "SERPAPI_API_KEY", "secret-key-123")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse(status, {"error": "x"}))
    with pytest.raises(SearchError) as error:
        web_search.call_serpapi("q")
    assert expected in str(error.value)
    assert "secret-key-123" not in str(error.value)


def test_network_error_never_reveals_the_key(monkeypatch):
    monkeypatch.setattr(config, "SERPAPI_API_KEY", "secret-key-123")

    def broken_get(*args, **kwargs):
        # Real `requests` errors include the full URL — which contains the key.
        raise requests.ConnectionError("Max retries exceeded with url: /search.json?api_key=secret-key-123")

    monkeypatch.setattr(requests, "get", broken_get)
    with pytest.raises(SearchError) as error:
        web_search.call_serpapi("q")
    assert "secret-key-123" not in str(error.value)
    assert error.value.__cause__ is None and error.value.__suppress_context__  # original error dropped


def test_timeout(monkeypatch):
    monkeypatch.setattr(config, "SERPAPI_API_KEY", "fake-key")

    def slow_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", slow_get)
    with pytest.raises(SearchError, match="took too long"):
        web_search.call_serpapi("q")


def test_one_failed_search_does_not_stop_the_others(monkeypatch):
    def reply(query):
        if "reddit" in query:
            raise SearchError("the web search took too long")
        return serp_reply(serp_result("Result", f"https://site-{len(query)}.com/"))

    enable_search(monkeypatch, reply)
    results, notes = web_search.search_many(['"A" scam', '"A" site:reddit.com'])
    assert len(results) == 1
    assert notes == ["1 of 2 web searches failed (the web search took too long)."]


def test_all_searches_failing_raises(monkeypatch):
    def reply(query):
        raise SearchError("the free web-search limit is used up for now (monthly or hourly)")

    enable_search(monkeypatch, reply)
    with pytest.raises(SearchError, match="limit is used up"):
        web_search.search_many(['"A" scam', '"A" site:reddit.com'])


# --- Cache ------------------------------------------------------------------------
def test_repeated_search_uses_the_cache(monkeypatch):
    sent = enable_search(monkeypatch, lambda query: serp_reply(serp_result("R", "https://r.com/")))
    web_search.search('"Acme" scam')
    web_search.search('"ACME"   scam')  # same search for Google: different case and spacing
    assert len(sent) == 1
