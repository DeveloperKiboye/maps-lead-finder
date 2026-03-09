"""
scraper.py — Sync Playwright scraper for Google Maps business listings.
Uses sync API to avoid Windows asyncio subprocess issues.
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

MAX_LISTINGS = 100
SCROLL_PAUSE = 2.0
ACTION_DELAY = 1.5
LISTING_TIMEOUT = 10_000
NAV_TIMEOUT = 60_000


async def scrape_google_maps(query: str) -> list[dict]:
    """Async wrapper that runs the sync scraper in a thread pool."""
    import asyncio
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        results = await loop.run_in_executor(pool, _run_scraper, query)
    return results


def _run_scraper(query: str) -> list[dict]:
    """Synchronous Playwright scraper — runs in a thread."""
    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.set_default_timeout(NAV_TIMEOUT)

        try:
            logger.info("Navigating to Google Maps …")
            encoded_query = query.replace(" ", "+")
            search_url = f"https://www.google.com/maps/search/{encoded_query}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            time.sleep(3)

            # Handle consent dialog
            try:
                for selector in [
                    'button[aria-label*="Accept"]',
                    'button[aria-label*="Reject"]',
                    'form:nth-child(2) button',
                    '[aria-label="Accept all"]',
                    'button:has-text("Accept all")',
                    'button:has-text("Reject all")',
                ]:
                    btn = page.query_selector(selector)
                    if btn:
                        btn.click()
                        time.sleep(1)
                        break
            except Exception:
                pass

            time.sleep(2)

            # Scroll results
            logger.info("Scrolling results panel …")
            previous_count = 0
            stall_counter = 0

            for _ in range(30):
                cards = page.query_selector_all('a.hfpxzc')
                current_count = len(cards)
                logger.info(f"  Listings visible: {current_count}")

                if current_count >= MAX_LISTINGS:
                    break

                end_notice = page.query_selector('span.HlvSq')
                if end_notice:
                    logger.info("Reached end of results.")
                    break

                page.evaluate("""
                    const feed = document.querySelector('div[role="feed"]');
                    if (feed) {
                        feed.scrollBy(0, 1000);
                    } else {
                        window.scrollBy(0, 1000);
                    }
                """)
                time.sleep(SCROLL_PAUSE)

                if current_count == previous_count:
                    stall_counter += 1
                    if stall_counter >= 4:
                        logger.info("No new results — stopping scroll.")
                        break
                else:
                    stall_counter = 0
                previous_count = current_count

            # Collect URLs
            listing_cards = page.query_selector_all('a.hfpxzc')
            listing_urls = []
            for card in listing_cards[:MAX_LISTINGS]:
                href = card.get_attribute("href")
                if href:
                    listing_urls.append(href)

            logger.info(f"Collected {len(listing_urls)} listing URLs.")

            if not listing_urls:
                logger.warning("No listing URLs found.")
                return []

            # Visit each listing
            for idx, url in enumerate(listing_urls, start=1):
                logger.info(f"[{idx}/{len(listing_urls)}] Scraping listing …")
                business = _extract_business(page, url)
                if business:
                    results.append(business)
                time.sleep(ACTION_DELAY)

        except Exception as exc:
            logger.error(f"Scraper error: {exc}", exc_info=True)
        finally:
            browser.close()

    logger.info(f"Scraping complete — {len(results)} businesses collected.")
    return results


def _extract_business(page: Page, url: str) -> Optional[dict]:
    """Visit a Maps listing URL and extract business details."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
        time.sleep(2)

        name = ""
        for selector in ['h1.DUwDvf', 'h1[class*="fontHeadlineLarge"]', 'h1']:
            el = page.query_selector(selector)
            if el:
                name = el.inner_text().strip()
                if name:
                    break
        if not name:
            name = "Unknown"

        rating = None
        rating_el = page.query_selector('div.F7nice span[aria-hidden="true"]')
        if rating_el:
            try:
                rating = float(rating_el.inner_text().strip().replace(",", "."))
            except ValueError:
                pass

        reviews = 0
        reviews_el = page.query_selector('div.F7nice span[aria-label*="review"]')
        if reviews_el:
            text = reviews_el.inner_text().strip()
            digits = re.sub(r"[^\d]", "", text)
            reviews = int(digits) if digits else 0

        phone = ""
        address = ""
        website = ""

        info_buttons = page.query_selector_all('button[data-item-id], a[data-item-id]')
        for btn in info_buttons:
            item_id = btn.get_attribute("data-item-id") or ""
            try:
                text = btn.inner_text().strip()
            except Exception:
                text = ""

            if "phone" in item_id and not phone:
                phone = text
            if "address" in item_id and not address:
                address = text
            if "authority" in item_id and not website:
                website = btn.get_attribute("href") or text

        if not phone:
            el = page.query_selector('[data-tooltip="Copy phone number"]')
            if el:
                phone = el.inner_text().strip()

        if not address:
            el = page.query_selector('[data-tooltip="Copy address"]')
            if el:
                address = el.inner_text().strip()

        if not website:
            el = page.query_selector('a[data-item-id*="authority"]')
            if el:
                website = el.get_attribute("href") or el.inner_text().strip()

        if website and "google.com/url" in website:
            match = re.search(r"url=([^&]+)", website)
            if match:
                from urllib.parse import unquote
                website = unquote(match.group(1))

        return {
            "name": name,
            "phone": phone,
            "address": address,
            "rating": rating,
            "reviews": reviews,
            "website": website,
            "maps_url": url,
        }

    except Exception as exc:
        logger.warning(f"Failed to extract business: {exc}")
        return None