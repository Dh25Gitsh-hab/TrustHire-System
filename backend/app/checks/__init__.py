"""
checks — one module per verification signal family (see the research paper,
Section IV, and Fig. 4.2 of the synopsis):

  domain_check       1. Domain age (WHOIS)                  -> LIVE (no key needed)
  reputation_check   2. Web reputation (SerpApi + Gemini)   -> LIVE once both keys are in .env
  review_check       3. Glassdoor / AmbitionBox reviews      -> manual links only
  registry_check     4. MCA registration (data.gov.in)       -> LIVE with DATAGOVIN_API_KEY
  red_flags          5. Hiring-process red flags (rules)     -> LIVE (no key needed)

Every module follows the same contract, which keeps them easy to add and test:

    run(info: ExtractedInfo, text: str) -> CheckResult

The CheckResult carries "signals" — numbers + plain-language messages — that
the trust-score model (app/scoring) turns into the final score.
"""
