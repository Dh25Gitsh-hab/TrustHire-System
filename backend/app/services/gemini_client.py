"""
gemini_client.py — sends one prompt to Google's Gemini API and returns its JSON answer.

We call Gemini's official REST endpoint with `requests` (the library the rest
of the backend already uses), so no extra package is needed:

    POST https://generativelanguage.googleapis.com/v1beta/models/<GEMINI_MODEL>:generateContent
    header  x-goog-api-key: <GEMINI_API_KEY>       (the key is never put in the URL)

"responseMimeType: application/json" + "responseSchema" ask Gemini to answer
in our JSON shape. We still check every answer ourselves in
evidence_analyzer.py, because a model can make mistakes.

FREE TIER ONLY: the key comes from AI Studio with no billing set up, and
GEMINI_MODEL must be a model the free tier offers. When the free limit is
reached Google answers HTTP 429 — we then report "AI analysis unavailable".
We never switch to a different (possibly paid) model by ourselves.
"""

import json
import logging

import requests

from app import config

logger = logging.getLogger("trusthire.gemini")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(Exception):
    """
    The AI call failed. The message is safe to show users.
    `retryable` = a second try could help (e.g. a malformed answer), as
    opposed to a used-up quota or a wrong key, where retrying only wastes requests.
    """

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def is_configured() -> bool:
    return bool(config.GEMINI_API_KEY and config.GEMINI_MODEL)


def generate_json(system_instruction: str, prompt: str, response_schema: dict) -> dict:
    """Ask Gemini and return its answer as a Python dict."""
    body = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }
    if config.GEMINI_THINKING_LEVEL:
        # Less "thinking" = a faster answer (and fewer tokens used).
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": config.GEMINI_THINKING_LEVEL}
    return parse_json_answer(call_gemini(body))


def call_gemini(body: dict) -> dict:
    """Send the request and return Gemini's raw reply. Kept separate so tests can replace it."""
    try:
        response = requests.post(
            GEMINI_URL.format(model=config.GEMINI_MODEL),
            json=body,
            headers={"x-goog-api-key": config.GEMINI_API_KEY},
            timeout=config.GEMINI_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        raise GeminiError("the AI took too long to answer") from None
    except requests.RequestException as error:
        logger.warning("Gemini request failed (%s)", type(error).__name__)
        raise GeminiError("the AI service could not be reached") from None

    status = response.status_code
    if status == 429:
        raise GeminiError("the free AI limit is used up for now (per-minute or daily limit)")
    if status in (401, 403) or (status == 400 and "API_KEY_INVALID" in response.text):
        logger.warning("Gemini rejected the API key (HTTP %s)", status)
        raise GeminiError("the AI service rejected the server's API key")
    if status == 404:
        raise GeminiError("the AI model set in GEMINI_MODEL is not available to this account")
    if status >= 500:
        raise GeminiError(f"the AI service had a temporary problem (error {status})", retryable=True)
    if status != 200:
        raise GeminiError(f"the AI service refused the request (error {status})")

    try:
        return response.json()
    except ValueError:
        raise GeminiError("the AI service sent an unreadable reply", retryable=True) from None


def parse_json_answer(data: dict) -> dict:
    """Take the JSON text out of Gemini's reply and turn it into a dict."""
    if not isinstance(data, dict):
        raise GeminiError("the AI service sent an unreadable reply", retryable=True)
    if (data.get("promptFeedback") or {}).get("blockReason"):
        raise GeminiError("the AI declined to analyse this content")

    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiError("the AI returned no answer", retryable=True)
    candidate = candidates[0]
    if candidate.get("finishReason") not in (None, "STOP"):
        # e.g. SAFETY or MAX_TOKENS: the answer is missing or cut off.
        raise GeminiError("the AI did not finish its answer")

    # "Thinking" models can add thought parts; only the normal text is the answer.
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts if not part.get("thought"))
    try:
        answer = json.loads(text)
    except ValueError:
        raise GeminiError("the AI's answer was not valid JSON", retryable=True) from None
    if not isinstance(answer, dict):
        raise GeminiError("the AI's answer was not in the expected format", retryable=True)
    return answer
