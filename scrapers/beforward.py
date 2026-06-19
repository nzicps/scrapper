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
        for link in soup.find_all("a", href=re.compile(r"/[a-z\-]+/[A-Z0-9]+\.html")):
            href = link.get("href", "")
            if href in seen or "stocklist" in href:
                continue
            seen.add(href)
            container = link.find_parent(class_=re.compile("item|card|product|listing"))
            if not container:
                continue
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            price_el = container.find(class_=re.compile("price|amount"))
            price_raw = price_el.get_text(strip=True) if price_el else ""
            stock_id = re.search(r"/([A-Z0-9]+)\.html", href)
            stock_id = stock_id.group(1) if stock_id else href.split("/")[-1]
            full_url = "https://www.beforward.jp" + href if href.startswith("/") else href
            img = container.find("img")
            image_url = (img.get("src") or img.get("data-src")) if img else None
            car = Car(source=self.name, source_url=full_url, stock_id=stock_id,
                      title=title, price_jpy=self.clean_price(price_raw), image_url=image_url)
            car.parse_title()
            cars.append(car)
        return cars
