# 🚗 Universal Car Scraper

Scrapes **all inventory** from multiple Japanese car export sites by splitting into
**Make × Year × Price Band** segments — bypassing per-page limits completely.

Runs daily on GitHub Actions (free), pushes to Supabase (free PostgreSQL).

---

## How it bypasses page limits

Instead of paginating through all 200,000+ cars (hitting the 20-50/page wall),
it queries by **Make + Year** combinations:

```
Toyota 1990 → maybe 200 cars → 10 pages ✅
Toyota 1991 → maybe 150 cars → 8 pages  ✅
...
Toyota 2025 → maybe 800 cars → 40 pages → too many!
  → auto-splits by price band:
     Toyota 2025 ¥0-500k      → 5 pages  ✅
     Toyota 2025 ¥500k-1M     → 12 pages ✅
     Toyota 2025 ¥1M-2M       → 8 pages  ✅
     ...
```

Every segment is guaranteed to be fully scraped.

---

## Setup (~10 minutes)

### 1. Supabase (free database)
1. Sign up at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to **SQL Editor → New Query**, paste `schema.sql`, click **Run**
4. Go to **Settings → API**, copy your **Project URL** and **anon key**

### 2. GitHub
1. Create a new repo and upload all these files
2. Go to **Settings → Secrets → Actions**, add:
   - `SUPABASE_URL` = your Supabase project URL
   - `SUPABASE_KEY` = your Supabase anon key

### 3. Done 🎉
Runs every day at 2 AM UTC (2 PM NZT).
Manual trigger: **Actions → Daily Car Scraper → Run workflow**

---

## Adding a new site

**1. Add to `config/sites.json`:**
```json
{
  "name": "My New Site",
  "base_url": "https://mynewsite.com",
  "search_url": "https://mynewsite.com/cars?page={page}",
  "adapter": "mynewsite",
  "max_pages": 5,
  "enabled": true
}
```

**2. Create `scrapers/mynewsite.py`:**
```python
from bs4 import BeautifulSoup
from scrapers.base import BaseAdapter, Car

class Adapter(BaseAdapter):

    def get_filtered_url(self, page, make=None, year=None,
                         price_min=None, price_max=None):
        # Build the URL with filters your site supports
        url = f"https://mynewsite.com/cars?page={page}"
        if make:  url += f"&make={make}"
        if year:  url += f"&year={year}"
        return url

    def get_total_pages(self, html, page_size=20):
        # Parse the total result count from the HTML
        # Return an int (number of pages)
        return 1

    def parse_page(self, html, page_url):
        # Parse car listings from HTML, return list[Car]
        return []
```

**3. Push to GitHub** — included in the next daily run automatically.

---

## Running locally

```bash
pip install -r requirements.txt

export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_KEY="your-anon-key"

# All sites, all makes/years
python scraper.py

# One site only
python scraper.py --site "SBT Japan"

# One make only (much faster for testing)
python scraper.py --make TOYOTA --year 2020

# Dry run (no DB writes)
python scraper.py --make HONDA --year 2022 --dry-run
```

---

## Files

```
car-scraper/
├── scraper.py                        # Main engine
├── requirements.txt
├── schema.sql                        # Run once in Supabase
├── config/
│   ├── sites.json                    # Add new sites here
│   └── segments.json                 # Makes, years, price bands
├── scrapers/
│   ├── base.py                       # Base adapter (don't edit)
│   ├── sbtjapan.py
│   ├── beforward.py
│   └── carfromjapan.py
└── .github/workflows/
    └── daily_scrape.yml              # 7 parallel GitHub Actions workers
```
