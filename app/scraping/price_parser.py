"""Pure, side-effect-free Romanian e-commerce price and availability parser."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
import unicodedata

_STARTING_PREFIX_RE = re.compile(
    r"\b(?:incepand\s+de\s+la|de\s+la|from)\b", re.IGNORECASE
)
_NUMBER_RE = re.compile(
    r"(?P<sign>-)?\s*(?P<num>\d+(?:[.\s\u00a0,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
)
_NON_RON_CURRENCIES: tuple[tuple[str, str], ...] = (
    ("eur", "EUR"),
    ("€", "EUR"),
    ("usd", "USD"),
    ("$", "USD"),
    ("gbp", "GBP"),
    ("£", "GBP"),
)
_RON_MARKERS = ("lei", "ron")

_OUT_OF_STOCK_PHRASES = (
    "momentan indisponibil",
    "indisponibil",
    "stoc epuizat",
    "produs epuizat",
    "epuizat",
    "stoc 0",
    "out of stock",
    "unavailable",
    "sold out",
)
_IN_STOCK_PHRASES = (
    "in stoc",
    "disponibil",
    "adauga in cos",
    "in stock",
    "available",
)


@dataclass(frozen=True, slots=True)
class ParsedPriceInfo:
    """Structured result of parsing current and optional original Romanian prices."""

    current_price: Decimal | None
    original_price: Decimal | None = None
    currency: str = "RON"
    is_starting_from: bool = False


def strip_diacritics(text: str) -> str:
    """Normalize Unicode string to ASCII-folded lowercase for resilient matching."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _detect_currency(text: str) -> str:
    lowered = text.lower()
    for token, code in _NON_RON_CURRENCIES:
        if token in ("€", "$", "£"):
            if token in lowered:
                return code
        elif re.search(rf"\b{re.escape(token)}\b", lowered):
            return code
    for marker in _RON_MARKERS:
        if re.search(rf"\b{marker}\b", lowered):
            return "RON"
    return "RON"


def _normalize_number_token(raw_num: str, sign: str | None) -> Decimal | None:
    cleaned = raw_num.replace("\u00a0", "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        # Romanian thousands dot + decimal comma: "1.299,99"
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = f"{parts[0]}.{parts[1]}"
        else:
            cleaned = cleaned.replace(",", "")
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = f"{parts[0]}.{parts[1]}"
        else:
            cleaned = cleaned.replace(".", "")

    if sign == "-":
        cleaned = f"-{cleaned}"
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_price_text(raw: str | None) -> tuple[Decimal | None, str, bool]:
    """Parse a single Romanian price string into (Decimal|None, currency, is_starting_from)."""
    if not raw or not isinstance(raw, str):
        return None, "RON", False

    text = raw.strip()
    if not text:
        return None, "RON", False

    folded = strip_diacritics(text)
    is_starting = bool(_STARTING_PREFIX_RE.search(folded))
    currency = _detect_currency(folded)
    if currency != "RON":
        return None, currency, is_starting

    match = _NUMBER_RE.search(text)
    if not match:
        return None, "RON", is_starting

    value = _normalize_number_token(match.group("num"), match.group("sign"))
    return value, "RON", is_starting


def parse_price_info(
    current_text: str | None,
    original_text: str | None = None,
) -> ParsedPriceInfo:
    """Parse current and optional strikethrough original price texts into ParsedPriceInfo."""
    current_price, currency, is_starting = parse_price_text(current_text)
    original_price: Decimal | None = None

    if original_text:
        parsed_orig, orig_currency, _ = parse_price_text(original_text)
        if (
            parsed_orig is not None
            and current_price is not None
            and orig_currency == currency
            and parsed_orig > current_price
        ):
            original_price = parsed_orig

    return ParsedPriceInfo(
        current_price=current_price,
        original_price=original_price,
        currency=currency,
        is_starting_from=is_starting,
    )


def parse_price_pair_from_text(combined_text: str | None) -> ParsedPriceInfo:
    """Extract current and optional original price from a single string with 1-2 prices."""
    if not combined_text or not isinstance(combined_text, str):
        return ParsedPriceInfo(current_price=None)

    folded = strip_diacritics(combined_text.strip())
    is_starting = bool(_STARTING_PREFIX_RE.search(folded))
    currency = _detect_currency(folded)
    if currency != "RON":
        return ParsedPriceInfo(current_price=None, currency=currency, is_starting_from=is_starting)

    values: list[Decimal] = []
    for match in _NUMBER_RE.finditer(combined_text):
        parsed = _normalize_number_token(match.group("num"), match.group("sign"))
        if parsed is not None:
            values.append(parsed)

    if not values:
        return ParsedPriceInfo(current_price=None, currency="RON", is_starting_from=is_starting)
    if len(values) == 1:
        return ParsedPriceInfo(
            current_price=values[0],
            original_price=None,
            currency="RON",
            is_starting_from=is_starting,
        )

    positive_values = [v for v in values if v > 0]
    if not positive_values:
        return ParsedPriceInfo(
            current_price=values[0],
            original_price=None,
            currency="RON",
            is_starting_from=is_starting,
        )

    current = min(positive_values)
    highest = max(positive_values)
    original = highest if highest > current else None
    return ParsedPriceInfo(
        current_price=current,
        original_price=original,
        currency="RON",
        is_starting_from=is_starting,
    )


def parse_availability(raw: str | None) -> bool | None:
    """Parse Romanian/English stock status text into True (in stock), False (out), or None."""
    if not raw or not isinstance(raw, str):
        return None
    normalized = " ".join(strip_diacritics(raw).lower().split())
    if not normalized:
        return None

    for phrase in _OUT_OF_STOCK_PHRASES:
        if phrase in normalized:
            return False
    for phrase in _IN_STOCK_PHRASES:
        if phrase in normalized:
            return True
    return None
