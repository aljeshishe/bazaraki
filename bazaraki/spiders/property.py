import re
import scrapy
from loguru import logger
from tqdm import tqdm


def getall(response, selector, replace=None):
    result = response.css(selector).getall()
    if result is None:
        return None

    result = [item.strip() for item in result]
    if replace:
        pattern = '|'.join(map(re.escape, replace.split()))
        result = [re.sub(pattern, "", item) for item in result]
        result = [item.strip() for item in result]

    return result

def get(response, selector, type=str, replace=None):
    result = response.css(selector).get()
    if result is None:
        return None
    
    result = result.strip()
    
    if replace:
        pattern = '|'.join(map(re.escape, replace.split()))
        result = re.sub(pattern, "", result)
        result = result.strip()

    result = type(result)
    return result 

class PropertySpider(scrapy.Spider):
    name = "property_spider"

    def __init__(self, urls: str, fast=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = urls.split(",")
        self.fast = int(fast)
        self.pb = tqdm(desc="Crawling Pages", unit="page", total=0) 

    def start_requests(self):
        for url in self.start_urls:
            logger.info(f"Starting to scrape {url}")
            yield scrapy.Request(url, self.parse)
    
    def parse(self, response):
        """
        Parse the initial page to find the maximum page number.
        """
        # Extract the maximum page number
        pages = response.css("a.page-number::attr(data-page)").getall()
        max_page_number = max(map(int, pages)) + 1 if pages and not self.fast else 2
        for page_number in range(1, max_page_number):
            url = f"{response.url}?page={page_number}"
            yield scrapy.Request(url=url, callback=self.parse_list_page)
       
        yield from self.parse_list_page(response)

    
    def parse_list_page(self, response):
        for url in response.css("a[class='mask']::attr(href)").getall():
            self.pb.total += 1
            self.pb.refresh()
            yield response.follow(url, callback=self.parse_page)

    def parse_page(self, response):
        """
        Parse a single page for property listings.
        """
        data = {
            "url": response.url,
            "title": get(response, "h1::text"),
            "price": get(response, "meta[itemprop='price']::attr(content)", type=float),
            "original_price": get(response, ".announcement-price__discount-start::text", type=int, replace="/m² € ."),
            "price_per_sqm": get(response, ".announcement-price__per-meter::text", type=int, replace="/m² € ."),
            "location": get(response, "span[itemprop='address']::text"),
            "posted": get(response, "span[class='date-meta']::text", replace="Posted: Today"),
            "ad_id": get(response, "span[itemprop='sku']::text"),
            "reference_number": get(response, "span.reference-number::text"),
            "views": get(response, "span[class='counter-views']::text", replace="Views:", type=int),
            "lat": get(response, "div[id='geoMap']::attr(data-default-lat)"),
            "lng": get(response, "div[id='geoMap']::attr(data-default-lng)"),
            "sold": bool(get(response, ".phone-author--sold")),
        }
        
        categories = getall(response, "span[itemprop='name']::text")
        categories_map = {f"cat{i}": cat for i, cat in enumerate(categories[1:])}
        data.update(categories_map)
            
        keys = getall(response, "div[class='announcement-characteristics clearfix'] [class='key-chars']::text", replace=":")
        values = getall(response, "div[class='announcement-characteristics clearfix'] [class='value-chars']::text", replace="m²")
        data.update(zip(keys, values))
        
        long_data = {
            "images": getall(response, "img[class='announcement__thumbnails-item js-select-image']::attr(src)"),
            "description": "\n".join(getall(response, "div.js-description > *::text"))
        }
        data.update(long_data)
        
        self.pb.update(1)
        return data
    
    def closed(self, reason):  
        # Close the progress bar when the spider finishes  
        if self.pb:  
            self.pb.close()     