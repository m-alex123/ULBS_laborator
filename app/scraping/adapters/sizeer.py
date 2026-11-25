"""Sizeer Romania (sizeer.ro) HTML product adapter."""

from app.scraping.adapters.base import AdapterSelectors, BaseHtmlAdapter


class SizeerAdapter(BaseHtmlAdapter):
    """Adapter for extracting sneaker data from sizeer.ro product pages."""

    store = "sizeer"
    domain = "sizeer.ro"
    selectors = AdapterSelectors(
        title=("h1.m-productInfo_name", ".m-productInfo h1"),
        current_price=(".m-productPrice_promo", ".m-productPrice_current"),
        original_price=(".m-productPrice_regular", ".m-productPrice s", ".m-productPrice del"),
        stock=(".m-availability", ".m-productInfo .availability"),
        sku=(".m-productInfo_code strong", ".m-productInfo_code .sku-code"),
        image=("img.js-product-image", ".m-productGallery img"),
        brand=(".m-productInfo_brand",),
    )
