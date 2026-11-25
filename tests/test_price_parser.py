from decimal import Decimal

import pytest

from app.scraping.price_parser import (
    ParsedPriceInfo,
    parse_availability,
    parse_price_info,
    parse_price_pair_from_text,
    parse_price_text,
)


@pytest.mark.parametrize(
    ("raw", "expected_price", "expected_currency", "expected_starting"),
    [
        ("1.299,99 lei", Decimal("1299.99"), "RON", False),
        ("de la 49 RON", Decimal("49.00"), "RON", True),
        ("1 299 lei", Decimal("1299.00"), "RON", False),
        ("1\u00a0299,50 RON", Decimal("1299.50"), "RON", False),
        ("489,99 Lei", Decimal("489.99"), "RON", False),
        ("549.90 RON", Decimal("549.90"), "RON", False),
        ("450 lei", Decimal("450.00"), "RON", False),
        ("începând de la 199,90 lei", Decimal("199.90"), "RON", True),
    ],
)
def test_parse_price_text_romanian_formats(
    raw: str,
    expected_price: Decimal,
    expected_currency: str,
    expected_starting: bool,
) -> None:
    price, currency, is_starting = parse_price_text(raw)
    assert price == expected_price
    assert isinstance(price, Decimal)
    assert currency == expected_currency
    assert is_starting is expected_starting


def test_parse_price_info_with_strikethrough_discount() -> None:
    info = parse_price_info("549,99 lei", original_text="799,99 lei")
    assert isinstance(info, ParsedPriceInfo)
    assert info.current_price == Decimal("549.99")
    assert info.original_price == Decimal("799.99")
    assert info.currency == "RON"
    assert info.is_starting_from is False


def test_parse_price_info_discards_non_higher_original_price() -> None:
    equal_info = parse_price_info("549,99 RON", original_text="549,99 RON")
    assert equal_info.current_price == Decimal("549.99")
    assert equal_info.original_price is None

    lower_info = parse_price_info("549,99 RON", original_text="499,99 RON")
    assert lower_info.current_price == Decimal("549.99")
    assert lower_info.original_price is None


def test_parse_price_pair_from_combined_text() -> None:
    info = parse_price_pair_from_text("Preț vechi: 1.299,99 lei | Preț redus: 899,99 lei")
    assert info.current_price == Decimal("899.99")
    assert info.original_price == Decimal("1299.99")
    assert info.currency == "RON"


def test_parse_price_text_handles_empty_and_garbage() -> None:
    for raw in (None, "", "   ", "N/A", "---", "Preț indisponibil"):
        price, currency, is_starting = parse_price_text(raw)
        assert price is None
        assert currency == "RON"
        assert is_starting is False


def test_parse_price_text_preserves_zero_and_negative_values_for_drift_checks() -> None:
    zero_price, zero_curr, _ = parse_price_text("0 lei")
    neg_price, neg_curr, _ = parse_price_text("-50,00 RON")
    assert zero_price == Decimal("0.00")
    assert zero_curr == "RON"
    assert neg_price == Decimal("-50.00")
    assert neg_curr == "RON"


def test_parse_price_text_rejects_non_ron_currency() -> None:
    price, currency, _ = parse_price_text("129,99 EUR")
    assert price is None
    assert currency == "EUR"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Indisponibil", False),
        ("Momentan indisponibil", False),
        ("Stoc epuizat", False),
        ("Produs epuizat", False),
        ("Out of stock", False),
        ("În stoc", True),
        ("Disponibil online", True),
        ("Adaugă în coș", True),
        ("In stock", True),
        ("", None),
        (None, None),
        ("Vezi detalii", None),
    ],
)
def test_parse_availability_romanian_and_english_states(
    raw: str | None, expected: bool | None
) -> None:
    assert parse_availability(raw) is expected
