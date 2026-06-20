"""
Turners NZ scraper using Playwright (real browser).
Runs separately from the main scraper.

Usage:
    python scrape_nz.py
    python scrape_nz.py --dry-run
    python scrape_nz.py --make Toyota --year 2020
"""

import os
import re
import time
import json
import argparse
import logging
from datetime import datetime, timezone
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TABLE_NAME   = "cars"
BATCH_SIZE   = 50

MAKES = [
    "Toyota", "Honda", "Nissan", "Mazda", "Mitsubishi", "Subaru", "Suzuki",
    "BMW", "Mercedes-Benz", "Volkswagen", "Audi", "Ford", "Hyundai", "Kia",
    "Lexus", "Isuzu", "Daihatsu", "Land Rover", "Jeep", "Volvo"
]


def clean_price(text):
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def clean_int(text):
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def car_to_row(car):
    return {
        "unique_key":   car["unique_key"],
        "source":       "Turners NZ",
        "source_url":   car.get("url"),
        "stock_id":     car.get("stock_id"),
        "title":        car.get("title"),
        "year":         car.get("year"),
        "make":         car.get("make"),
        "model":        car.get("model"),
        "price_jpy":    None,
        "price_nzd":    car.get("price_nzd"),
        "mileage_km":   car.get("mileage_km"),
        "engine_cc":    car.get("engine_cc"),
        "fuel":         car.get("fuel"),
        "transmission": car.get("transmission"),
        "color":        car.get("color"),
        "image_url":    car.get("image_url"),
        "scraped_at":   datetime.now(timezone.utc).isoformat(),
    }


def scrape_turners(make, dry_run=False):
    from playwright.sync_api import sync_playwright

    cars = []
    url = f"https://www.turners.co.nz/Cars/Used-Cars-for-Sale/?make={make}&inStock=true"

    log.info(f"Scraping Turners: {make} → {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page.set_extra_http_headers({"Accept-Language": "en-NZ,en;q=0.9"})

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)  # let JS render

            # Scroll to load lazy content
            for _ in range(3):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                page.wait_for_timeout(1000)

            # Extract car cards
            cards = page.query_selector_all("[class*='vehicle-card'], [class*='car-card'], [class*='listing-card'], [class*='result-card'], article")

            log.info(f"  Found {len(cards)} cards on page")

            for card in cards:
                try:
                    # Title
                    title_el = card.query_selector("h2, h3, [class*='title'], [class*='name'], [class*='heading']")
                    title = title_el.inner_text().strip() if title_el else ""
                    if not title or len(title) < 5:
                        continue

                    # URL
                    link_el = card.query_selector("a")
                    href = link_el.get_attribute("href") if link_el else ""
                    full_url = "https://www.turners.co.nz" + href if href and href.startswith("/") else href

                    # Price
                    price_el = card.query_selector("[class*='price'], [class*='amount'], [class*='cost']")
                    price_nzd = clean_price(price_el.inner_text() if price_el else "")

                    # Mileage
                    text = card.inner_text()
                    mileage_match = re.search(r"([\d,]+)\s*km", text, re.I)
                    mileage = clean_int(mileage_match.group(1)) if mileage_match else None

                    # Year from title
                    year_match = re.match(r"^(\d{4})\s+", title)
                    year = int(year_match.group(1)) if year_match else None

                    # Make/model from title
                    parts = title.split()
                    car_make = parts[1] if len(parts) > 1 else make
                    car_model = " ".join(parts[2:]) if len(parts) > 2 else ""

                    # Stock ID from URL
                    stock_id = href.rstrip("/").split("/")[-1] if href else title[:20]

                    # Image
                    img = card.query_selector("img")
                    image_url = img.get_attribute("src") if img else None

                    # Fuel / transmission from text
                    fuel = None
                    for f in ["Petrol", "Diesel", "Hybrid", "Electric", "Plug-in"]:
                        if f.lower() in text.lower():
                            fuel = f
                            break

                    transmission = None
                    for t in ["Automatic", "Manual"]:
                        if t.lower() in text.lower():
                            transmission = t[:4]
                            break

                    car = {
                        "unique_key": f"Turners NZ::{stock_id}",
                        "url": full_url,
                        "stock_id": stock_id,
                        "title": title,
                        "year": year,
                        "make": car_make,
                        "model": car_model,
                        "price_nzd": price_nzd,
                        "mileage_km": mileage,
                        "fuel": fuel,
                        "transmission": transmission,
                        "image_url": image_url,
                    }
                    cars.append(car)

                except Exception as e:
                    log.warning(f"  Error parsing card: {e}")
                    continue

        except Exception as e:
            log.error(f"  Page load error: {e}")
        finally:
            browser.close()

    log.info(f"  Extracted {len(cars)} cars for {make}")
    return cars


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", help="Scrape only this make")
    parser.add_argument("--year", type=int, help="Filter by year")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    makes = [args.make] if args.make else MAKES

    db = None if args.dry_run else create_client(SUPABASE_URL, SUPABASE_KEY)

    total = 0
    for make in makes:
        cars = scrape_turners(make, args.dry_run)

        if args.dry_run:
            log.info(f"[dry-run] Would upsert {len(cars)} cars for {make}")
            continue

        rows = [car_to_row(c) for c in cars]
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            try:
                db.table(TABLE_NAME).upsert(batch, on_conflict="unique_key").execute()
                total += len(batch)
            except Exception as e:
                log.error(f"DB error: {e}")

        time.sleep(2)  # polite delay between makes

    log.info(f"Done — {total} Turners rows upserted")


if __name__ == "__main__":
    main()
