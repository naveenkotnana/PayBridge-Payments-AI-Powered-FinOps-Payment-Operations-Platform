"""Server-owned cafe menu prices for the ordering demonstration."""
import json
from decimal import Decimal

MENU = {
    "masala_dosa": ("Masala Dosa", Decimal("120.00")),
    "idli": ("Idli", Decimal("50.00")),
    "vada": ("Vada", Decimal("70.00")),
    "filter_coffee": ("Filter Coffee", Decimal("40.00")),
    "tea": ("Tea", Decimal("30.00")),
}
DEFAULT_CART = {"masala_dosa": 2, "filter_coffee": 1}
SNACK_CART = {"idli": 1, "vada": 1, "tea": 1}
EMPTY_CART = {item_id: 0 for item_id in MENU}


def price_cart(cart=None):
    cart = DEFAULT_CART if cart is None else cart
    if not isinstance(cart, dict) or any(key not in MENU for key in cart):
        raise ValueError("Choose items from the cafe menu.")
    rows = []
    total = Decimal("0.00")
    for key, (name, price) in MENU.items():
        qty = cart.get(key, 0)
        if type(qty) is not int or not 0 <= qty <= 10:
            raise ValueError("Each quantity must be a whole number from 0 to 10.")
        if qty:
            rows.append({"item_id": key, "name": name, "quantity": qty,
                         "unit_price": str(price), "subtotal": str(price * qty)})
            total += price * qty
    if not rows:
        raise ValueError("Select at least one item before paying.")
    return rows, total


def cart_json(rows):
    return json.dumps(rows, sort_keys=True)
