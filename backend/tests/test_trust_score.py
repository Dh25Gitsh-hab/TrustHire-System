"""Tests for app/scoring/trust_score.py — the logistic trust-score model."""

from app.schemas import CheckResult, Signal
from app.scoring.trust_score import calculate_trust_score


def check_with(*signals: tuple[str, float], status: str = "completed") -> CheckResult:
    return CheckResult(
        key="test",
        title="Test",
        status=status,
        summary="",
        signals=[Signal(feature=feature, value=value, message=feature) for feature, value in signals],
    )


def test_scam_signals_give_low_trust():
    result = calculate_trust_score([check_with(("upfront_payment", 1), ("offplatform_contact", 1), ("domain_age", -3.3))])
    assert result.level == "low"
    assert result.reasons[0].feature == "upfront_payment"  # strongest reason first
    assert all(reason.effect == "lowers_trust" for reason in result.reasons)


def test_old_domain_and_no_flags_give_high_trust():
    result = calculate_trust_score([check_with(("domain_age", 2.5))])
    assert result.level == "high"
    assert result.reasons[0].effect == "raises_trust"


def test_no_evidence_gives_medium_with_special_verdict():
    result = calculate_trust_score([check_with()])
    assert result.level == "medium"
    assert "could not find enough information" in result.verdict


def test_unfinished_checks_are_ignored():
    result = calculate_trust_score([check_with(("upfront_payment", 1), status="not_configured")])
    assert result.reasons == []


def test_score_stays_between_1_and_99():
    very_bad = calculate_trust_score([check_with(("salary_too_high", 1_000))])
    very_good = calculate_trust_score([check_with(("domain_age", 1_000))])
    assert very_bad.score == 1
    assert very_good.score == 99


def test_web_scam_reports_weight():
    """3 or more independent report websites (value 1.0) lower z by exactly 1.2."""
    result = calculate_trust_score([check_with(("web_scam_reports", 1.0))])
    assert result.reasons[0].impact == -1.2
    assert result.reasons[0].effect == "lowers_trust"


def test_zero_web_reports_changes_nothing():
    assert calculate_trust_score([check_with(("web_scam_reports", 0.0))]).reasons == []
