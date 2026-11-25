from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import CanonicalProduct, ProductListing
from app.scraping.adapters import get_adapter
from app.scraping.adapters.base import ScrapedProductData
from app.scraping.deduplicator import normalize_sku, upsert_scraped_listing

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_normalize_sku_handles_separators_spaces_and_case() -> None:
    assert normalize_sku("553558-403") == "553558-403"
    assert normalize_sku(" 553558 403 ") == "553558-403"
    assert normalize_sku("553558_403") == "553558-403"
    assert normalize_sku("hq 8708") == "HQ8708"
    assert normalize_sku("  ") is None
    assert normalize_sku(None) is None


def test_cross_site_deduplication_merges_all_three_stores_by_normalized_sku(
    db_session: Session,
) -> None:
    fixtures = [
        (
            "jdsports",
            "https://www.jdsports.ro/nike-air-jordan-1-low-university-blue-553558-403",
            "jdsports_product.html",
        ),
        (
            "sizeer",
            "https://sizeer.ro/nike-air-jordan-1-low-553558-403",
            "sizeer_product.html",
        ),
        (
            "buzzsneakers",
            "https://www.buzzsneakers.ro/pantofi-sport/nike-air-jordan-1-low-553558-403",
            "buzzsneakers_product.html",
        ),
    ]

    results = []
    for store, url, filename in fixtures:
        html = (FIXTURES_DIR / filename).read_text(encoding="utf-8")
        scraped = get_adapter(store).parse(html, url)
        listing, dedup = upsert_scraped_listing(db_session, scraped)
        results.append((listing, dedup))

    db_session.commit()

    canonical_ids = {listing.canonical_product_id for listing, _ in results}
    assert len(canonical_ids) == 1
    assert db_session.query(CanonicalProduct).count() == 1
    assert db_session.query(ProductListing).count() == 3
    assert results[0][1].match_type == "new_canonical"
    assert results[1][1].match_type == "exact_sku"
    assert results[2][1].match_type == "exact_sku"
    assert all(not listing.match_needs_review for listing, _ in results)


def test_missing_sku_high_similarity_auto_matches_and_uncertain_match_flags_admin_review(
    db_session: Session,
) -> None:
    canonical = CanonicalProduct(
        name="Adidas Originals Campus 00s Core Black",
        brand="Adidas",
        sku="HQ8708",
    )
    db_session.add(canonical)
    db_session.flush()
    db_session.add(
        ProductListing(
            canonical_product_id=canonical.id,
            store="jdsports",
            url="https://www.jdsports.ro/adidas-originals-campus-00s-hq8708",
            current_price=Decimal("499.99"),
            raw_title="Adidas Originals Campus 00s Core Black",
            in_stock=True,
        )
    )
    db_session.commit()

    # High similarity, same brand, missing SKU -> auto-attaches to existing CanonicalProduct
    high_sim_scraped = ScrapedProductData(
        store="sizeer",
        url="https://sizeer.ro/adidas-originals-campus-00s-core-black",
        title="Adidas Pantofi sport Originals Campus 00s Core Black",
        current_price=Decimal("479.99"),
        original_price=Decimal("549.99"),
        currency="RON",
        in_stock=True,
        image_url="https://sizeer.ro/media/campus.jpg",
        sku=None,
        brand="Adidas",
    )
    sizeer_listing, sizeer_dedup = upsert_scraped_listing(db_session, high_sim_scraped)
    db_session.commit()

    assert sizeer_dedup.match_type == "fuzzy_auto"
    assert sizeer_dedup.needs_admin_confirmation is False
    assert sizeer_listing.canonical_product_id == canonical.id
    assert sizeer_listing.match_needs_review is False

    # Uncertain partial match (truncated model name without full colorway, missing SKU) -> flagged for admin review
    uncertain_scraped = ScrapedProductData(
        store="buzzsneakers",
        url="https://www.buzzsneakers.ro/pantofi-sport/adidas-campus-00s-core",
        title="Adidas Pantofi sport Campus 00s Core",
        current_price=Decimal("459.99"),
        original_price=None,
        currency="RON",
        in_stock=True,
        image_url="https://www.buzzsneakers.ro/media/campus-core.jpg",
        sku=None,
        brand="Adidas",
    )
    buzz_listing, buzz_dedup = upsert_scraped_listing(db_session, uncertain_scraped)
    db_session.commit()

    assert buzz_dedup.match_type == "uncertain_review"
    assert buzz_dedup.needs_admin_confirmation is True
    assert buzz_listing.match_needs_review is True
    assert buzz_listing.suggested_canonical_product_id == canonical.id
    assert buzz_listing.canonical_product_id != canonical.id
    assert buzz_listing.match_confidence is not None
    assert 0.60 <= buzz_listing.match_confidence < 0.85


def test_unrelated_sneaker_creates_separate_canonical_product(db_session: Session) -> None:
    existing = CanonicalProduct(
        name="Nike Air Jordan 1 Low University Blue",
        brand="Nike",
        sku="553558-403",
    )
    db_session.add(existing)
    db_session.commit()

    unrelated = ScrapedProductData(
        store="buzzsneakers",
        url="https://www.buzzsneakers.ro/pantofi-sport/new-balance-550-bb550wt1",
        title="New Balance Pantofi sport 550 White Green",
        current_price=Decimal("599.99"),
        original_price=None,
        currency="RON",
        in_stock=True,
        image_url=None,
        sku="BB550WT1",
        brand="New Balance",
    )
    listing, dedup = upsert_scraped_listing(db_session, unrelated)
    db_session.commit()

    assert dedup.match_type == "new_canonical"
    assert dedup.needs_admin_confirmation is False
    assert listing.canonical_product_id != existing.id
    assert db_session.query(CanonicalProduct).count() == 2
