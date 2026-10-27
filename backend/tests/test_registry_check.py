"""Tests for app/checks/registry_check.py — MCA lookup via data.gov.in (network faked)."""

from app import config
from app.checks import registry_check
from app.schemas import ExtractedInfo

INFOSYS_RECORD = {
    "CIN": "L85110KA1981PLC013115",
    "CompanyName": "INFOSYS LIMITED",
    "CompanyStatus": "Active",
    "CompanyRegistrationdate_date": "1981-07-02",
}


def test_name_variants_follow_mca_style():
    assert registry_check.mca_name_variants("Acme Analytics Pvt. Ltd.") == ["ACME ANALYTICS PRIVATE LIMITED"]
    assert registry_check.mca_name_variants("Infosys Ltd") == ["INFOSYS LIMITED"]
    assert registry_check.mca_name_variants("Acme Analytics") == [
        "ACME ANALYTICS PRIVATE LIMITED",
        "ACME ANALYTICS LIMITED",
    ]


def test_without_api_key_shows_manual_links():
    result = registry_check.run(ExtractedInfo(company_name="Infosys"), "")
    assert result.status == "not_configured"
    assert result.manual_links


def test_found_company(monkeypatch):
    monkeypatch.setattr(config, "DATAGOVIN_API_KEY", "fake-key")
    names_searched = []

    def fake_fetch(name):
        names_searched.append(name)
        return [INFOSYS_RECORD] if name == "INFOSYS LIMITED" else []

    monkeypatch.setattr(registry_check, "fetch_mca_records", fake_fetch)
    result = registry_check.run(ExtractedInfo(company_name="Infosys"), "")

    assert names_searched == ["INFOSYS PRIVATE LIMITED", "INFOSYS LIMITED"]
    assert result.status == "completed"
    assert result.details["cin"] == "L85110KA1981PLC013115"
    features = {signal.feature: signal.value for signal in result.signals}
    assert features["registry_match"] == 1.0
    assert features["incorporation_age"] > 0  # older than one year
    assert "registry_inactive" not in features


def test_struck_off_company_is_flagged(monkeypatch):
    monkeypatch.setattr(config, "DATAGOVIN_API_KEY", "fake-key")
    record = {**INFOSYS_RECORD, "CompanyStatus": "Strike Off"}
    monkeypatch.setattr(registry_check, "fetch_mca_records", lambda name: [record])
    result = registry_check.run(ExtractedInfo(company_name="Infosys Limited"), "")
    assert "registry_inactive" in {signal.feature for signal in result.signals}


def test_not_found(monkeypatch):
    monkeypatch.setattr(config, "DATAGOVIN_API_KEY", "fake-key")
    monkeypatch.setattr(registry_check, "fetch_mca_records", lambda name: [])
    result = registry_check.run(ExtractedInfo(company_name="Brightpath Global Solutions"), "")
    assert [signal.feature for signal in result.signals] == ["registry_not_found"]


def test_api_failure_becomes_error_card(monkeypatch):
    monkeypatch.setattr(config, "DATAGOVIN_API_KEY", "fake-key")

    def broken_fetch(name):
        raise ConnectionError("network down")

    monkeypatch.setattr(registry_check, "fetch_mca_records", broken_fetch)
    result = registry_check.run(ExtractedInfo(company_name="Infosys"), "")
    assert result.status == "error"
    assert result.manual_links
