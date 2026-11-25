from decimal import Decimal
from pathlib import Path

import pytest

from app.scraping.adapters import get_adapter, get_adapter_for_url
from app.scraping.adapters.base import ScrapedProductData

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_jdsports_adapter_parses_offline_fixture() -> None:
    html = (FIXTURES_DIR / "jdsports_product.html").read_text(encoding="utf-8")
    url = "https://www.jdsports.ro/nike-air-jordan-1-low-university-blue-553558-403"
    adapter = get_adapter_for_url(url)
    assert adapter.store == "jdsports"

    data = adapter.parse(html, url)
    assert isinstance(data, ScrapedProductData)
    assert data.store == "jdsports"
    assert data.title == "Nike Air Jordan 1 Low 'University Blue' Bărbați"
    assert data.current_price == Decimal("489.99")
    assert data.original_price == Decimal("599.99")
    assert data.currency == "RON"
    assert data.in_stock is True
    assert data.sku == "553558-403"
    assert (
        data.image_url
        == "https://www.jdsports.ro/media/catalog/product/cache/nike-air-jordan-1-low-university-blue-553558-403.jpg"
    )


def test_sizeer_adapter_parses_offline_fixture() -> None:
    html = (FIXTURES_DIR / "sizeer_product.html").read_text(encoding="utf-8")
    url = "https://sizeer.ro/nike-air-jordan-1-low-553558-403"
    adapter = get_adapter_for_url(url)
    assert adapter.store == "sizeer"

    data = adapter.parse(html, url)
    assert data.store == "sizeer"
    assert data.title == "Jordan Air 1 Low University Blue 553558-403"
    assert data.current_price == Decimal("529.99")
    assert data.original_price == Decimal("599.99")
    assert data.currency == "RON"
    assert data.in_stock is True
    assert data.sku == "553558 403"
    assert (
        data.image_url
        == "https://sizeer.ro/media/catalog/product/cache/nike-air-jordan-1-low-553558-403.jpg"
    )


def test_buzzsneakers_adapter_parses_offline_fixture() -> None:
    html = (FIXTURES_DIR / "buzzsneakers_product.html").read_text(encoding="utf-8")
    url = "https://www.buzzsneakers.ro/pantofi-sport/nike-air-jordan-1-low-553558-403"
    adapter = get_adapter_for_url(url)
    assert adapter.store == "buzzsneakers"

    data = adapter.parse(html, url)
    assert data.store == "buzzsneakers"
    assert data.title == "Nike Pantofi sport Air Jordan 1 Low 553558-403"
    assert data.current_price == Decimal("1049.99")
    assert data.original_price == Decimal("1299.00")
    assert data.currency == "RON"
    assert data.in_stock is True
    assert data.sku == "553558-403"
    assert (
        data.image_url
        == "https://www.buzzsneakers.ro/files/thumbs/files/images/slike_proizvoda/media/553/553558-403/553558-403.jpg"
    )


def test_adapter_handles_out_of_stock_and_unsupported_domains() -> None:
    oos_html = """
    <html><body>
      <h1 class="product-title">Adidas Campus 00s</h1>
      <span class="current-price">479,99 lei</span>
      <div class="stock-status">Momentan indisponibil</div>
      <span class="sku-value">HQ8708</span>
    </body></html>
    """
    adapter = get_adapter("jdsports")
    data = adapter.parse(oos_html, "https://www.jdsports.ro/adidas-campus-00s-hq8708")
    assert data.in_stock is False
    assert data.current_price == Decimal("479.99")

    with pytest.raises(ValueError):
        get_adapter_for_url("https://www.zara.com/ro/ro/sneakers-p123.html")
