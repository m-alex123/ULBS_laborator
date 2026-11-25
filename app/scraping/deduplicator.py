"""Cross-site sneaker SKU normalization and fuzzy-title deduplication."""

from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import re
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import CanonicalProduct, ProductListing
from app.scraping.adapters.base import ScrapedProductData
from app.scraping.price_parser import strip_diacritics

_KNOWN_BRANDS: tuple[tuple[str, str], ...] = (
    ("new balance", "New Balance"),
    ("nike", "Nike"),
    ("jordan", "Nike"),
    ("adidas", "Adidas"),
    ("asics", "ASICS"),
    ("puma", "Puma"),
    ("converse", "Converse"),
    ("vans", "Vans"),
    ("reebok", "Reebok"),
    ("salomon", "Salomon"),
)
_BOILERPLATE_TOKENS = {
    "pantofi",
    "sport",
    "sneakers",
    "incaltaminte",
    "adidasi",
    "barbati",
    "femei",
    "copii",
    "unisex",
    "originals",
    "retro",
}
_AUTO_MATCH_THRESHOLD = 0.85
_UNCERTAIN_MATCH_THRESHOLD = 0.60


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    """Outcome of matching a scraped listing to a CanonicalProduct."""

    canonical_product: CanonicalProduct
    match_type: Literal["exact_sku", "fuzzy_auto", "uncertain_review", "new_canonical"]
    confidence: float
    needs_admin_confirmation: bool
    suggested_canonical_id: int | None = None


def sku_comparison_key(raw_sku: str | None) -> str | None:
    """Strip non-alphanumeric separators for cross-store SKU equality checks."""
    if not raw_sku or not isinstance(raw_sku, str):
        return None
    key = re.sub(r"[^A-Z0-9]", "", raw_sku.upper())
    return key or None


def normalize_sku(raw_sku: str | None) -> str | None:
    """Normalize manufacturer SKU into canonical uppercase representation."""
    if not raw_sku or not isinstance(raw_sku, str):
        return None
    cleaned = " ".join(raw_sku.strip().upper().split())
    if not cleaned:
        return None
    # e.g. "553558 403" / "553558_403" -> "553558-403"; "hq 8708" -> "HQ8708"
    tokens = re.split(r"[\s_-]+", cleaned)
    if len(tokens) == 2 and len(tokens[0]) >= 4 and len(tokens[1]) >= 2 and tokens[0][-1].isdigit():
        return f"{tokens[0]}-{tokens[1]}"
    return "".join(tokens)


def extract_brand(title: str | None, explicit_brand: str | None = None) -> str:
    """Infer canonical sneaker brand name from explicit metadata or title."""
    combined = strip_diacritics(f"{explicit_brand or ''} {title or ''}").lower()
    for needle, canonical_brand in _KNOWN_BRANDS:
        if re.search(rf"\b{re.escape(needle)}\b", combined):
            return canonical_brand
    if explicit_brand and explicit_brand.strip():
        return explicit_brand.strip().title()
    return "Sneakers"


def _core_tokens(title: str, sku: str | None = None) -> list[str]:
    folded = strip_diacritics(title).lower()
    tokens = re.findall(r"[a-z0-9]+", folded)
    sku_key = (sku_comparison_key(sku) or "").lower()
    filtered = [
        tok
        for tok in tokens
        if tok not in _BOILERPLATE_TOKENS and (not sku_key or tok not in sku_key)
    ]
    return filtered or tokens


def _title_similarity(title_a: str, title_b: str, sku_a: str | None = None, sku_b: str | None = None) -> float:
    tokens_a = _core_tokens(title_a, sku_a)
    tokens_b = _core_tokens(title_b, sku_b)
    if not tokens_a or not tokens_b:
        return 0.0
    seq_ratio = SequenceMatcher(None, " ".join(tokens_a), " ".join(tokens_b)).ratio()
    set_a, set_b = set(tokens_a), set(tokens_b)
    jaccard = len(set_a & set_b) / len(set_a | set_b)
    return round(0.6 * seq_ratio + 0.4 * jaccard, 4)


def _provisional_sku(scraped: ScrapedProductData) -> str:
    normalized = normalize_sku(scraped.sku)
    if normalized:
        return normalized
    digest = hashlib.sha256(scraped.url.encode("utf-8")).hexdigest()[:8].upper()
    return f"UNVERIFIED-{scraped.store.upper()}-{digest}"


def resolve_canonical_product(
    db: Session,
    scraped: ScrapedProductData,
) -> DeduplicationResult:
    """Match a scraped product to an existing CanonicalProduct or create a new one."""
    candidates = db.scalars(
        select(CanonicalProduct).options(selectinload(CanonicalProduct.listings))
    ).all()

    scraped_sku_key = sku_comparison_key(scraped.sku)
    if scraped_sku_key:
        for candidate in candidates:
            if sku_comparison_key(candidate.sku) == scraped_sku_key:
                return DeduplicationResult(
                    canonical_product=candidate,
                    match_type="exact_sku",
                    confidence=1.0,
                    needs_admin_confirmation=False,
                    suggested_canonical_id=None,
                )

    scraped_brand = extract_brand(scraped.title, scraped.brand)
    scraped_title = scraped.title or scraped.url

    best_candidate: CanonicalProduct | None = None
    best_score = 0.0
    for candidate in candidates:
        score = _title_similarity(
            scraped_title,
            candidate.name,
            sku_a=scraped.sku,
            sku_b=candidate.sku,
        )
        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate is not None and best_score >= _UNCERTAIN_MATCH_THRESHOLD:
        same_brand = best_candidate.brand.lower() == scraped_brand.lower()
        store_slot_free = not any(
            lst.store == scraped.store for lst in best_candidate.listings
        )
        if best_score >= _AUTO_MATCH_THRESHOLD and same_brand and store_slot_free:
            return DeduplicationResult(
                canonical_product=best_candidate,
                match_type="fuzzy_auto",
                confidence=best_score,
                needs_admin_confirmation=False,
                suggested_canonical_id=None,
            )

        provisional = CanonicalProduct(
            name=scraped.title or best_candidate.name,
            brand=scraped_brand,
            sku=_provisional_sku(scraped),
            image_url=scraped.image_url,
        )
        db.add(provisional)
        db.flush()
        return DeduplicationResult(
            canonical_product=provisional,
            match_type="uncertain_review",
            confidence=best_score,
            needs_admin_confirmation=True,
            suggested_canonical_id=best_candidate.id,
        )

    created = CanonicalProduct(
        name=scraped.title or f"{scraped_brand} Sneakers",
        brand=scraped_brand,
        sku=_provisional_sku(scraped),
        image_url=scraped.image_url,
    )
    db.add(created)
    db.flush()
    return DeduplicationResult(
        canonical_product=created,
        match_type="new_canonical",
        confidence=1.0,
        needs_admin_confirmation=False,
        suggested_canonical_id=None,
    )


def upsert_scraped_listing(
    db: Session,
    scraped: ScrapedProductData,
) -> tuple[ProductListing, DeduplicationResult]:
    """Create or update a ProductListing linked to its deduplicated CanonicalProduct."""
    existing_by_url = db.scalar(
        select(ProductListing)
        .where(ProductListing.url == scraped.url)
        .options(selectinload(ProductListing.canonical_product))
    )
    if existing_by_url is not None:
        return existing_by_url, DeduplicationResult(
            canonical_product=existing_by_url.canonical_product,
            match_type="exact_sku",
            confidence=1.0,
            needs_admin_confirmation=existing_by_url.match_needs_review,
            suggested_canonical_id=existing_by_url.suggested_canonical_product_id,
        )

    dedup = resolve_canonical_product(db, scraped)
    existing_store_listing = db.scalar(
        select(ProductListing).where(
            ProductListing.canonical_product_id == dedup.canonical_product.id,
            ProductListing.store == scraped.store,
        )
    )
    if existing_store_listing is not None:
        return existing_store_listing, dedup

    listing = ProductListing(
        canonical_product_id=dedup.canonical_product.id,
        store=scraped.store,
        url=scraped.url,
        current_price=scraped.current_price,
        original_price=scraped.original_price,
        raw_title=scraped.title or dedup.canonical_product.name,
        image_url=scraped.image_url,
        currency=scraped.currency,
        in_stock=True if scraped.in_stock is None else scraped.in_stock,
        match_needs_review=dedup.needs_admin_confirmation,
        match_confidence=dedup.confidence,
        suggested_canonical_product_id=dedup.suggested_canonical_id,
    )
    db.add(listing)
    db.flush()
    return listing, dedup
