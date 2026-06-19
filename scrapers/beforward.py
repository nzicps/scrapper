from bs4 import BeautifulSoup
from scrapers.base import BaseAdapter, Car
import re


class Adapter(BaseAdapter):

    def parse_page(self, html: str, page_url: str) -> list[Car]:
        soup = BeautifulSoup(html, "html.parser")
        cars = []
        seen = set()

        for link in soup.find_all("a", href=re.compile(r"/[a-z\-]+/[A-Z0-9]+\.html")):
            href = link.get("href", "")
            if href in seen or "stocklist" in href:
                continue
            seen.add(href)

            container = link.find_parent(class_=re.compile("item|card|product|listing"))
            if not container:
                continue

            def get_text(sel):
                el = container.find(class_=re.compile(sel))
                return el.get_text(strip=True) if el else ""

            title = get_text("car.?name|title|model") or link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            price_raw = get_text("price|amount")
            stock_id = re.search(r"/([A-Z0-9]+)\.html", href)
            stock_id = stock_id.group(1) if stock_id else href.split("/")[-1]
            full_url = "https://www.beforward.jp" + href if href.startswith("/") else href

            mileage_raw = get_text("mileage|odometer")
            engine_raw = get_text("engine|cc|displacement")
            fuel = get_text("fuel")
            drivetrain = get_text("drive|4wd|2wd|awd")
            color = get_text("color|colour")

            img = container.find("img")
            image_url = img.get("src") or img.get("data-src") if img else None

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
                color=color or None,
                image_url=image_url,
            )
            car.parse_title()
            cars.append(car)

        return cars
