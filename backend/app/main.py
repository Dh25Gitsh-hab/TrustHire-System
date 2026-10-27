"""
main.py — starting point of the TrustHire backend.

Run the server (from the backend folder):
    uvicorn app.main:app --reload

Then open http://localhost:8000/docs to try the API in the browser.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.routes import router

app = FastAPI(
    title="TrustHire API",
    description="Verifies the company behind a job posting and returns an explainable trust score.",
    version="0.1.0",
)

# CORS: allows the React frontend (a different address/port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# All endpoints live in routes.py under the /api prefix.
app.include_router(router)


@app.get("/")
def root():
    return {"name": "TrustHire API", "docs": "/docs", "health": "/api/health"}
