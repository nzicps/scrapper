from bs4 import BeautifulSoup
from scrapers.base import BaseAdapter, Car
import re


class Adapter(BaseAdapter):

    def get_filtered_url(self, page, make=None, year=None, price_min=None, price_max=None):
        base = "https://carfromjapan.com/cheap-used-japanese-cars?page={}".format(page)
        if make:
            base += "&maker_id={}".format(make)
        if year:
            base += "&year_from={}&year_to={}".format(year, year)
        if price_min is not None:
            base += "&price_from={}".format(price_min)
        if price_max is not None:
            base += "&price_to={}".format(price_max)
        return base

    def get_total_pages(self, html, page_size=20):
        return 1

    def parse_page(self, html, page_url):
        return []
