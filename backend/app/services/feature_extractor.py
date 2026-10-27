"""
feature_extractor.py — pulls the key facts out of a job posting's text.

What we look for:
  * company name            -> used by the reputation / review / registry checks
  * company website domain  -> used by the WHOIS domain-age check
  * e-mail addresses and Indian mobile numbers
  * salary (converted to rupees per month) and required experience
  * "established in 2005"-style claims -> compared with the domain's age

Everything here is plain pattern matching (regular expressions): fast, free
and easy to explain, but it can miss things. That is why the user may also
type the company name and website in directly — those always win.
"""

import re
from datetime import date
from urllib.parse import urlparse

from app.schemas import ExtractedInfo

# ------------------------------------------------------------------
# Reference lists
# ------------------------------------------------------------------

# Websites that HOST postings for many companies (job boards, applicant-
# tracking systems, social media, link shorteners). Their domain age says
# nothing about the hiring company, so we never use them for the WHOIS check.
JOB_PLATFORM_DOMAINS = {
    "linkedin.com", "naukri.com", "indeed.com", "internshala.com", "glassdoor.com",
    "glassdoor.co.in", "foundit.in", "monsterindia.com", "shine.com", "timesjobs.com",
    "wellfound.com", "angel.co", "apna.co", "instahyre.com", "hirist.tech", "iimjobs.com",
    "cutshort.io", "unstop.com", "freshersworld.com", "workindia.in", "quikr.com", "olx.in",
    "lever.co", "greenhouse.io", "myworkdayjobs.com", "smartrecruiters.com", "ashbyhq.com",
    "zohorecruit.com", "zohorecruit.in", "keka.com", "darwinbox.in", "freshteam.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "t.me",
    "telegram.me", "wa.me", "whatsapp.com", "google.com", "forms.gle", "bit.ly", "tinyurl.com",
}

# Free e-mail providers. A "company" recruiting from one of these is a warning sign.
FREE_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "yahoo.in", "ymail.com",
    "outlook.com", "hotmail.com", "live.com", "msn.com", "rediffmail.com", "aol.com",
    "icloud.com", "protonmail.com", "proton.me", "zoho.com", "zohomail.in", "mail.com",
    "gmx.com", "yandex.com",
}

# Two-part domain endings, needed to cut "careers.acme.co.in" down to "acme.co.in".
TWO_PART_SUFFIXES = {
    "co.in", "net.in", "org.in", "firm.in", "gen.in", "ind.in", "ac.in", "edu.in", "gov.in",
    "co.uk", "org.uk", "ac.uk", "com.au", "net.au", "co.nz", "com.sg", "com.my", "co.jp",
    "com.br", "co.za",
}

# Names that the patterns below sometimes catch but are not company names.
NOT_COMPANY_NAMES = {"we", "our company", "the company", "company", "urgent", "hiring", "our client", "client"}

# ------------------------------------------------------------------
# Regular expressions
# ------------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'()]+", re.IGNORECASE)
# Indian mobile numbers: 10 digits starting with 6-9, optional +91 / 0 prefix.
PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")

# Company name patterns, tried in this order:
#   "Company: Acme Pvt Ltd"
COMPANY_LABEL_RE = re.compile(
    r"^\s*(?:company(?:\s+name)?|organi[sz]ation|employer|hiring\s+company)\s*[:\-–]\s*(?P<name>.{2,80})$",
    re.IGNORECASE | re.MULTILINE,
)
#   "Acme Technologies is hiring"
#   ([ \t]+ instead of \s+ keeps a name on one line)
HIRING_RE = re.compile(
    r"(?P<name>[A-Z][\w&.'-]*(?:[ \t]+[A-Z][\w&.'-]*){0,4})[ \t]+(?:is|are)[ \t]+(?:hiring|looking\s+for|seeking|recruiting)"
)
#   "... Brightpath Global Solutions ..." (capitalised words ending in a business word).
#   The last lookahead rejects job titles such as "Customer Services Executive",
#   where another capitalised word follows the business word.
LEGAL_NAME_RE = re.compile(
    r"(?P<name>[A-Z][\w&'-]*(?:[ \t]+[A-Z][\w&.'-]*){0,4}[ \t]+"
    r"(?:Pvt\.?[ \t]*Ltd\.?|Private[ \t]+Limited|Limited|Ltd\.?|LLP|Inc\.?|Technologies|Solutions|"
    r"Services|Infotech|Infosystems|Consultancy|Consultants|Corporation|Corp\.?|"
    r"Enterprises|Industries|Systems|Labs))(?!\w)(?![ \t]+[A-Z])"
)

# Salary: an amount like "Rs. 25,000", "₹40k", "3.5 LPA" or "25000 - 30000".
SALARY_AMOUNT_RE = re.compile(
    r"(?P<currency>₹|\brs\.?|\binr)?\s*"
    r"(?P<low>\d[\d,]*(?:\.\d+)?)\s*(?P<low_unit>k\b|lakhs?|lacs?|lpa|l\b)?"
    r"(?:\s*(?:-|–|to)\s*(?:₹|rs\.?|inr)?\s*(?P<high>\d[\d,]*(?:\.\d+)?)\s*(?P<high_unit>k\b|lakhs?|lacs?|lpa|l\b)?)?",
    re.IGNORECASE,
)
# The time period written just after an amount: "per month", "/day", "p.a." ...
SALARY_PERIOD_RE = re.compile(
    r"^\s*(?:/-)?\s*(?:/|per|a|an|every|p\.?)?\s*"
    r"(?P<period>month|mon|mo|day|daily|week|weekly|hour|hr|year|yr|annum|annually|a\.?\b|m\.?\b)",
    re.IGNORECASE,
)
# Words that tell us a number is a salary (used when there is no ₹ sign)...
SALARY_WORDS_RE = re.compile(r"salary|stipend|ctc|package|pay\b|earn|income|compensation|remuneration", re.IGNORECASE)
# ...and words that tell us it is a FEE, not a salary.
FEE_WORDS_RE = re.compile(r"fee|deposit|charge|registration", re.IGNORECASE)

# How many times per month each period is paid.
# A "day" is counted as 26 working days (6-day week, common in India).
MONTHLY_MULTIPLIER = {"hour": 8 * 26, "day": 26, "week": 4.33, "month": 1, "year": 1 / 12}

# Experience: "Freshers", "0-1 years", "3+ years of experience", "Experience: 2-5 yrs".
FRESHER_RE = re.compile(
    r"\b(?:freshers?|no\s+(?:prior\s+)?experience|entry[\s-]level|0\s*(?:-|–|to)\s*\d+\s*(?:years?|yrs?))\b",
    re.IGNORECASE,
)
EXPERIENCE_RE = re.compile(
    r"(?P<years>\d+(?:\.\d+)?)\s*\+?\s*(?:(?:-|–|to)\s*\d+(?:\.\d+)?\s*)?(?:years?|yrs?)"
    r"(?:\s+of)?(?:\s+\w+){0,3}?\s+(?:experience|exp)\b"
    r"|(?:experience|exp)\s*[:\-–]?\s*(?P<years2>\d+(?:\.\d+)?)\s*\+?\s*(?:(?:-|–|to)\s*\d+\s*)?(?:years?|yrs?)",
    re.IGNORECASE,
)

# "Established in 2005", "founded in 1998", "since 2010"
FOUNDED_YEAR_RE = re.compile(
    r"(?:established|founded|incorporated|started|in\s+business|operating)\s+(?:in|since)?\s*((?:19|20)\d{2})\b"
    r"|\bsince\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
# "25 years of excellence", "15+ years in business"
YEARS_IN_BUSINESS_RE = re.compile(
    r"(\d{1,3})\+?\s*years?\s+(?:of\s+)?(?:excellence|in\s+business|of\s+service|of\s+trust|legacy|track\s+record)",
    re.IGNORECASE,
)


# ------------------------------------------------------------------
# Main function
# ------------------------------------------------------------------
def extract_info(
    text: str,
    posting_url: str | None = None,
    structured: dict | None = None,
    company_name: str | None = None,
    company_website: str | None = None,
) -> ExtractedInfo:
    """
    Build an ExtractedInfo from the posting.

    Priority for every field: what the user typed > structured page data > text patterns.
    """
    structured = structured or {}
    emails = _unique(EMAIL_RE.findall(text))
    phones = _unique(match.group(0).strip() for match in PHONE_RE.finditer(text))

    domain, domain_source = _choose_domain(text, emails, posting_url, structured, company_website)

    name = (
        _clean_name(company_name)
        or _clean_name(structured.get("company_name"))
        or find_company_name(text)
        or _name_from_domain(domain)
    )

    salary_text, salary_monthly = parse_salary(structured.get("salary_text") or "")
    if salary_monthly is None:
        salary_text, salary_monthly = parse_salary(text)

    return ExtractedInfo(
        company_name=name,
        website_domain=domain,
        domain_source=domain_source,
        emails=emails,
        phone_numbers=phones,
        salary_text=salary_text,
        salary_monthly_inr=salary_monthly,
        experience_min_years=parse_experience(text),
        claimed_years_in_business=parse_claimed_years(text),
    )


# ------------------------------------------------------------------
# Domains
# ------------------------------------------------------------------
def registrable_domain(host: str) -> str:
    """'careers.acme.co.in' -> 'acme.co.in', 'www.acme.com' -> 'acme.com'."""
    host = host.lower().strip().rstrip(".")
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in TWO_PART_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def domain_from_url(url: str) -> str | None:
    """Return the registrable domain of a link, or None if it is not a valid link."""
    if "://" not in url:
        url = "http://" + url
    host = urlparse(url).hostname
    if not host or "." not in host:
        return None
    return registrable_domain(host)


def _choose_domain(text, emails, posting_url, structured, company_website) -> tuple[str | None, str | None]:
    """
    Decide which domain represents the hiring company. Checked in order:
      1. the website the user typed in
      2. the company website from the page's structured data
      3. the first non-job-board link in the text
      4. the first company (non-free) e-mail domain
      5. the posting link itself, if it is not on a job board
    """
    candidates = [
        (company_website, "website you entered"),
        (structured.get("company_website"), "company website on the posting page"),
    ]
    candidates += [(url, "website mentioned in the posting") for url in URL_RE.findall(text)]
    candidates += [(email.split("@")[1], "recruiter e-mail address") for email in emails]
    candidates.append((posting_url, "posting link"))

    for value, source in candidates:
        if not value:
            continue
        domain = domain_from_url(value.strip().rstrip(".,;"))
        if domain and domain not in JOB_PLATFORM_DOMAINS and domain not in FREE_EMAIL_DOMAINS:
            return domain, source
    return None, None


# ------------------------------------------------------------------
# Company name
# ------------------------------------------------------------------
def find_company_name(text: str) -> str | None:
    """Try the company-name patterns one by one and return the first good hit."""
    for pattern in (COMPANY_LABEL_RE, HIRING_RE, LEGAL_NAME_RE):
        for match in pattern.finditer(text):
            name = _clean_name(match.group("name"))
            if name:
                return name
    return None


def _clean_name(name: str | None) -> str | None:
    """Trim spaces/punctuation and reject generic words like 'We' or 'Hiring'."""
    if not name:
        return None
    name = " ".join(name.split()).strip(" ,;:-–|")
    if len(name) < 2 or name.lower() in NOT_COMPANY_NAMES:
        return None
    return name[:80]


def _name_from_domain(domain: str | None) -> str | None:
    """Last resort: 'brightpath-global.com' -> 'Brightpath Global'."""
    if not domain:
        return None
    label = domain.split(".")[0]
    return " ".join(word.capitalize() for word in re.split(r"[-_]", label) if word) or None


# ------------------------------------------------------------------
# Salary
# ------------------------------------------------------------------
def parse_salary(text: str) -> tuple[str | None, float | None]:
    """
    Find the highest salary mentioned and convert it to rupees per month.

    Returns (salary as written, monthly amount) or (None, None).
    Rules that keep this from grabbing random numbers:
      * the amount must have a ₹/Rs/INR sign, a lakh/LPA unit, or a salary
        word (salary, stipend, CTC, earn ...) shortly before it;
      * amounts right after fee words (fee, deposit, registration) are fees, not salary;
      * digits that belong to a phone number are ignored.
    """
    best_text, best_monthly = None, None
    phone_spans = [match.span() for match in PHONE_RE.finditer(text)]

    for match in SALARY_AMOUNT_RE.finditer(text):
        number_start = match.start("low")
        if any(start <= number_start < end for start, end in phone_spans):
            continue

        before = text[max(0, match.start() - 40) : match.start()]
        after = text[match.end() : match.end() + 20]
        unit = (match.group("high_unit") or match.group("low_unit") or "").lower()
        has_lakh_unit = unit.startswith("l")

        looks_like_salary = match.group("currency") or has_lakh_unit or SALARY_WORDS_RE.search(before)
        if not looks_like_salary or FEE_WORDS_RE.search(before[-30:]):
            continue

        amount = _to_number(match.group("high") or match.group("low"), unit)
        if amount is None or amount < 100:
            continue

        period = _salary_period(after, unit, amount)
        monthly = round(amount * MONTHLY_MULTIPLIER[period])
        if best_monthly is None or monthly > best_monthly:
            # Keep the salary exactly as written in the posting, period included.
            period_match = SALARY_PERIOD_RE.match(after)
            end = match.end() + (period_match.end() if period_match else 0)
            best_text, best_monthly = text[match.start() : end].strip(), monthly

    return best_text, best_monthly


def _to_number(raw: str | None, unit: str) -> float | None:
    """'1,50,000' -> 150000; '40' with unit 'k' -> 40000; '3.5' with 'lpa' -> 350000."""
    if not raw:
        return None
    try:
        value = float(raw.replace(",", ""))
    except ValueError:
        return None
    if unit == "k":
        value *= 1_000
    elif unit.startswith("l"):  # lakh / lac / LPA / L
        value *= 100_000
    return value


def _salary_period(after: str, unit: str, amount: float) -> str:
    """Work out if an amount is per hour/day/week/month/year."""
    match = SALARY_PERIOD_RE.match(after)
    word = match.group("period").lower() if match else ""

    if word.startswith("h"):
        return "hour"
    if word.startswith("d"):
        return "day"
    if word.startswith("w"):
        return "week"
    if word.startswith("m"):
        return "month"
    if word.startswith(("y", "a")) or unit == "lpa":
        return "year"
    # No period written: lakh amounts and anything >= 1,00,000 are usually yearly CTC.
    if unit.startswith("l") or amount >= 100_000:
        return "year"
    return "month"


# ------------------------------------------------------------------
# Experience and company-age claims
# ------------------------------------------------------------------
def parse_experience(text: str) -> float | None:
    """Minimum years of experience asked for (0 for freshers), or None if not stated."""
    if FRESHER_RE.search(text):
        return 0.0
    years = [
        float(match.group("years") or match.group("years2"))
        for match in EXPERIENCE_RE.finditer(text)
    ]
    return min(years) if years else None


def parse_claimed_years(text: str) -> int | None:
    """How many years in business the posting claims ('established in 2005' -> ~21)."""
    this_year = date.today().year
    claims = []
    for match in FOUNDED_YEAR_RE.finditer(text):
        year = int(match.group(1) or match.group(2))
        if 1900 <= year <= this_year:
            claims.append(this_year - year)
    for match in YEARS_IN_BUSINESS_RE.finditer(text):
        claims.append(int(match.group(1)))
    return max(claims) if claims else None


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------
def _unique(items) -> list[str]:
    """Remove duplicates but keep the original order."""
    seen, result = set(), []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
