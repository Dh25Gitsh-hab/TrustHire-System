"""Tests for app/services/feature_extractor.py — pulling facts out of posting text."""

from app.services.feature_extractor import (
    extract_info,
    find_company_name,
    parse_claimed_years,
    parse_experience,
    parse_salary,
    registrable_domain,
)


# ---------------- Salary ----------------
def test_salary_per_day_is_converted_to_monthly():
    text, monthly = parse_salary("Earn Rs. 3,000 per day from home")
    assert text == "Rs. 3,000 per day"
    assert monthly == 3_000 * 26  # 26 working days


def test_salary_lpa_range_uses_upper_value():
    _, monthly = parse_salary("CTC 3.5 - 4.5 LPA")
    assert monthly == round(450_000 / 12)


def test_salary_k_suffix():
    assert parse_salary("Rs 40k/month") == ("Rs 40k/month", 40_000)


def test_fee_amount_is_not_a_salary():
    assert parse_salary("Pay a registration fee of Rs. 999") == (None, None)


def test_phone_number_is_not_a_salary():
    assert parse_salary("Salary discussed on call: 98765 43210") == (None, None)


# ---------------- Experience & company age ----------------
def test_experience():
    assert parse_experience("Freshers can apply") == 0
    assert parse_experience("3+ years of relevant experience") == 3
    assert parse_experience("Experience: 2-5 yrs") == 2
    assert parse_experience("Great team culture") is None


def test_claimed_years_in_business():
    assert parse_claimed_years("Established in 2005") is not None
    assert parse_claimed_years("25 years of excellence") == 25
    assert parse_claimed_years("We build software") is None


# ---------------- Company name & domain ----------------
def test_company_name_patterns():
    assert find_company_name("Company: Zenith Infotech\nRole: Analyst") == "Zenith Infotech"
    assert find_company_name("Acme Analytics is hiring interns") == "Acme Analytics"
    assert find_company_name("Executive at Nova Retail Services") == "Nova Retail Services"


def test_job_titles_are_not_company_names():
    assert find_company_name("Senior Software Engineer needed") is None


def test_registrable_domain():
    assert registrable_domain("careers.acme.co.in") == "acme.co.in"
    assert registrable_domain("www.acme.com") == "acme.com"


def test_domain_prefers_company_email_and_skips_free_email():
    info = extract_info("Write to jobs@gmail.com or hr@acme-tech.in")
    assert info.website_domain == "acme-tech.in"
    assert info.domain_source == "recruiter e-mail address"


def test_job_board_link_is_not_the_company_domain():
    info = extract_info("Some posting text", posting_url="https://www.naukri.com/job-listings-123")
    assert info.website_domain is None


def test_user_supplied_values_win():
    info = extract_info(
        "Acme Analytics is hiring. Write to hr@acme.com",
        company_name="Real Name Ltd",
        company_website="https://www.realname.in",
    )
    assert info.company_name == "Real Name Ltd"
    assert info.website_domain == "realname.in"
