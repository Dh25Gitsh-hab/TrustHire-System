"""
weights.py — the numbers inside the trust-score model.

The model is logistic regression (research paper, Section V-B):

    trust probability = sigmoid( BIAS + sum of  WEIGHT[feature] x value )

  * a POSITIVE weight means the feature makes a posting MORE trustworthy,
  * a NEGATIVE weight means it makes it LESS trustworthy,
  * a bigger number means a stronger effect.

IMPORTANT: these are hand-set STARTING values chosen to be sensible, so the
whole system works end to end today. In the ML phase (timeline weeks 9-10)
they will be replaced by weights LEARNED from a labelled dataset, and an
XGBoost model will be compared against this one.
"""

# Starting point when there is no evidence at all: sigmoid(0.5) ≈ 62 / 100.
BIAS = 0.5

WEIGHTS = {
    # --- 1. Domain age (WHOIS) -----------------------------------------
    "domain_age": 0.6,  # value: about -3.3 (12-day-old domain) ... +2.3 (10-year-old)
    "domain_age_hidden": -0.3,  # weak: many genuine owners hide WHOIS data
    "domain_unregistered": -2.0,  # the posting's website does not exist
    "age_claim_mismatch": -1.5,  # "20 years in business" on a months-old domain
    # --- 5. Hiring-process red flags -----------------------------------
    "upfront_payment": -2.5,  # strongest sign: genuine jobs never charge candidates
    "offplatform_contact": -1.2,  # WhatsApp / Telegram instead of formal process
    "no_interview": -1.2,  # "direct joining", "100% job guarantee"
    "sensitive_info_request": -0.8,  # Aadhaar / PAN / bank details up front
    "free_email": -0.8,  # recruiter uses gmail.com etc.
    "salary_too_high": -0.8,  # value = log2(salary / reference); 2x reference -> -0.8
    # --- 2. Online reputation (web search + AI) --------------------------
    # value = min(independent websites with scam reports about this company, 3) / 3
    #   0 sites -> 0 (no effect), 1 -> -0.4, 2 -> -0.8, 3 or more -> -1.2.
    # Smaller than the old Reddit weight (-2.0) because search snippets are
    # unverified allegations labelled by an AI. Impersonation warnings do not
    # count. Gemini's own risk score is NOT a feature (see reputation_check.py).
    "web_scam_reports": -1.2,
    # --- 4. Company registration (MCA) ----------------------------------
    "registry_match": 0.8,  # a registered company with this exact name exists
    "incorporation_age": 0.3,  # same scale as domain_age, but weaker (names can be copied)
    "registry_inactive": -1.5,  # registered, but struck off / dormant / liquidated
    "registry_not_found": -0.5,  # weak: the name may simply be written differently
    # --- 3. Reviews: weights added when that check is connected ----------
}
