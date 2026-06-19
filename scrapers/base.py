"""
Base adapter class. To add a new site:
1. Create a new file in scrapers/ e.g. scrapers/mysite.py
2. Subclass BaseAdapter and implement parse_page()
3. Add the site to config/sites.json with "adapter": "mysite"
"""

from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class Car:
    source: str          # Site name e.g. "SBT Japan"
    source_url: str      # Full URL to the listing
    stock_id: str        # Unique ID from the source site
    title: str           # Full title e.g. "2018 TOYOTA SIENTA G"
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    price_jpy: Optional[int] = None
    mileage_km: Optional[int] = None
    engine_cc: Optional[int] = None
    fuel: Optional[str] = None
    drivetrain: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    seats: Optional[int] = None
    doors: Optional[int] = None
    location: Optional[str] = None
    image_url: Optional[str] = None

    def parse_title(self):
        """Auto-extract year/make/model from title if not already set."""
        m = re.match(r'^(\d{4})(?:/\d+)?\s+(\S+)\s+(.+)$', self.title)
        if m:
            if not self.year:
                self.year = int(m.group(1))
            if not self.make:
                self.make = m.group(2).title()
            if not self.model:
                self.model = m.group(3).strip()

    def unique_key(self):
        """Used for deduplication in the database."""
        return f"{self.source}::{self.stock_id}"


class BaseAdapter:
    """
    Subclass this to add support for a new car site.
    Only parse_page() needs to be implemented.
    """

    def __init__(self, site_config: dict):
        self.config = site_config
        self.name = site_config["name"]
        self.base_url = site_config["base_url"]
        self.search_url = site_config["search_url"]
        self.max_pages = site_config.get("max_pages", 5)

    def get_page_url(self, page: int) -> str:
        return self.search_url.replace("{page}", str(page))

    def parse_page(self, html: str, page_url: str) -> list[Car]:
        """
        Parse an HTML page and return a list of Car objects.
        Must be implemented by each site adapter.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement parse_page()")

    @staticmethod
    def clean_int(value: str) -> Optional[int]:
        if not value:
            return None
        digits = re.sub(r'[^\d]', '', value)
        return int(digits) if digits else None

    @staticmethod
    def clean_price(value: str) -> Optional[int]:
        if not value or 'ask' in value.lower():
            return None
        digits = re.sub(r'[^\d]', '', value)
        return int(digits) if digits else None
