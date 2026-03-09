import asyncio
import sys

import subprocess
import os

# Install Playwright browsers at startup if not present
chromium_path = "/opt/render/.cache/ms-playwright/chromium-1117/chrome-linux/chrome"
if not os.path.exists(chromium_path):
    subprocess.run(["playwright", "install", "chromium"], check=True)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

"""
main.py — FastAPI application entry point.

Routes:
  GET  /          → Homepage with search form
  POST /search    → Trigger scrape, score results, render table
  GET  /status    → Simple health-check endpoint
"""

import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scraper import scrape_google_maps
from utils import (
    build_summary,
    calculate_opportunity_score,
    clean_phone,
    clean_rating,
    clean_reviews,
    safe_text,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent

app = FastAPI(title="Maps Lead Finder", version="1.0.0")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Render the homepage with an empty search form."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "results": [],
            "summary": None,
            "query": "",
            "error": None,
            "loading": False,
        },
    )


@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    """
    1. Validate the query.
    2. Run the Playwright scraper.
    3. Clean & score every business.
    4. Build summary stats.
    5. Render the results table.
    """
    query = query.strip()
    if not query:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "results": [],
                "summary": None,
                "query": query,
                "error": "Please enter a search query.",
                "loading": False,
            },
        )

    logger.info(f"Search request: '{query}'")

    try:
        # ------------------------------------------------------------------
        # Scrape Google Maps
        # ------------------------------------------------------------------
        raw_businesses = await scrape_google_maps(query)

        if not raw_businesses:
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "results": [],
                    "summary": {"total": 0, "no_website": 0, "highest_score": 0},
                    "query": query,
                    "error": "No businesses found. Try a different search query.",
                    "loading": False,
                },
            )

        # ------------------------------------------------------------------
        # Clean data with Pandas
        # ------------------------------------------------------------------
        df = pd.DataFrame(raw_businesses)

        # Normalise columns
        df["name"]    = df["name"].apply(lambda v: safe_text(v, "Unknown"))
        df["phone"]   = df["phone"].apply(lambda v: clean_phone(safe_text(v)))
        df["address"] = df["address"].apply(lambda v: safe_text(v))
        df["rating"]  = df["rating"].apply(
            lambda v: clean_rating(str(v)) if v is not None else None
        )
        df["reviews"] = df["reviews"].apply(
            lambda v: clean_reviews(str(v)) if v else 0
        )
        df["website"] = df["website"].apply(lambda v: safe_text(v))
        df["maps_url"] = df["maps_url"].apply(lambda v: safe_text(v))

        # Convert back to list of dicts for scoring
        businesses = df.to_dict(orient="records")

        # ------------------------------------------------------------------
        # Score every business
        # ------------------------------------------------------------------
        scored = [calculate_opportunity_score(b) for b in businesses]

        # Sort by score descending so the best leads appear first
        scored.sort(key=lambda b: b["score"], reverse=True)

        # ------------------------------------------------------------------
        # Summary stats
        # ------------------------------------------------------------------
        summary = build_summary(scored)
        logger.info(
            f"Done — {summary['total']} businesses, "
            f"{summary['no_website']} without websites, "
            f"top score: {summary['highest_score']}"
        )

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "results": scored,
                "summary": summary,
                "query": query,
                "error": None,
                "loading": False,
            },
        )

    except Exception as exc:
        logger.error(f"Search failed: {exc}", exc_info=True)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "results": [],
                "summary": None,
                "query": query,
                "error": f"An error occurred during scraping: {str(exc)}",
                "loading": False,
            },
        )


@app.get("/health")
async def health():
    """Simple health-check for Render / uptime monitors."""
    return {"status": "ok"}
