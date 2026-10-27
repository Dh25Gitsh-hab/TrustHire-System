"""
posting_fetcher.py — downloads a job posting from a link and turns it into text.

Steps:
  1. Safety check: only public http/https addresses are allowed. This stops
     someone from using our server to reach private machines (an attack
     called SSRF — Server-Side Request Forgery).
  2. Download the page, with a time limit and a size limit.
  3. If the site embeds structured "JobPosting" data (JSON-LD, which many job
     boards include for Google Jobs), read company name, website and salary
     from it — this is far more reliable than guessing from the text.
  4. Strip the HTML and return the visible text.
"""

import ipaddress
import json
import socket
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.config import HTTP_TIMEOUT_SECONDS, MAX_JOB_TEXT_CHARS, MAX_PAGE_BYTES, USER_AGENT

# Some websites refuse requests that do not look like a normal browser.
REQUEST_HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

MAX_REDIRECTS = 5

# If a page has less visible text than this, it is probably a login wall
# (LinkedIn, for example, hides most postings from logged-out visitors).
MIN_USEFUL_TEXT_CHARS = 200


class PostingFetchError(Exception):
    """Raised when a link cannot be read. The message is shown to the user."""


@dataclass
class FetchedPosting:
    url: str  # final address after any redirects
    text: str  # readable text of the posting
    structured: dict = field(default_factory=dict)  # data from JSON-LD, if any


# ------------------------------------------------------------------
# Main function
# ------------------------------------------------------------------
def fetch_posting(url: str) -> FetchedPosting:
    """Download `url` and return the job posting's text (+ structured data)."""
    url = url.strip()
    if "://" not in url:
        url = "https://" + url  # users often paste "www.site.com/job/123"

    final_url, html_bytes = _download(url)
    soup = BeautifulSoup(html_bytes, "html.parser")

    # Read JSON-LD first, because the next step deletes all <script> tags.
    structured = _read_job_posting_json(soup)

    # Prefer the clean description from JSON-LD; otherwise use the page text.
    text = structured.pop("description", "") or _html_to_text(soup)
    if len(text) < MIN_USEFUL_TEXT_CHARS:
        raise PostingFetchError(
            "This page did not show the job description (it may need a login, like LinkedIn). "
            "Please copy the job description and paste it as text instead."
        )

    return FetchedPosting(url=final_url, text=text[:MAX_JOB_TEXT_CHARS], structured=structured)


# ------------------------------------------------------------------
# Step 1 + 2: safe download
# ------------------------------------------------------------------
def _ensure_public_address(url: str) -> None:
    """Refuse links that point to localhost or a private network."""
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise PostingFetchError("Please enter a valid link starting with http:// or https://.")

    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or 443)
    except socket.gaierror:
        raise PostingFetchError(f"The website '{parts.hostname}' could not be found.")

    for address_info in addresses:
        ip_text = address_info[4][0].split("%")[0]  # drop IPv6 zone like "%eth0"
        if not ipaddress.ip_address(ip_text).is_global:
            raise PostingFetchError("For safety, links to private or local network addresses are not allowed.")


def _download(url: str) -> tuple[str, bytes]:
    """
    Download the page and return (final_url, page_bytes).

    Redirects are followed by hand so that EVERY address in the chain
    passes the safety check, not just the first one.
    """
    for _ in range(MAX_REDIRECTS + 1):
        _ensure_public_address(url)
        try:
            response = requests.get(
                url,
                headers=REQUEST_HEADERS,
                timeout=HTTP_TIMEOUT_SECONDS,
                allow_redirects=False,
                stream=True,  # lets us stop reading once the size limit is hit
            )
        except requests.RequestException:
            raise PostingFetchError("We could not connect to that website. Please paste the job text instead.")

        if response.is_redirect:
            url = urljoin(url, response.headers.get("Location", ""))
            response.close()
            continue

        if response.status_code != 200:
            response.close()
            raise PostingFetchError(
                f"The website replied with error {response.status_code}. Please paste the job text instead."
            )

        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type and "text" not in content_type:
            response.close()
            raise PostingFetchError("That link is not a web page (it may be a PDF or image). Please paste the text.")

        return url, _read_limited(response)

    raise PostingFetchError("That link redirected too many times.")


def _read_limited(response: requests.Response) -> bytes:
    """Read the response body, but never more than MAX_PAGE_BYTES."""
    chunks, total = [], 0
    for chunk in response.iter_content(chunk_size=64_000):
        chunks.append(chunk)
        total += len(chunk)
        if total >= MAX_PAGE_BYTES:
            break
    response.close()
    return b"".join(chunks)[:MAX_PAGE_BYTES]


# ------------------------------------------------------------------
# Step 3: structured JobPosting data (JSON-LD)
# ------------------------------------------------------------------
def _read_job_posting_json(soup: BeautifulSoup) -> dict:
    """
    Look for <script type="application/ld+json"> blocks describing a JobPosting
    (https://schema.org/JobPosting) and return the fields we care about.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except ValueError:
            continue  # broken JSON on the page — just skip it

        for item in _walk_json_ld(data):
            item_type = item.get("@type")
            types = item_type if isinstance(item_type, list) else [item_type]
            if "JobPosting" in types:
                return _job_posting_fields(item)
    return {}


def _walk_json_ld(data):
    """JSON-LD can be one object, a list, or an object with a "@graph" list."""
    if isinstance(data, list):
        for element in data:
            yield from _walk_json_ld(element)
    elif isinstance(data, dict):
        yield data
        if "@graph" in data:
            yield from _walk_json_ld(data["@graph"])


def _job_posting_fields(job: dict) -> dict:
    """Pick company name, website, salary and description out of a JobPosting."""
    org = job.get("hiringOrganization") or {}
    if isinstance(org, list):
        org = org[0] if org else {}
    if isinstance(org, str):
        org = {"name": org}

    website = org.get("sameAs") or org.get("url")
    if isinstance(website, list):
        website = website[0] if website else None

    description_html = job.get("description") or ""
    description = _html_to_text(BeautifulSoup(description_html, "html.parser")) if description_html else ""

    return {
        "company_name": org.get("name"),
        "company_website": website,
        "salary_text": _salary_to_text(job.get("baseSalary")),
        "description": description,
    }


def _salary_to_text(base_salary) -> str | None:
    """
    Turn schema.org salary data into a sentence our salary parser understands,
    e.g. {"currency": "INR", "value": {"minValue": 25000, "unitText": "MONTH"}}
    becomes "INR 25000 per month".
    """
    if not isinstance(base_salary, dict):
        return None
    value = base_salary.get("value")
    if not isinstance(value, dict):
        value = {"value": value}

    low = value.get("minValue") or value.get("value")
    high = value.get("maxValue") or low
    if low is None:
        return None

    currency = base_salary.get("currency") or "INR"
    amount = f"{low}" if high == low else f"{low} - {high}"
    unit = str(value.get("unitText") or "").lower()  # month / year / day / hour / week
    return f"{currency} {amount}" + (f" per {unit}" if unit else "")


# ------------------------------------------------------------------
# Step 4: HTML -> plain text
# ------------------------------------------------------------------
def _html_to_text(soup: BeautifulSoup) -> str:
    """Remove scripts, menus and footers, then return clean visible text."""
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form"]):
        tag.decompose()
    raw_text = soup.get_text(separator="\n")
    lines = (" ".join(line.split()) for line in raw_text.splitlines())
    return "\n".join(line for line in lines if line)
