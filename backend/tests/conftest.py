"""
Shared test setup.

backend/.env holds real API keys, so before EVERY test we switch all
third-party services off. Tests never write to the real Supabase database
or spend the data.gov.in / SerpApi / Gemini quota. A test that wants a
service "on" sets a fake key and replaces the network function with a fake one.
"""

import pytest

from app import config, database
from app.services import evidence_analyzer, web_search


@pytest.fixture(autouse=True)
def no_third_party_services(monkeypatch):
    for setting in ("SUPABASE_URL", "SUPABASE_KEY", "DATAGOVIN_API_KEY",
                    "SERPAPI_API_KEY", "GEMINI_API_KEY", "GEMINI_MODEL"):
        monkeypatch.setattr(config, setting, "")
    monkeypatch.setattr(database, "_client", None)
    # Start every test with empty caches, so one test's results never leak into another.
    web_search._cache.clear()
    evidence_analyzer._cache.clear()
