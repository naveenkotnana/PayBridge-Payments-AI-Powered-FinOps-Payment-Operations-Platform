from decimal import Decimal

import pytest

from app.services.cafe_menu import DEFAULT_CART, SNACK_CART, price_cart


def test_two_combo_totals():
    assert price_cart(DEFAULT_CART)[1] == Decimal("280.00")
    assert price_cart(SNACK_CART)[1] == Decimal("150.00")


def test_custom_cart_prices_are_server_owned():
    rows, total = price_cart({"masala_dosa": 1, "tea": 2})
    assert total == Decimal("180.00")
    assert sum(Decimal(row["subtotal"]) for row in rows) == total


@pytest.mark.parametrize("cart", [{}, {"free_item": 1}, {"tea": -1}, {"tea": 11}, {"tea": 1.5}, {"tea": True}])
def test_invalid_cart_is_rejected(cart):
    with pytest.raises(ValueError):
        price_cart(cart)
