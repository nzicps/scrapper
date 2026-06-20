from bs4 import BeautifulSoup
from scrapers.base import BaseAdapter, Car
import re


class Adapter(BaseAdapter):

    def get_filtered_url(self, page, make=None, year=None, price_min=None, price_max=None):
        base = "https://www.turners.co.nz/Cars/Used-Cars-for-Sale/?page={}".format(page)
        if make:
            base += "&make={}".format(make.title())
        if year:
            base += "&yearFrom={}&yearTo={}".format(year, year)
        if price_min is not None:
            base += "&priceMin={}".format(price_min)
        if price_max is not None:
            base += "&priceMax={}".format(price_max)
        return base

    def get_total_pages(self, html, page_size=20):
        soup = BeautifulSoup(html, "html.parser")
        for el in soup.find_all(string=re.compile(r"of\s+[\d,]+", re.I)):
            m = re.search(r"of\s+([\d,]+)", el)
            if m:
                total = int(m.group(1).replace(",", ""))
                return max(1, -(-total // page_size))
        pagination = soup.find(class_=re.compile(r"paginat|pager"))
        if pagination:
            nums = [int(a.get_text(strip=True)) for a in pagination.find_all("a")
                    if a.get_text(strip=True).isdigit()]
            if nums:
                return max(nums)
        return 1

    def parse_page(self, html, page_url):
        soup = BeautifulSoup(html, "html.parser")
        cars = []
        seen = set()

        for link in soup.find_all("a", href=re.compile(r"/Cars/Used-Cars-for-Sale/[^/]+/\d+")):
            href = link.get("href", "")
            if href in seen:
                continue
            seen.add(href)

            container = link.find_parent(class_=re.compile(r"card|listing|result|vehicle|item"))
            if not container:
                container = link.parent

            def get(sel):
                el = container.find(class_=re.compile(sel))
                return el.get_text(strip=True) if el else ""

            title = get("title|name|heading|vehicle") or link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            price_raw = get("price|amount|cost")
            stock_id = href.rstrip("/").split("/")[-1]
            full_url = "https://www.turners.co.nz" + href if href.startswith("/") else href

            # Extract mileage
            mileage_el = container.find(string=re.compile(r"\d[\d,]*\s*km", re.I))
            mileage = None
            if mileage_el:
                m = re.search(r"([\d,]+)\s*km", mileage_el, re.I)
                if m:
                    mileage = int(m.group(1).replace(",", ""))

            img = container.find("img")
            image_url = (img.get("src") or img.get("data-src")) if img else None

            # Parse NZD price
            price_nzd = None
            if price_raw:
                m = re.search(r"[\d,]+", price_raw.replace(",", ""))
                if m:
                    price_nzd = int(m.group().replace(",", ""))

            car = Car(
                source=self.name,
                source_url=full_url,
                stock_id=stock_id,
                title=title,
                price_jpy=None,
                mileage_km=mileage,
                image_url=image_url,
            )
            # For Turners, store NZD price directly in price_nzd via title parse
            car.parse_title()

            # Hack: store NZD in price_jpy field temporarily, scraper will handle
            if price_nzd:
                car.price_jpy = price_nzd  # Will be stored as price_nzd in DB

            cars.append(car)

        return cars
