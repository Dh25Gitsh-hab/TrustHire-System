"""
check_services.py — checks the SerpApi and Gemini keys in backend/.env
WITHOUT spending any of the free search or AI quota.

  * SerpApi: asks the Account API (free, not counted) for the plan and searches left.
  * Gemini:  asks for the list of models (free, no text is generated) and
             checks that GEMINI_MODEL is in it.

Run it from the backend folder:

    python check_services.py

It never prints the keys themselves.
"""

import requests

from app import config

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def check_serpapi() -> None:
    print("SerpApi (web search)")
    if not config.SERPAPI_API_KEY:
        print("  not configured: add SERPAPI_API_KEY to backend/.env")
        return
    try:
        response = requests.get(
            "https://serpapi.com/account.json",
            params={"api_key": config.SERPAPI_API_KEY},
            timeout=config.HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        print(f"  could not reach serpapi.com ({type(error).__name__})")  # never print the URL: it has the key
        return
    if response.status_code != 200:
        print(f"  key NOT accepted (HTTP {response.status_code})")
        return
    account = response.json()
    # Only these fields are shown (the reply also contains the key and the account e-mail).
    print(f"  key works - plan: {account.get('plan_name')}")
    print(f"  searches left this month: {account.get('total_searches_left')} of {account.get('searches_per_month')}")
    print(f"  hourly limit: {account.get('account_rate_limit_per_hour')}, used this hour: {account.get('this_hour_searches')}")


def check_gemini() -> None:
    print("Gemini (AI analysis)")
    if not config.GEMINI_API_KEY:
        print("  not configured: add GEMINI_API_KEY to backend/.env")
        return
    if not config.GEMINI_MODEL:
        print("  GEMINI_MODEL is empty: add e.g. GEMINI_MODEL=gemini-3.5-flash-lite to backend/.env")
        return

    names, page_token = set(), None
    while True:  # the list comes in pages
        params = {"pageSize": 1000, **({"pageToken": page_token} if page_token else {})}
        try:
            response = requests.get(GEMINI_MODELS_URL, params=params,
                                    headers={"x-goog-api-key": config.GEMINI_API_KEY},
                                    timeout=config.HTTP_TIMEOUT_SECONDS)
        except requests.RequestException as error:
            print(f"  could not reach Google ({type(error).__name__})")
            return
        if response.status_code != 200:
            print(f"  key NOT accepted (HTTP {response.status_code})")
            return
        data = response.json()
        for model in data.get("models", []):
            if "generateContent" in model.get("supportedGenerationMethods", []):
                names.add(model.get("name", "").removeprefix("models/"))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    print("  key works")
    if config.GEMINI_MODEL in names:
        print(f"  model '{config.GEMINI_MODEL}' is available to this key")
    else:
        print(f"  model '{config.GEMINI_MODEL}' was NOT found for this key. Models you can use:")
        for name in sorted(names):
            print(f"    {name}")
    print("  (free-tier limits for your account are shown in AI Studio - this script cannot see them)")


if __name__ == "__main__":
    check_serpapi()
    print()
    check_gemini()
