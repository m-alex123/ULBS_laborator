"""Base classes and shared BeautifulSoup4 extraction helpers for retailer adapters."""

from dataclasses import dataclass
from decimal import Decimal
import json
from typing import Protocol
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from app.scraping.price_parser import parse_availability, parse_price_info


@dataclass(frozen=True, slots=True)
class ScrapedProductData:
    """Normalized product attributes extracted from a retailer product page."""

    store: str
    url: str
    title: str | None
    current_price: Decimal | None
    original_price: Decimal | None
    currency: str
    in_stock: bool | None
    image_url: str | None
    sku: str | None
    brand: str | None = None


@dataclass(frozen=True, slots=True)
class AdapterSelectors:
    """Declarative CSS selector tuples for a retailer's product page."""

    title: tuple[str, ...]
    current_price: tuple[str, ...]
    original_price: tuple[str, ...]
    stock: tuple[str, ...]
    sku: tuple[str, ...]
    image: tuple[str, ...]
    brand: tuple[str, ...] = ()


class StoreAdapter(Protocol):
    """Contract implemented by every supported Romanian sneaker store adapter."""

    store: str
    domain: str

    def supports_url(self, url: str) -> bool:
        ...

    def parse(self, html: str, url: str) -> ScrapedProductData:
        ...


def _first_element(soup: BeautifulSoup, selectors: tuple[str, ...]) -> Tag | None:
    for selector in selectors:
        found = soup.select_one(selector)
        if found is not None:
            return found
    return None


def _first_text(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        found = soup.select_one(selector)
        if found is not None:
            text = " ".join(found.get_text(" ", strip=True).split())
            if text:
                return text
    return None


def _extract_image_url(soup: BeautifulSoup, selectors: tuple[str, ...], base_url: str) -> str | None:
    for selector in selectors:
        found = soup.select_one(selector)
        if found is None:
            continue
        for attr in ("data-src", "src", "content"):
            raw = found.get(attr)
            if isinstance(raw, str) and raw.strip():
                candidate = urljoin(base_url, raw.strip())
                if candidate.startswith("https://") and "placeholder" not in candidate.lower():
                    return candidate
    og_img = soup.select_one('meta[property="og:image"]')
    if og_img is not None:
        raw_og = og_img.get("content")
        if isinstance(raw_og, str) and raw_og.strip().startswith("https://"):
            return raw_og.strip()
    return None


def _extract_json_ld_product(soup: BeautifulSoup) -> dict[str, object]:
    for script in soup.select('script[type="application/ld+json"]'):
        raw_json = script.string or script.get_text()
        if not raw_json:
            continue
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                return item
    return {}


class BaseHtmlAdapter:
    """Shared BeautifulSoup4 extraction implementation driven by AdapterSelectors."""

    store: str
    domain: str
    selectors: AdapterSelectors

    def supports_url(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host == self.domain or host.endswith(f".{self.domain}")

    def parse(self, html: str, url: str) -> ScrapedProductData:
        soup = BeautifulSoup(html, "html.parser")
        json_ld = _extract_json_ld_product(soup)

        title = _first_text(soup, self.selectors.title)
        if not title and isinstance(json_ld.get("name"), str):
            title = json_ld["name"].strip() or None

        current_price_text = _first_text(soup, self.selectors.current_price)
        original_price_text = _first_text(soup, self.selectors.original_price)
        price_info = parse_price_info(current_price_text, original_price_text)

        stock_el = _first_element(soup, self.selectors.stock)
        in_stock: bool | None = None
        if stock_el is not None:
            data_avail = stock_el.get("data-available")
            if isinstance(data_avail, str) and data_avail.lower() in ("true", "false"):
                in_stock = data_avail.lower() == "true"
            if in_stock is None:
                in_stock = parse_availability(stock_el.get_text(" ", strip=True))

        sku = _first_text(soup, self.selectors.sku)
        if not sku and isinstance(json_ld.get("sku"), str):
            sku = json_ld["sku"].strip() or None

        brand = _first_text(soup, self.selectors.brand) if self.selectors.brand else None
        if not brand and isinstance(json_ld.get("brand"), dict):
            brand_name = json_ld["brand"].get("name")
            if isinstance(brand_name, str):
                brand = brand_name.strip() or None

        image_url = _extract_image_url(soup, self.selectors.image, url)

        return ScrapedProductData(
            store=self.store,
            url=url,
            title=title,
            current_price=price_info.current_price,
            original_price=price_info.original_price,
            currency=price_info.currency,
            in_stock=in_stock,
            image_url=image_url,
            sku=sku,
            brand=brand,
        )
