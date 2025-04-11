# Scrapy settings for bazaraki project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "bazaraki"

SPIDER_MODULES = ["bazaraki.spiders"]
NEWSPIDER_MODULE = "bazaraki.spiders"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "bazaraki (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 10
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "bazaraki.middlewares.BazarakiSpiderMiddleware": 543,
#}

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
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

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
