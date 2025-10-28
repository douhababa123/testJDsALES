"""Asynchronous background scraper for JD.com refrigerator listings.

This module avoids heavyweight browser automation by leveraging JD's
search endpoints directly.  It implements backoff, proxy rotation and
HTML parsing tailored to JD's markup so we can keep running in the
background with a lower risk of being blocked.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from dataclasses import dataclass
from typing import AsyncIterator, Iterable, List, Optional

import httpx

logger = logging.getLogger(__name__)


SEARCH_URL = "https://search.jd.com/s_new.php"
DETAIL_URL_TEMPLATE = "https://item.jd.com/{sku}.html"
MOBILE_DETAIL_URL_TEMPLATE = (
    "https://item.m.jd.com/product/{sku}.html"
)

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/124.0.0.0 Mobile/15E148 "
    "Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.6422.0 Mobile Safari/537.36",
]

DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "referer": "https://search.jd.com/",
}


@dataclass(slots=True)
class Product:
    """Product data returned by the scraper."""

    sku: str
    title: str
    detail_url: str
    brand: Optional[str] = None
    model: Optional[str] = None
    shop: Optional[str] = None


@dataclass(slots=True)
class ScraperConfig:
    """Configuration for :class:`JDScraper`."""

    keyword: str
    max_pages: int = 10
    page_size: int = 30
    max_tasks: int = 5
    request_timeout: float = 15.0
    request_retries: int = 3
    proxy_pool: Optional[Iterable[str]] = None
    base_delay: float = 1.0
    jitter: float = 0.3

    def build_headers(self) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        headers["user-agent"] = random.choice(USER_AGENTS)
        return headers


class JDScraper:
    """Scrape JD search results and product details using HTTP requests."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self._proxy_pool = list(config.proxy_pool or [])
        self._proxy_index = 0
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(config.max_tasks)

    async def __aenter__(self) -> "JDScraper":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.request_timeout,
                headers=self.config.build_headers(),
                http2=True,
            )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def scrape(self) -> List[Product]:
        """Scrape the configured keyword and return collected products."""

        products: List[Product] = []
        async for product in self.iter_products():
            products.append(product)
        return products

    async def iter_products(self) -> AsyncIterator[Product]:
        """Asynchronously yield :class:`Product` objects."""

        tasks = []
        page = 1
        while page <= self.config.max_pages:
            tasks.append(asyncio.create_task(self._scrape_page(page)))
            page += 1

        for task in asyncio.as_completed(tasks):
            try:
                for product in await task:
                    yield product
            except Exception as exc:  # pragma: no cover - propagation already logged
                logger.exception("Failed to scrape page", exc_info=exc)

    async def _scrape_page(self, page_number: int) -> List[Product]:
        html = await self._fetch_search_page(page_number)
        skus = list(self._parse_search_results(html))
        if not skus:
            return []

        products: List[Product] = []
        detail_tasks = [
            asyncio.create_task(self._fetch_product_detail(sku)) for sku in skus
        ]

        for task in asyncio.as_completed(detail_tasks):
            product = await task
            if product:
                products.append(product)
        return products

    async def _fetch_search_page(self, page_number: int) -> str:
        params = {
            "keyword": self.config.keyword,
            "enc": "utf-8",
            "page": str(page_number * 2 - 1),
            "s": str((page_number - 1) * self.config.page_size + 1),
            "scrolling": "y",
        }
        return await self._request(SEARCH_URL, params=params)

    async def _fetch_product_detail(self, sku: str) -> Optional[Product]:
        html = await self._request(DETAIL_URL_TEMPLATE.format(sku=sku))
        product = self._parse_product_detail(html, sku)

        # Some PC pages lazy-load parameter data; fallback to mobile page.
        if product.model is None:
            mobile_html = await self._request(
                MOBILE_DETAIL_URL_TEMPLATE.format(sku=sku)
            )
            mobile_product = self._parse_mobile_detail(mobile_html, sku)
            product.brand = product.brand or mobile_product.brand
            product.model = mobile_product.model
        return product

    async def _request(self, url: str, params: Optional[dict[str, str]] = None) -> str:
        if self._client is None:
            raise RuntimeError("Scraper has not been started")

        for attempt in range(1, self.config.request_retries + 1):
            proxy = self._choose_proxy()
            try:
                async with self._semaphore:
                    await asyncio.sleep(self._throttle_delay())
                    response = await self._client.get(url, params=params, proxy=proxy)
                response.raise_for_status()
                # Randomise headers each time to minimise fingerprinting
                self._client.headers["user-agent"] = random.choice(USER_AGENTS)
                return response.text
            except (httpx.HTTPError, asyncio.TimeoutError) as exc:
                wait_time = self._retry_delay(attempt)
                logger.warning(
                    "Request failed (attempt %s/%s): %s", attempt, self.config.request_retries, exc
                )
                await asyncio.sleep(wait_time)
        raise RuntimeError(f"Failed to fetch {url} after {self.config.request_retries} attempts")

    def _choose_proxy(self) -> Optional[str]:
        if not self._proxy_pool:
            return None
        proxy = self._proxy_pool[self._proxy_index % len(self._proxy_pool)]
        self._proxy_index += 1
        return proxy

    def _throttle_delay(self) -> float:
        jitter = random.uniform(-self.config.jitter, self.config.jitter)
        return max(0.0, self.config.base_delay + jitter)

    def _retry_delay(self, attempt: int) -> float:
        return min(30.0, (2 ** attempt) + random.random())

    @staticmethod
    def _parse_search_results(html: str) -> Iterable[str]:
        sku_pattern = re.compile(r'data-sku="(\d+)"')
        return sku_pattern.findall(html)

    @staticmethod
    def _parse_product_detail(html: str, sku: str) -> Product:
        brand = None
        model = None
        shop = None

        brand_match = re.search(r'品牌：<a[^>]*?>([^<]+)</a>', html)
        if brand_match:
            brand = brand_match.group(1).strip()

        # The model is often inside the "规格与包装" parameter list.
        parameter_match = re.search(
            r'<ul class="parameter2 p-parameter-list">(.*?)</ul>', html, re.S
        )
        if parameter_match:
            list_html = parameter_match.group(1)
            model_match = re.search(
                r'(?:能效网)?规格型号：</li>\s*<li title="([^"]+)"', list_html
            )
            if model_match:
                model = model_match.group(1).strip()

        shop_match = re.search(r'"shopName":"([^"]+)"', html)
        if shop_match:
            shop = shop_match.group(1)

        title_match = re.search(r'(?s)<title>(.*?)</title>', html)
        title = title_match.group(1).strip() if title_match else sku

        return Product(
            sku=sku,
            title=title,
            detail_url=DETAIL_URL_TEMPLATE.format(sku=sku),
            brand=brand,
            model=model,
            shop=shop,
        )

    @staticmethod
    def _parse_mobile_detail(html: str, sku: str) -> Product:
        brand = None
        model = None

        data_match = re.search(r'window\.pageConfig\s*=\s*(\{.*?\});', html, re.S)
        if data_match:
            try:
                data = json.loads(data_match.group(1))
                ext = data.get("product", {}).get("extend", {})
                brand = ext.get("brand") or data.get("product", {}).get("brand")
                model = ext.get("model") or ext.get("skuModel")
            except json.JSONDecodeError:
                pass

        if not model:
            model_match = re.search(r'规格型号</span>\s*<span>([^<]+)</span>', html)
            if model_match:
                model = model_match.group(1).strip()

        title_match = re.search(r'<title>(.*?)</title>', html)
        title = title_match.group(1).strip() if title_match else sku

        return Product(
            sku=sku,
            title=title,
            detail_url=MOBILE_DETAIL_URL_TEMPLATE.format(sku=sku),
            brand=brand,
            model=model,
        )


def demo(keyword: str = "冰箱", pages: int = 1) -> List[Product]:
    """Convenience function for manual testing."""

    config = ScraperConfig(keyword=keyword, max_pages=pages)
    scraper = JDScraper(config)

    async def _run() -> List[Product]:
        async with scraper:
            return await scraper.scrape()

    return asyncio.run(_run())


__all__ = [
    "JDScraper",
    "ScraperConfig",
    "Product",
    "demo",
]
