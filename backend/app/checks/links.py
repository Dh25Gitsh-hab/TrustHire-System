"""
links.py — builds "verify it yourself" links shown on each check card.

When a check cannot run automatically (no API access yet, or a site that
blocks automated access), the synopsis says the system should fall back to
giving the user a direct link to verify manually. These helpers build those links.
"""

from urllib.parse import quote_plus

from app.schemas import ManualLink


def google_search(label: str, query: str) -> ManualLink:
    return ManualLink(label=label, url=f"https://www.google.com/search?q={quote_plus(query)}")


def reddit_search(label: str, query: str) -> ManualLink:
    return ManualLink(label=label, url=f"https://www.reddit.com/search/?q={quote_plus(query)}")
