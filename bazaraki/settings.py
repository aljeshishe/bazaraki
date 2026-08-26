# Scrapy settings for bazaraki project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import os
from pathlib import Path as _Path

BOT_NAME = "bazaraki"


def _load_dotenv(path=".env"):
    """Minimal .env reader; BAZARAKI_PROXY lives there so credentials stay out of the repo."""
    env_file = _Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv()

SPIDER_MODULES = ["bazaraki.spiders"]
NEWSPIDER_MODULE = "bazaraki.spiders"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "bazaraki (+http://www.yourdomain.com)"

# Obey robots.txt rules
# The crawler talks to the site's JSON API, which robots.txt puts behind `Disallow: /api`.
# Deliberately disabled so those requests are not filtered out; keep the crawl polite
# through AutoThrottle and a low concurrency instead.
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# The API answered 100 back-to-back requests without a single 429, unlike the HTML pages,
# so a handful of parallel requests is safe. AutoThrottle still backs off if that changes.
#CONCURRENT_REQUESTS_PER_DOMAIN = 4
CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Host": "www.bazaraki.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0",
    # Field and category names are language dependent — pin English so the columns stay stable.
    "Accept-Language": "en"
    # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    # "Accept-Language": "en-US,en;q=0.5",
    # "Connection": "keep-alive"
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
   # "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware": 0,

   # "bazaraki.middlewares.BazarakiSpiderMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "bazaraki.middlewares.BazarakiDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   "bazaraki.pipelines.BazarakiPipeline": 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# The site started answering 429 under a steady one-request-at-a-time crawl,
# so back off automatically instead of losing pages to exhausted retries.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

RETRY_TIMES = 5
# A rotating residential proxy hands out a fresh exit IP per connection, and Cloudflare
# refuses some of them: roughly one request in five came back 403 in a 10-request sample.
# Scrapy does not retry 403 by default, so those ads would be dropped without a trace —
# a retry simply lands on another IP.
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403]

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# Disable scrapy logging configuration
LOG_ENABLED = False  
# Custom logging configuration
from datetime import datetime, timezone
NOW_STR = datetime.now(tz=timezone.utc).isoformat(sep=" ", timespec="seconds")
DEFAULT_LOGGING = {  
    "version": 1,  
    "disable_existing_loggers": False,  
    "formatters": {  
        "default": {  
            "format": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",  
        },  
    },  
    "handlers": {  
        "console": {  
            "level": "WARN",  
            "class": "logging.StreamHandler",  
            "formatter": "default",  
        },  
        "file": {  
            "level": "INFO",  
            "class": "logging.handlers.RotatingFileHandler",  
            "formatter": "default",  
            "filename": f"output/logs/debug_{NOW_STR}.log",  # File to store debug logs  
            "maxBytes": 10 * 1024 * 1024,  # 10 MB per log file  
            "backupCount": 5,  # Keep up to 5 backup files  
        },  
    },  
    "loggers": {  
        "root": {  
            "handlers": ["console", "file"],  
            "level": "DEBUG",  
            "propagate": True,  
        },  
    },  
}  
from pathlib import Path
Path(DEFAULT_LOGGING["handlers"]["file"]["filename"]).parent.mkdir(parents=True, exist_ok=True)
from scrapy.utils import log
log.DEFAULT_LOGGING = DEFAULT_LOGGING
