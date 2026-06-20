from bs4 import BeautifulSoup
from scrapers.base import BaseAdapter, Car
import re


class Adapter(BaseAdapter):

    def get_filtered_url(self, page, make=None, year=None, price_min=None, price_max=None):
        base = f"https://www.beforward.jp/stocklist/page:{page}/"
        params = []
        if make:
            params.append(f"make={make.replace(' ', '+')}")
        if year:
            params.append(f"minyear={year}&maxyear={year}")
        if price_min is not None:
            params.append(f"minprice={price_min}")
        if price_max is not None:
            params.append(f"maxprice={price_max}")
        if params:
            base += "?" + "&".join(params)
        return base

    def get_total_pages(self, html, page_size=20):
        soup = BeautifulSoup(html, "html.parser")
        for el in soup.find_all(string=re.compile(r"\d+\s*(cars|results|vehicles)", re.I)):
            m = re.search(r"of\s+([\d,]+)", el)
            if m:
                total = int(m.group(1).replace(",", ""))
                return max(1, -(-total // page_size))
        pagination = soup.find(class_=re.compile(r"paginat|pager|page-nav"))
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

        for row in soup.find_all("div", class_=re.compile(r"^stocklist-row")):
            link = row.find("a", class_="vehicle-url-link")
            if not link:
                continue
            href = link.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            full_url = "https://www.beforward.jp" + href if href.startswith("/") else href

            # Stock ID: prefer the numeric /id/<digits>/ segment, fall back to the slug code
            id_match = re.search(r"/id/(\d+)/", href)
            if id_match:
                stock_id = id_match.group(1)
            else:
                slug_match = re.search(r"/([a-z0-9]+)/id/", href, re.I)
                stock_id = slug_match.group(1) if slug_match else href.rstrip("/").split("/")[-1]

            title_el = row.find("p", class_="make-model")
            title = title_el.get_text(separator=" ", strip=True) if title_el else ""
            title = re.sub(r"\s+", " ", title).strip()
            if not title or len(title) < 5:
                continue

            price_el = row.find("span", class_="price")
            price_raw = price_el.get_text(strip=True) if price_el else ""

            def spec_value(spec_name):
                td = row.find("td", class_=re.compile(spec_name))
                if not td:
                    return ""
                val_el = td.find("p", class_="val")
                return val_el.get_text(strip=True) if val_el else ""

            mileage_raw = spec_value("mileage")
            engine_raw = spec_value("engine")
            transmission = spec_value("trans")

            img = row.find("img")
            image_url = None
            if img:
                src = img.get("src") or img.get("data-src")
                if src:
                    image_url = "https:" + src if src.startswith("//") else src

            car = Car(
                source=self.name,
                source_url=full_url,
                stock_id=stock_id,
                title=title,
                price_jpy=self.clean_price(price_raw),
                mileage_km=self.clean_int(mileage_raw),
                engine_cc=self.clean_int(engine_raw),
                transmission=transmission or None,
                image_url=image_url,
            )
            car.parse_title()
            cars.append(car)

        return cars
