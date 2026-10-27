"""
trust_score.py — combines all signals into one score from 1 to 99, with reasons.

How it works (logistic regression, research paper Sections V-B and V-C):

  1. Every signal from every completed check has a feature name and a value.
  2. impact = WEIGHT[feature] x value       (+ raises trust, - lowers trust)
  3. z      = BIAS + sum of all impacts
  4. trust  = sigmoid(z) = 1 / (1 + e^-z)   -> a probability between 0 and 1
  5. score  = trust x 100, kept between 1 and 99 (the tool is never 100% sure)

Because each impact is simply weight x value, the explanation is exact:
the reasons list shows precisely how much each signal moved the score.
"""

import math
from dataclasses import dataclass

from app.schemas import CheckResult, Reason
from app.scoring.weights import BIAS, WEIGHTS

# Score bands. These will be re-tuned on a validation set in the ML phase.
HIGH_TRUST_FROM = 70
MEDIUM_TRUST_FROM = 40

VERDICTS = {
    "high": "No major warning signs were found. It looks genuine, but still never pay money to get a job.",
    "medium": "Some warning signs or missing information. Verify the company yourself before sharing personal details.",
    "low": "Strong warning signs of a job scam. Do not pay any money or share documents with this recruiter.",
}
NO_EVIDENCE_VERDICT = (
    "We could not find enough information to judge this posting. "
    "Add the company name or website, or use the manual links to verify it yourself."
)


@dataclass
class TrustScore:
    score: int
    level: str
    verdict: str
    reasons: list[Reason]


def calculate_trust_score(checks: list[CheckResult]) -> TrustScore:
    reasons: list[Reason] = []

    # Steps 1 + 2: turn every signal into an impact on the score.
    for check in checks:
        if check.status != "completed":
            continue  # skipped / not connected / failed checks add nothing
        for signal in check.signals:
            weight = WEIGHTS.get(signal.feature)
            if weight is None:
                continue  # a feature the model does not know (yet)
            impact = round(weight * signal.value, 3)
            if abs(impact) < 0.05:
                continue  # too small to be worth showing
            reasons.append(Reason(
                feature=signal.feature,
                message=signal.message,
                impact=impact,
                effect="raises_trust" if impact > 0 else "lowers_trust",
            ))

    # Steps 3 + 4 + 5: logistic formula.
    z = BIAS + sum(reason.impact for reason in reasons)
    z = max(-30.0, min(30.0, z))  # keeps math.exp() from overflowing on absurd inputs
    probability = 1 / (1 + math.exp(-z))
    score = min(99, max(1, round(probability * 100)))

    level = "high" if score >= HIGH_TRUST_FROM else "medium" if score >= MEDIUM_TRUST_FROM else "low"
    verdict = VERDICTS[level] if reasons else NO_EVIDENCE_VERDICT

    # Strongest reasons first, so the user reads the most important ones.
    reasons.sort(key=lambda reason: abs(reason.impact), reverse=True)
    return TrustScore(score=score, level=level, verdict=verdict, reasons=reasons)
