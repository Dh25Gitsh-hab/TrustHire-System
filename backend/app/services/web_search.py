"""
web_search.py — Google search results through SerpApi (serpapi.com).

SerpApi runs a Google search for us and returns the results as JSON, so we
never scrape Google, Reddit or LinkedIn ourselves. We only see what Google has
indexed PUBLICLY (title, link, short snippet) — never private posts, never
pages behind a login, and never "every post" about a company.

Free plan: 250 searches a month, 50 an hour. To save them we:
  * run at most MAX_SEARCHES_PER_ANALYSIS searches per analysis (default 3),
  * skip duplicate queries,
  * remember results for EVIDENCE_CACHE_HOURS (see cache.py).
SerpApi itself does not count failed searches, or repeats within 1 hour.

SECURITY: SerpApi wants the key inside the URL (?api_key=...). Error messages
from the requests library can contain that URL, so we NEVER show or log
them — only our own messages and the error's type name.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from app import config
from app.services.cache import TimedCache
from app.services.feature_extractor import registrable_domain

logger = logging.getLogger("trusthire.web_search")

SERPAPI_URL = "https://serpapi.com/search.json"

MAX_TITLE_CHARS = 150
MAX_SNIPPET_CHARS = 300

_cache = TimedCache(max_age_seconds=config.EVIDENCE_CACHE_HOURS * 3600)


class SearchError(Exception):
    """A search failed. The message is safe to show users (it never contains the key)."""


@dataclass
class SearchResult:
    title: str
    url: str
    domain: str  # registrable domain of the link, e.g. "reddit.com"
    snippet: str  # Google's short extract of the page
    date: str | None  # only some results have one
    query: str  # the search that found it


def is_configured() -> bool:
    return bool(config.SERPAPI_API_KEY)


# ------------------------------------------------------------------
# 1. Which searches to run
# ------------------------------------------------------------------
def build_queries(company: str | None, domain: str | None) -> list[str]:
    """
    The searches for one analysis, most useful first, without duplicates:

      1. scam reports / complaints about the company anywhere on the web
      2. what OTHER websites say about the company's website
         (e.g. a government warning that names a fake job portal)
      3. public Reddit and LinkedIn pages about the company
      4. the company's official website and careers page

    The searches of one analysis are always different from each other; the
    same search repeated in a later analysis is answered from the cache.
    """
    queries = []
    if company:
        queries.append(f'"{company}" scam OR fraud OR fake job')
    if domain:
        queries.append(f'"{domain}" -site:{domain}')
    if company:
        queries.append(f'"{company}" site:reddit.com OR site:linkedin.com')
        queries.append(f'"{company}" official website careers')
    return queries[: config.MAX_SEARCHES_PER_ANALYSIS]


# ------------------------------------------------------------------
# 2. Run the searches
# ------------------------------------------------------------------
def search_many(queries: list[str]) -> tuple[list[SearchResult], list[str]]:
    """
    Run the searches at the same time and merge their results without duplicates.

    Returns (results, notes about searches that failed).
    Raises SearchError only if EVERY search failed.
    """
    if not queries:
        return [], []
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        outcomes = list(pool.map(_search_or_error, queries))

    results = [result for outcome in outcomes if isinstance(outcome, list) for result in outcome]
    failures = [outcome for outcome in outcomes if isinstance(outcome, SearchError)]
    if len(failures) == len(queries):
        raise failures[0]
    notes = [f"{len(failures)} of {len(queries)} web searches failed ({failures[0]})."] if failures else []
    return deduplicate(results), notes


def _search_or_error(query: str):
    """search(), but a failure is returned instead of raised (so one bad search does not stop the rest)."""
    try:
        return search(query)
    except SearchError as error:
        return error


def search(query: str) -> list[SearchResult]:
    """One Google search through SerpApi. Results are cached."""
    # Google ignores case and extra spaces, so '"ACME"  scam' and '"Acme" scam' are the same search.
    cache_key = " ".join(query.lower().split())
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    results = parse_results(call_serpapi(query), query)
    _cache.set(cache_key, results)  # empty results are cached too: they are a valid answer
    return results


def call_serpapi(query: str) -> dict:
    """Send one search to SerpApi and return its JSON. Kept separate so tests can replace it."""
    params = {
        "engine": "google",
        "q": query,
        "gl": "in",  # results as seen from India
        "hl": "en",
        "api_key": config.SERPAPI_API_KEY,
    }
    # "from None" drops the original error, whose text may include the URL with the key.
    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=config.HTTP_TIMEOUT_SECONDS)
    except requests.Timeout:
        raise SearchError("the web search took too long") from None
    except requests.RequestException as error:
        logger.warning("SerpApi request failed (%s)", type(error).__name__)
        raise SearchError("the web search service could not be reached") from None

    # Status codes from serpapi.com/api-status-and-error-codes
    if response.status_code in (401, 403):
        logger.warning("SerpApi rejected the API key (HTTP %s)", response.status_code)
        raise SearchError("the web search service rejected the server's API key")
    if response.status_code == 429:
        raise SearchError("the free web-search limit is used up for now (monthly or hourly)")
    if response.status_code != 200:
        raise SearchError(f"the web search service returned error {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        raise SearchError("the web search service sent an unreadable reply") from None
    if not isinstance(data, dict):
        raise SearchError("the web search service sent an unreadable reply")
    # "Error" = the search itself failed. (No results at all is still "Success".)
    if (data.get("search_metadata") or {}).get("status") == "Error":
        raise SearchError("the web search failed on the service's side")
    return data


# ------------------------------------------------------------------
# 3. Read the JSON
# ------------------------------------------------------------------
def parse_results(data: dict, query: str) -> list[SearchResult]:
    """Keep the useful fields of each normal Google result. Results without a title or link are skipped."""
    results = []
    for item in data.get("organic_results") or []:  # missing when Google found nothing
        if not isinstance(item, dict):
            continue
        title = " ".join(str(item.get("title") or "").split())
        url = str(item.get("link") or "").strip()
        host = _host(url)
        if not title or not host:
            continue
        results.append(SearchResult(
            title=title[:MAX_TITLE_CHARS],
            url=url,
            domain=registrable_domain(host),
            snippet=" ".join(str(item.get("snippet") or "").split())[:MAX_SNIPPET_CHARS],
            date=str(item["date"]) if item.get("date") else None,
            query=query,
        ))
    return results


def deduplicate(results: list[SearchResult]) -> list[SearchResult]:
    """The same page is often found by two searches — keep only the first copy."""
    unique, seen = [], set()
    for result in results:
        key = normalize_url(result.url)
        if key not in seen:
            seen.add(key)
            unique.append(result)
    return unique


def normalize_url(url: str) -> str:
    """Make equivalent links equal: ignore http/https, 'www.', '#section' and a trailing '/'."""
    parts = urlparse(url)
    host = (parts.hostname or "").removeprefix("www.")
    path = parts.path.rstrip("/")
    return f"{host}{path}?{parts.query}" if parts.query else f"{host}{path}"


def _host(url: str) -> str | None:
    """The website name of a link, or None if it is not a normal web link."""
    if not url.startswith(("http://", "https://")):
        return None
    try:
        host = urlparse(url).hostname
    except ValueError:  # malformed link
        return None
    return host if host and "." in host else None
