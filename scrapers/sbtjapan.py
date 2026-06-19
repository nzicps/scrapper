from bs4 import BeautifulSoup
from scrapers.base import BaseAdapter, Car
import re


class Adapter(BaseAdapter):

    def get_filtered_url(self, page: int, make: str = None, year: int = None,
                         price_min: int = None, price_max: int = None) -> str:
        """Build a filtered search URL for SBT Japan."""
        base = "https://www.sbtjapan.com/used-cars/search?s=-pv&inventory_location=36"
        if make:
            base += f"&make={make.replace(' ', '+')}"
        if year:
            base += f"&year_from={year}&year_to={year}"
        if price_min is not None:
            base += f"&price_from={price_min}"
        if price_max is not None:
            base += f"&price_to={price_max}"
        base += f"&page={page}"
        return base

    def get_total_pages(self, html: str, page_size: int = 20) -> int:
        """Extract total result count from HTML and return page count."""
        soup = BeautifulSoup(html, "html.parser")
        for el in soup.find_all(string=re.compile(r'\d+\s*(cars|results|vehicles)', re.I)):
            m = re.search(r'of\s+([\d,]+)', el)
            if m:
                total = int(m.group(1).replace(',', ''))
                return max(1, -(-total // page_size))
        pagination = soup.find(class_=re.compile(r'paginat|pager|page-nav'))
        if pagination:
            nums = [int(a.get_text(strip=True)) for a in pagination.find_all('a')
                    if a.get_text(strip=True).isdigit()]
            if nums:
                return max(nums)
        return 1

    def parse_page(self, html: str, page_url: str) -> list[Car]:
        soup = BeautifulSoup(html, "html.parser")
        cars = []
        seen = set()

        for link in soup.find_all("a", href=re.compile(r"/used-cars/[A-Z]{2}\d+")):
            href = link.get("href", "")
            if href in seen:
                continue
            seen.add(href)

            container = link.find_parent(class_=re.compile("card"))
            if not container:
                container = link.parent

            def get(sel):
                el = container.find(class_=re.compile(sel))
                return el.get_text(strip=True) if el else ""

            title = get("name|title|product") or link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            price_raw = get("price")
            stock_id  = href.split("/")[-1]
            full_url  = "https://www.sbtjapan.com" + href if href.startswith("/") else href

            statuses = [el.get_text(strip=True) for el in
                        container.find_all(class_=re.compile("status|spec|badge"))]

            mileage = color = fuel = drivetrain = engine_cc = None
            for s in statuses:
                su = s.upper()
                if re.match(r"^\d[\d,]*KM$", su):
                    mileage = self.clean_int(s)
                elif re.match(r"^\d[\d,]*CC$", su):
                    engine_cc = self.clean_int(s)
                elif su in ("2WD", "4WD", "AWD", "FWD", "RWD"):
                    drivetrain = su
                elif any(f in su for f in ["PETROL", "DIESEL", "HYBRID", "ELECTRIC", "PLUG-IN"]):
                    fuel = s
                elif re.match(r"^(WHITE|BLACK|SILVER|PEARL|BLUE|RED|GOLD|GREEN|GRAY|GREY|BROWN|BEIGE)", su):
                    color = s

            img = container.find("img")
            image_url = (img.get("src") or img.get("data-src")) if img else None

            car = Car(
                source=self.name,
                source_url=full_url,
                stock_id=stock_id,
                title=title,
                price_jpy=self.clean_price(price_raw),
                mileage_km=mileage,
                engine_cc=engine_cc,
                fuel=fuel,
                drivetrain=drivetrain,
                color=color,
                image_url=image_url,
            )
            car.parse_title()
            cars.append(car)

        return cars
