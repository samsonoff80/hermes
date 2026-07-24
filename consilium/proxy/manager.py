import os, httpx, logging

logger = logging.getLogger("consilium.proxy")

class ProxyManager:
    def __init__(self):
        self._proxies = {}
        self._indexes = {}
        for k, v in os.environ.items():
            if k.startswith("PROXY_"):
                p = k[6:].lower()
                self._proxies[p] = [u.strip() for u in v.split(',') if u.strip()]
                self._indexes[p] = 0
    
    def get(self, platform: str) -> str | None:
        urls = self._proxies.get(platform, [])
        if not urls: return None
        idx = self._indexes.get(platform, 0)
        self._indexes[platform] = idx + 1
        return urls[idx % len(urls)]
    
    def get_client(self, platform: str, base_url: str, timeout: int = 30) -> httpx.AsyncClient:
        proxy = self.get(platform)
        if proxy:
            return httpx.AsyncClient(base_url=base_url, proxy=proxy, timeout=httpx.Timeout(timeout))
        return httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(timeout))

proxy_manager = ProxyManager()
