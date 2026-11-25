"""JD Sports Romania (jdsports.ro) HTML product adapter."""

from app.scraping.adapters.base import AdapterSelectors, BaseHtmlAdapter


class JDSportsAdapter(BaseHtmlAdapter):
    """Adapter for extracting sneaker data from jdsports.ro product pages."""

    store = "jdsports"
    domain = "jdsports.ro"
    selectors = AdapterSelectors(
        title=("h1.product-title", "h1[itemprop='name']", ".product-info h1"),
        current_price=(
            ".price-box .current-price",
            ".product-info .current-price",
            ".current-price",
        ),
        original_price=(".price-box .old-price del", ".price-box .old-price", ".price-box s"),
        stock=(".stock-status", ".product-info .availability", "button.add-to-cart"),
        sku=(".sku-value", ".product-sku .value", "[itemprop='sku']"),
        image=("img.product-main-image", ".product-gallery img"),
        brand=(".product-brand", "[itemprop='brand']"),
    )
