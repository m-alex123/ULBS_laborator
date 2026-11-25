"""Buzz Sneakers Romania (buzzsneakers.ro) HTML product adapter."""

from app.scraping.adapters.base import AdapterSelectors, BaseHtmlAdapter


class BuzzSneakersAdapter(BaseHtmlAdapter):
    """Adapter for extracting sneaker data from buzzsneakers.ro product pages."""

    store = "buzzsneakers"
    domain = "buzzsneakers.ro"
    selectors = AdapterSelectors(
        title=("h1.product-detail-title", ".product-detail-info h1"),
        current_price=(".product-prices .product-price-value", ".product-prices .current-price"),
        original_price=(".product-prices .prev-price", ".product-prices del", ".product-prices s"),
        stock=(".availability-badge", ".product-detail-info .stock-info"),
        sku=(".product-code-label .code", ".product-code-label em"),
        image=("img.product-detail-img", ".product-gallery-slider img"),
        brand=(".brand-name",),
    )
