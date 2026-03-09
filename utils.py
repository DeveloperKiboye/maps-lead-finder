"""
utils.py — Helper functions for lead scoring, data cleaning, and safe extraction.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Safe element extraction
# ---------------------------------------------------------------------------

def safe_text(value: Optional[str], fallback: str = "") -> str:
    """Return stripped text or fallback if value is None / empty."""
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def clean_phone(phone: str) -> str:
    """Normalize phone numbers — keep digits, +, spaces, and dashes."""
    if not phone:
        return ""
    # Remove everything except digits, +, spaces, dashes, parentheses
    cleaned = re.sub(r"[^\d\+\s\-\(\)]", "", phone).strip()
    return cleaned if len(cleaned) >= 7 else ""


def clean_rating(rating: str) -> Optional[float]:
    """Parse a rating string like '4.5' or '4,5' to float."""
    if not rating:
        return None
    try:
        return float(rating.replace(",", "."))
    except ValueError:
        return None


def clean_reviews(reviews: str) -> int:
    """Parse review count — strips commas, parentheses, etc."""
    if not reviews:
        return 0
    # Extract first sequence of digits (handles '(1,234)' → 1234)
    digits = re.sub(r"[^\d]", "", reviews)
    return int(digits) if digits else 0


# ---------------------------------------------------------------------------
# Opportunity score calculation
# ---------------------------------------------------------------------------

def calculate_opportunity_score(business: dict) -> dict:
    """
    Score a business on its potential as a web-development client.

    Scoring breakdown:
      +40  No website listed
      +25  Rating >= 4.0
      +20  Reviews >= 30
      +10  Phone number exists
      +5   Address exists

    Returns the same dict enriched with 'score' and 'opportunity' keys.
    """
    score = 0

    has_website = bool(business.get("website", ""))
    rating = business.get("rating")          # float | None
    reviews = business.get("reviews", 0)     # int
    phone = business.get("phone", "")
    address = business.get("address", "")

    if not has_website:
        score += 40

    if rating is not None and rating >= 4.0:
        score += 25

    if isinstance(reviews, int) and reviews >= 30:
        score += 20

    if phone:
        score += 10

    if address:
        score += 5

    # Cap at 100
    score = min(score, 100)

    # Classify
    if score >= 80:
        level = "HIGH"
    elif score >= 50:
        level = "MEDIUM"
    else:
        level = "LOW"

    business["score"] = score
    business["opportunity"] = level
    return business


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def build_summary(leads: list[dict]) -> dict:
    """Compute summary stats shown above the results table."""
    total = len(leads)
    no_website = sum(1 for b in leads if not b.get("website"))
    scores = [b.get("score", 0) for b in leads]
    highest = max(scores) if scores else 0

    return {
        "total": total,
        "no_website": no_website,
        "highest_score": highest,
    }
