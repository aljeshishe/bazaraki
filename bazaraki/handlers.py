from scrapy.core.downloader.handlers.http11 import HTTP11DownloadHandler


class FreshConnectionDownloadHandler(HTTP11DownloadHandler):
    """Opens a new connection per request.

    The rotating proxy picks the exit IP per connection, so a kept-alive tunnel pins the crawl to IPs
    that Cloudflare has already started answering with 429/403, and retries never get past them.
    """

    def __init__(self, settings, crawler):
        super().__init__(settings, crawler)
        self._pool.persistent = False
