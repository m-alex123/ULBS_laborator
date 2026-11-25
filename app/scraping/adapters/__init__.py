"""Retailer adapter registry and URL routing."""

from urllib.parse import urlparse

from app.scraping.adapters.base import BaseHtmlAdapter, ScrapedProductData, StoreAdapter
from app.scraping.adapters.buzzsneakers import BuzzSneakersAdapter
from app.scraping.adapters.jdsports import JDSportsAdapter
from app.scraping.adapters.sizeer import SizeerAdapter

ADAPTERS: dict[str, StoreAdapter] = {
    "jdsports": JDSportsAdapter(),
    "sizeer": SizeerAdapter(),
    "buzzsneakers": BuzzSneakersAdapter(),
}


def get_adapter(store: str) -> StoreAdapter:
    """Return the StoreAdapter for a canonical store identifier."""
    normalized = store.strip().lower()
    if normalized not in ADAPTERS:
        raise ValueError(f"Unsupported store identifier: {store}")
    return ADAPTERS[normalized]


def get_adapter_for_url(url: str) -> StoreAdapter:
    """Resolve the matching StoreAdapter from a product URL's hostname."""
    host = urlparse(url).netloc.lower()
    for adapter in ADAPTERS.values():
        if adapter.supports_url(url):
            return adapter
    raise ValueError(f"Unsupported retailer domain: {host or url}")


__all__ = [
    "ADAPTERS",
    "BaseHtmlAdapter",
    "BuzzSneakersAdapter",
    "JDSportsAdapter",
    "ScrapedProductData",
    "SizeerAdapter",
    "StoreAdapter",
    "get_adapter",
    "get_adapter_for_url",
]
