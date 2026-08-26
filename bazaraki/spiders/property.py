"""Crawler for bazaraki real-estate listings.

Runs against the site's own JSON API (`/api/v2/spa/...`), the one its Next.js frontend
talks to. It returns the full advert object in ~3.5 KB gzipped against ~54 KB for the
rendered page, and — unlike the HTML pages, which start answering 429 after a couple of
requests — it is not rate limited.
"""
from datetime import datetime, timedelta
import json
import os
import re
from urllib.parse import urlencode, urlsplit

import scrapy
from tqdm import tqdm

API_LISTING = "/api/v2/spa/adverts/listing"
API_CARD = "/api/v2/spa/adverts/card"
# The API caps a listing page at 100 adverts; anything larger comes back empty.
PAGE_SIZE = 100

NOW = datetime.now()

# "5 minutes ago", "2 hours ago", "4 weeks ago", ...
RELATIVE_RE = re.compile(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", re.I)
RELATIVE_UNITS = {"minute": 1, "hour": 60, "day": 60 * 24, "week": 60 * 24 * 7,
                  "month": 60 * 24 * 30, "year": 60 * 24 * 365}
CONTACT_CHANNELS = ("is_phone", "is_chat", "is_whatsapp", "is_email")


def parse_money(value):
    """'€525.000' -> 525000.0, '€3.387/m²' -> 3387.0, 'Call for price' -> None."""
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value.split("/")[0])
    return float(digits) if digits else None


def date_published(advert):
    """schema.org publication date, carried by the API inside seo.linked_data."""
    graph = ((advert.get("seo") or {}).get("linked_data") or {}).get("@graph") or []
    for node in graph:
        if isinstance(node, dict) and node.get("@type") == "WebPage":
            return node.get("datePublished")
    return None


def normalize_posted(published, published_date=None):
    """Best-effort timestamp for an ad.

    The site only exposes a relative publication time ("2 hours ago", "Today"), so the
    time of day is only recoverable for ads younger than a day. Everything older falls
    back to the schema.org date, which is exact but date-only.
    """
    published = (published or "").strip()
    match = RELATIVE_RE.search(published)
    # "12 minutes ago" / "2 hours ago" is the only place a time of day survives; for anything
    # older the relative label is rounded, so schema.org's exact date wins.
    if match and match.group(2).lower() in ("minute", "hour"):
        minutes = int(match.group(1)) * RELATIVE_UNITS[match.group(2).lower()]
        return (NOW - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    if published_date:
        try:
            return datetime.strptime(published_date, "%Y-%m-%d").isoformat(timespec="seconds")
        except ValueError:
            pass
    if match:
        minutes = int(match.group(1)) * RELATIVE_UNITS[match.group(2).lower()]
        return (NOW - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    if published.lower() == "today":
        return NOW.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    if published.lower() == "yesterday":
        return (NOW - timedelta(days=1)).replace(hour=0, minute=0, second=0,
                                                 microsecond=0).isoformat(timespec="seconds")
    return ""


class PropertySpider(scrapy.Spider):
    name = "property_spider"

    def __init__(self, urls: str, fast=False, proxy=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = urls.split(",")
        self.fast = int(fast)
        # `-a proxy=http://user:pass@host:port`, or BAZARAKI_PROXY in the environment / .env.
        self.proxy = proxy or os.environ.get("BAZARAKI_PROXY")
        self.meta = {"proxy": self.proxy} if self.proxy else {}
        self.pb = tqdm(desc="Crawling Pages", unit="page", total=0)

    def listing_url(self, url, page):
        """https://www.bazaraki.com/real-estate-to-rent -> the API listing call for it."""
        parts = urlsplit(url)
        rubric = parts.path.strip("/")
        query = urlencode({"page": page, "page_size": PAGE_SIZE})
        return f"{parts.scheme}://{parts.netloc}{API_LISTING}/{rubric}/?{query}"

    def card_url(self, response, advert_url):
        """/adv/6629911_1-bedroom-apartment-to-rent/ -> the API card call for it."""
        parts = urlsplit(response.url)
        slug = advert_url.strip("/").split("/")[-1]
        return f"{parts.scheme}://{parts.netloc}{API_CARD}/{slug}/"

    def start_requests(self):
        # Log the host only, so proxy credentials never reach the log file.
        self.logger.info(f"Proxy: {urlsplit(self.proxy).hostname if self.proxy else 'none, direct'}")
        for url in self.start_urls:
            self.logger.info(f"Starting to scrape {url}")
            yield scrapy.Request(self.listing_url(url, 1), self.parse_start_page,
                                 meta=self.meta, priority=10)

    def parse_start_page(self, response):
        """
        Parse the initial page to find the maximum page number.
        """
        data = json.loads(response.text)
        total_pages = 1 if self.fast else data.get("total_pages") or 1
        self.logger.info(f"{response.url}: {total_pages} pages, {data.get('count')} adverts")
        for page_number in range(2, total_pages + 1):
            url = re.sub(r"page=\d+", f"page={page_number}", response.url)
            yield scrapy.Request(url=url, callback=self.parse_list_page,
                                 meta=self.meta, priority=10)

        yield from self.parse_list_page(response)

    def parse_list_page(self, response):
        adverts = json.loads(response.text).get("adverts") or []
        if not adverts:
            self.logger.warning(f"No adverts in {response.url}")
        for advert in adverts:
            self.pb.total += 1
            self.pb.refresh()
            yield scrapy.Request(self.card_url(response, advert["url"]),
                                 callback=self.parse_page, meta=self.meta, priority=0)

    def parse_page(self, response):
        """
        Parse a single page for property listings.
        """
        advert = json.loads(response.text)

        counters = advert.get("counters") or {}
        price = advert.get("price") or {}
        location = advert.get("location") or {}
        coordinates = location.get("coordinates") or {}
        features = {item["name"]: item["value"] for item in advert.get("features") or []}
        contacts = (advert.get("user") or {}).get("contacts") or {}

        data = {
            "url": (advert.get("seo") or {}).get("canonical") or response.url,
            "title": advert.get("name"),
            "price": parse_money(price.get("price")),
            "original_price": parse_money(price.get("start_price")),
            "price_per_sqm": parse_money(price.get("square_meter_price")),
            "location": location.get("name"),
            "posted": counters.get("published"),
            "ad_id": str(advert.get("id")) if advert.get("id") is not None else None,
            "reference_number": features.get("Reference number"),
            "views": counters.get("advert_view"),
            "lat": coordinates.get("lat"),
            "lng": coordinates.get("lng"),
            # A closed ad offers no way to reach the seller.
            "sold": not any(contacts.get(channel) for channel in CONTACT_CHANNELS),
        }
        data["posted_dt"] = normalize_posted(data["posted"], date_published(advert))
        categories = [category["name"] for category in advert.get("categories") or []]
        data.update({f"cat{i}": category for i, category in enumerate(categories)})
        data.update({key: re.sub(r"\s*m²", "", value).strip() if isinstance(value, str) else value
                     for key, value in features.items()})

        gallery = advert.get("gallery") or {}
        data["images"] = gallery.get("full") or gallery.get("small") or gallery.get("preview") or []
        data["description"] = advert.get("description") or ""

        self.pb.update(1)
        return data

    def closed(self, reason):
        # Close the progress bar when the spider finishes
        if self.pb:
            self.pb.close()
