"""Tests for app/checks/red_flags.py — the hiring-process rule engine."""

from app.checks import red_flags
from app.schemas import ExtractedInfo


def features_found(text: str, info: ExtractedInfo | None = None) -> set[str]:
    result = red_flags.run(info or ExtractedInfo(), text)
    return {signal.feature for signal in result.signals}


def test_registration_fee_is_flagged():
    assert "upfront_payment" in features_found("Pay a refundable registration fee of Rs. 999 to confirm.")


def test_negated_fee_warning_is_not_flagged():
    # Genuine companies often warn candidates like this.
    assert "upfront_payment" not in features_found("Note: we never charge any registration fee.")


def test_whatsapp_contact_is_flagged_but_negated_warning_is_not():
    assert "offplatform_contact" in features_found("Send your CV on WhatsApp to 9876543210")
    assert "offplatform_contact" not in features_found("We will never contact you on WhatsApp.")


def test_no_interview_and_job_guarantee():
    assert "no_interview" in features_found("No interview. Direct joining.")
    assert "no_interview" in features_found("100% job guarantee for all applicants")


def test_sensitive_documents_requested():
    assert "sensitive_info_request" in features_found("Share your Aadhaar and PAN card to proceed")


def test_free_email_only_when_no_company_email():
    assert "free_email" in features_found("", ExtractedInfo(emails=["hr.jobs@gmail.com"]))
    assert "free_email" not in features_found("", ExtractedInfo(emails=["hr@gmail.com", "hr@acme.com"]))


def test_salary_far_above_reference_is_flagged():
    fresher_high_pay = ExtractedInfo(salary_monthly_inr=200_000, experience_min_years=0)
    assert "salary_too_high" in features_found("", fresher_high_pay)

    normal_pay = ExtractedInfo(salary_monthly_inr=30_000, experience_min_years=0)
    assert "salary_too_high" not in features_found("", normal_pay)


def test_clean_posting_has_no_flags():
    text = "We are hiring a backend developer. Two technical interview rounds. Apply on our careers page."
    assert features_found(text) == set()
