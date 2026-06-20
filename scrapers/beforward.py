from bs4 import BeautifulSoup
from scrapers.base import BaseAdapter, Car
import re


class Adapter(BaseAdapter):

    def get_filtered_url(self, page, make=None, year=None, price_min=None, price_max=None):
        base = "https://www.beforward.jp/stocklist/page:{}/".format(page)
        params = []
        if make:
            params.append("make={}".format(make))
        if year:
            params.append("minyear={}&maxyear={}".format(year, year))
        if price_min is not None:
            params.append("minprice={}".format(price_min))
        if price_max is not None:
            params.append("maxprice={}".format(price_max))
        if params:
            base += "?" + "&".join(params)
        return base

    def get_total_pages(self, html, page_size=20):
        return 1

    def parse_page(self, html, page_url):
        return []
