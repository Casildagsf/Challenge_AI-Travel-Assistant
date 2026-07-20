"""FastAPI wrapper around travel_assistant.py.

The Gradio app (app.py) and this API call the exact same functions. Gradio holds
them in one process; this exposes them over HTTP so a React front end can use
them from anywhere.

Run locally:
    uvicorn api.main:app --reload
Then open http://localhost:8000/docs

Deployed on Render with:
    build:  pip install -r requirements-api.txt
    start:  uvicorn api.main:app --host 0.0.0.0 --port $PORT
"""
import os
import secrets
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# travel_assistant.py sits one level up, next to app.py. Make it importable
# whether uvicorn is started from the repo root or from inside api/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Local runs only: pick up .env.local so OPENAI_API_KEY is set before
# travel_assistant imports (it builds the OpenAI client at import time).
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")
except ImportError:
    pass

import travel_assistant as ta

app = FastAPI(
    title="AI Travel Advisor API",
    description="Plans a trip against real weather, currency and transport data.",
    version="0.1.0",
)

# The browser blocks a page on vercel.app from calling an api on onrender.com
# unless the API says it is allowed. Set ALLOWED_ORIGINS on Render once the
# front end has a URL; "*" is fine while nothing secret is behind it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------
# /plan spends real money on every call, so it is not open to the internet.
# Callers must send the shared secret as an X-API-Key header. This is exactly
# what OpenAI does to us: a secret in a header, checked before any work starts.
def require_api_key(x_api_key: str | None = Header(default=None)):
    expected = os.environ.get("APP_API_KEY")
    if not expected:
        # Refuse to serve rather than silently running unprotected. /health
        # stays up, so a deploy in this state is still diagnosable.
        raise HTTPException(
            status_code=503,
            detail="APP_API_KEY is not set on the server; /plan is disabled.",
        )
    # compare_digest, not ==, so the comparison time does not leak the secret.
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key.")


# ---------------------------------------------------------------------------
# request / response shapes
# ---------------------------------------------------------------------------
# These mirror the RECAP object the collector prompt produces in
# travel_assistant.COLLECTOR_SYSTEM, so no translation is needed.
class TripRequest(BaseModel):
    destination: str = Field(..., examples=["Andalusia"])
    country: str = Field(..., description="English country name", examples=["Spain"])
    days: int = Field(..., gt=0, le=30)
    nights_per_city: dict[str, int] = Field(
        ..., description="City or town -> nights slept there",
        examples=[{"Seville": 3, "Granada": 2}],
    )
    inter_city_transport: str = Field("train", examples=["train"])
    month: str = Field(..., examples=["September"])
    interests: list[str] = Field(default_factory=list,
                                 examples=[["food", "history", "flamenco"]])
    constraints: str = Field("", examples=["travelling with a 7-year-old"])


class TripResponse(BaseModel):
    itinerary_markdown: str
    summary: dict
    facts: dict
    usage: list
    cost_report_markdown: str
    # Numbers, not markdown: the front end should never have to parse a table
    # to show a total.
    total_tokens: int
    cost_usd: float
    cost_eur: float


def _cost(usage):
    """Same arithmetic as travel_assistant.usage_report_md, but as numbers."""
    tokens = sum(r["input"] + r["output"] for r in usage)
    usd = sum(
        r["input"] / 1e6 * ta.PRICES[r["model"]]["input"]
        + r["output"] / 1e6 * ta.PRICES[r["model"]]["output"]
        for r in usage if r["model"] in ta.PRICES
    )
    return tokens, round(usd, 4), round(usd * ta.EUR_PER_USD, 4)


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    """A bare URL should explain itself rather than 404."""
    return {"service": "AI Travel Advisor API",
            "docs": "/docs", "health": "/health", "plan": "POST /plan"}


@app.get("/health")
def health():
    """Cheap endpoint that touches no models. Use it to check a deploy is alive."""
    return {"status": "ok"}


@app.post("/plan", response_model=TripResponse,
          dependencies=[Depends(require_api_key)])
def plan(trip: TripRequest):
    """Full planning run: real-world facts, then a day-by-day itinerary.

    Takes 30-60s and costs real money. No images in this version.
    """
    recap = trip.model_dump()
    usage = []  # one per request, so concurrent users never share a tally

    try:
        facts = ta.gather_facts(recap, usage)
        itinerary = ta.build_itinerary(recap, facts, usage)
        summary = ta.summarise(itinerary, usage)
    except Exception as e:
        # Surface the real reason. Render's logs will show the traceback too.
        raise HTTPException(status_code=502,
                            detail=f"{type(e).__name__}: {e}") from e

    tokens, usd, eur = _cost(usage)
    return TripResponse(
        itinerary_markdown=itinerary,
        summary=summary,
        facts=facts,
        usage=usage,
        cost_report_markdown=ta.usage_report_md(usage),
        total_tokens=tokens,
        cost_usd=usd,
        cost_eur=eur,
    )
