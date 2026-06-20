from bs4 import BeautifulSoup
from scrapers.base import BaseAdapter, Car
import re


class Adapter(BaseAdapter):

    def get_filtered_url(self, page, make=None, year=None, price_min=None, price_max=None):
        base = f"https://carfromjapan.com/cheap-used-japanese-cars?page={page}"
        if make:
            base += f"&maker_id={make}"
        if year:
            base += f"&year_from={year}&year_to={year}"
        if price_min is not None:
            base += f"&price_from={price_min}"
        if price_max is not None:
            base += f"&price_to={price_max}"
        return base

    def get_total_pages(self, html, page_size=20):
        return 1

    def parse_page(self, html: str, page_url: str) -> list[Car]:
        soup = BeautifulSoup(html, "html.parser")
        cars = []
        seen = set()
        for link in soup.find_all("a", href=re.compile(r"/used-car/[^/]+/\d+")):
            href = link.get("href", "")
            if href in seen:
                continue
            seen.add(href)
            container = link.find_parent(class_=re.compile("car|item|product|listing"))
            if not container:
                continue

            def get_text(sel):
                el = container.find(class_=re.compile(sel))
                return el.get_text(strip=True) if el else ""

            title = get_text("title|name|car.?name") or link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            price_raw = get_text("price|amount|cost")
            stock_id = href.rstrip("/").split("/")[-1]
            full_url = "https://carfromjapan.com" + href if href.startswith("/") else href
            mileage_raw = get_text("mileage|odometer|km")
            engine_raw = get_text("engine|cc|displacement")
            fuel = get_text("fuel|gas|energy")
            drivetrain = get_text("drive|4wd|fwd|awd")
            color = get_text("color|colour")
            transmission = get_text("trans|gearbox|shift")
            img = container.find("img")
            image_url = (img.get("src") or img.get("data-src")) if img else None
            car = Car(
                source=self.name,
                source_url=full_url,
                stock_id=stock_id,
                title=title,
                price_jpy=self.clean_price(price_raw),
                mileage_km=self.clean_int(mileage_raw),
                engine_cc=self.clean_int(engine_raw),
                fuel=fuel or None,
                drivetrain=drivetrain or None,
                transmission=transmission or None,
                color=color or None,
                image_url=image_url,
            )
            car.parse_title()
            cars.append(car)
        return cars
