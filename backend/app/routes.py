"""
routes.py — the API endpoints (URLs) the frontend calls.

  GET  /api/health    -> quick "is the server running?" check
  POST /api/analyze   -> analyse one job posting and return the trust report
  POST /api/reports   -> user feedback: "this posting was a scam / genuine"
"""

from fastapi import APIRouter, HTTPException

from app import database
from app.schemas import AnalyzeRequest, AnalyzeResponse, ReportRequest
from app.services import gemini_client, web_search
from app.services.analyzer import analyze_posting
from app.services.posting_fetcher import PostingFetchError

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    """Is the server running, and which optional services are connected? (Never shows keys.)"""

    def state(configured: bool) -> str:
        return "configured" if configured else "not configured"

    return {
        "status": "ok",
        "database": state(database.is_configured()),
        "web_search": state(web_search.is_configured()),
        "ai_analysis": state(gemini_client.is_configured()),
    }


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    """
    Analyse a job posting (pasted text and/or a link) and return the trust
    score, the reasons behind it, and the result of every verification check.

    This is a normal (non-async) function on purpose: FastAPI runs it in a
    worker thread, so slow WHOIS / network calls do not block other users.
    """
    try:
        return analyze_posting(request)
    except PostingFetchError as error:
        # The link could not be read — tell the user why (e.g. LinkedIn login wall).
        raise HTTPException(status_code=422, detail=str(error))


@router.post("/reports")
def report(request: ReportRequest):
    """Save the user's feedback on an analysis (future training data for the model)."""
    if not database.is_configured():
        raise HTTPException(status_code=503, detail="Reports are not available: the database is not connected.")
    if not database.save_report(request):
        raise HTTPException(status_code=502, detail="Your report could not be saved right now. Please try again.")
    return {"saved": True}
