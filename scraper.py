"""
Universal Car Scraper — segmented by Make × Year × Price Band
Bypasses per-page limits by splitting inventory into small filterable chunks.

Usage:
    python scraper.py                         # all sites, all segments
    python scraper.py --site "SBT Japan"      # one site only
    python scraper.py --make TOYOTA           # one make only
    python scraper.py --year 2020             # one year only
    python scraper.py --dry-run               # no DB writes
    python scraper.py --chunk 0 --total-chunks 7  # for GitHub Actions parallelism
"""

import os, json, time, importlib, argparse, requests, logging
from datetime import datetime, timezone
from itertools import product as cartesian
from supabase import create_client, Client
from scrapers.base import Car

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY", "")
TABLE_NAME    = "cars"
PROXY_URL     = "https://api.allorigins.win/get?url={url}"
REQUEST_DELAY = 2.5   # seconds between fetches
TIMEOUT       = 30
BATCH_SIZE    = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# ── Loaders ───────────────────────────────────────────────────────────────────

def load_config(name):
    path = os.path.join(os.path.dirname(__file__), "config", name)
    with open(path) as f:
        return json.load(f)

def load_adapter(site: dict):
    mod = importlib.import_module(f"scrapers.{site['adapter']}")
    return mod.Adapter(site)

# ── Segment builder ───────────────────────────────────────────────────────────

def build_segments(seg_cfg: dict, filter_make=None, filter_year=None) -> list[dict]:
    """
    Returns a list of {make, year, price_min, price_max} dicts.
    Each segment is small enough to paginate fully.
    """
    makes = seg_cfg["makes"]
    yr    = seg_cfg["year_range"]
    years = list(range(yr["start"], yr["end"] + 1))
    bands = seg_cfg["price_bands_jpy"]

    if filter_make:
        makes = [m for m in makes if m.upper() == filter_make.upper()]
    if filter_year:
        years = [y for y in years if y == filter_year]

    segments = []
    for make, year in cartesian(makes, years):
        # Start with one segment per make/year; split by price if needed
        segments.append({
            "make": make, "year": year,
            "price_min": None, "price_max": None,
            "use_price_bands": False
        })
    return segments

# ── Fetcher ───────────────────────────────────────────────────────────────────

def fetch_html(url: str) -> str:
    proxied = PROXY_URL.format(url=requests.utils.quote(url, safe=""))
    r = requests.get(proxied, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("contents", "")

def get_nzd_rate() -> float:
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/JPY", timeout=10)
        rate = r.json()["rates"]["NZD"]
        log.info(f"💱 JPY→NZD: {rate:.5f}")
        return rate
    except Exception:
        log.warning("Could not fetch live rate, using fallback 0.0108")
        return 0.0108

# ── Core scrape logic ─────────────────────────────────────────────────────────

def scrape_segment(adapter, seg: dict, seg_cfg: dict, nzd_rate: float,
                   db: Client, dry_run: bool) -> int:
    """
    Scrape a single make/year (optionally price-banded) segment.
    Returns number of cars upserted.
    """
    max_pages   = seg_cfg["max_pages_per_segment"]
    page_size   = seg_cfg["page_size"]
    price_bands = seg_cfg["price_bands_jpy"]
    make, year  = seg["make"], seg["year"]

    def scrape_band(price_min, price_max) -> list[Car]:
        cars = []
        for page in range(1, max_pages + 1):
            url = adapter.get_filtered_url(
                page=page, make=make, year=year,
                price_min=price_min, price_max=price_max
            )
            try:
                html = fetch_html(url)
            except Exception as e:
                log.warning(f"  Fetch error page {page}: {e}")
                break

            # On first page, detect total pages
            if page == 1:
                total_pages = adapter.get_total_pages(html, page_size)
                log.info(f"  {make} {year} band={price_min}-{price_max}: {total_pages} pages")

                # If too many pages, split by price bands recursively
                if total_pages > max_pages and price_min is None:
                    log.info(f"  → Too large, splitting into price bands")
                    banded = []
                    for pmin, pmax in price_bands:
                        banded += scrape_band(pmin, pmax)
                    return banded

            page_cars = adapter.parse_page(html, url)
            cars.extend(page_cars)

            if page >= total_pages:
                break

            time.sleep(REQUEST_DELAY)

        return cars

    all_cars = scrape_band(None, None)

    if not all_cars:
        return 0

    if dry_run:
        log.info(f"  [dry-run] Would upsert {len(all_cars)} cars")
        return len(all_cars)

    rows = [car_to_row(c, nzd_rate) for c in all_cars]
    upserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        try:
            db.table(TABLE_NAME).upsert(batch, on_conflict="unique_key").execute()
            upserted += len(batch)
        except Exception as e:
            log.error(f"  DB error: {e}")

    return upserted

def car_to_row(car: Car, nzd_rate: float) -> dict:
    return {
        "unique_key":   car.unique_key(),
        "source":       car.source,
        "source_url":   car.source_url,
        "stock_id":     car.stock_id,
        "title":        car.title,
        "year":         car.year,
        "make":         car.make,
        "model":        car.model,
        "price_jpy":    car.price_jpy,
        "price_nzd":    round(car.price_jpy * nzd_rate) if car.price_jpy else None,
        "mileage_km":   car.mileage_km,
        "engine_cc":    car.engine_cc,
        "fuel":         car.fuel,
        "drivetrain":   car.drivetrain,
        "transmission": car.transmission,
        "color":        car.color,
        "seats":        car.seats,
        "doors":        car.doors,
        "location":     car.location,
        "image_url":    car.image_url,
        "scraped_at":   datetime.now(timezone.utc).isoformat(),
    }

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site",         help="Scrape only this site")
    parser.add_argument("--make",         help="Filter to one make e.g. TOYOTA")
    parser.add_argument("--year",         type=int, help="Filter to one year e.g. 2020")
    parser.add_argument("--dry-run",      action="store_true")
    parser.add_argument("--chunk",        type=int, default=0,
                        help="Which chunk to process (0-based, for parallelism)")
    parser.add_argument("--total-chunks", type=int, default=1,
                        help="Total number of parallel chunks")
    args = parser.parse_args()

    sites_cfg = load_config("sites.json")
    seg_cfg   = load_config("segments.json")

    sites = [s for s in sites_cfg if s.get("enabled", True)]
    if args.site:
        sites = [s for s in sites if s["name"].lower() == args.site.lower()]

    nzd_rate = get_nzd_rate()
    db = None if args.dry_run else create_client(SUPABASE_URL, SUPABASE_KEY)

    segments = build_segments(seg_cfg, filter_make=args.make, filter_year=args.year)

    # Chunk segments across parallel workers
    my_segments = [s for i, s in enumerate(segments) if i % args.total_chunks == args.chunk]
    log.info(f"Processing {len(my_segments)}/{len(segments)} segments "
             f"(chunk {args.chunk+1}/{args.total_chunks})")

    total = 0
    for site in sites:
        log.info(f"\n{'═'*55}\n🌐 Site: {site['name']}\n{'═'*55}")
        adapter = load_adapter(site)

        for seg in my_segments:
            log.info(f"  ▶ {seg['make']} {seg['year']}")
            count = scrape_segment(adapter, seg, seg_cfg, nzd_rate, db, args.dry_run)
            total += count

    log.info(f"\n✅ Done — {total} cars upserted total")

if __name__ == "__main__":
    main()
