"""Ethical scraping engine, adapters, drift detection, and SKU deduplication."""

from app.scraping.deduplicator import (
    DeduplicationResult,
    normalize_sku,
    resolve_canonical_product,
    upsert_scraped_listing,
)
from app.scraping.drift_detector import (
    DriftCheckResult,
    ScrapeOutcome,
    check_plausibility,
    compute_title_similarity,
    record_scrape_outcome,
    save_failure_snapshot,
)
from app.scraping.polite_client import (
    CircuitBreakerOpenError,
    HourlyRateLimitExceededError,
    PoliteClientError,
    PoliteHttpClient,
    RobotsDisallowedError,
    UpstreamFetchError,
)
from app.scraping.price_parser import (
    ParsedPriceInfo,
    parse_availability,
    parse_price_info,
    parse_price_pair_from_text,
    parse_price_text,
)

__all__ = [
    "CircuitBreakerOpenError",
    "DeduplicationResult",
    "DriftCheckResult",
    "HourlyRateLimitExceededError",
    "ParsedPriceInfo",
    "PoliteClientError",
    "PoliteHttpClient",
    "RobotsDisallowedError",
    "ScrapeOutcome",
    "UpstreamFetchError",
    "check_plausibility",
    "compute_title_similarity",
    "normalize_sku",
    "parse_availability",
    "parse_price_info",
    "parse_price_pair_from_text",
    "parse_price_text",
    "record_scrape_outcome",
    "resolve_canonical_product",
    "save_failure_snapshot",
    "upsert_scraped_listing",
]
