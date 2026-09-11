"""
The bot's ONLY path to product/cart/order/payment data is apps/api — see
master instructions section 16 ("the bot is not a separate store"). No
handler in this package talks to Supabase directly or reimplements
pricing/inventory/order logic; every function here is a thin wrapper
around an HTTP call to the same backend the web app uses.
"""
from __future__ import annotations

import os

import httpx


def _api_base_url() -> str:
    return os.environ.get("API_BASE_URL", "http://localhost:8000")


def list_categories(client: httpx.Client) -> list[dict]:
    response = client.get("/categories")
    response.raise_for_status()
    return response.json()


def list_products(client: httpx.Client) -> list[dict]:
    response = client.get("/products")
    response.raise_for_status()
    return response.json()


def get_product(client: httpx.Client, slug: str) -> dict | None:
    response = client.get(f"/products/{slug}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def get_cart(client: httpx.Client, cart_token: str) -> dict:
    response = client.get("/cart", headers={"X-Cart-Token": cart_token})
    response.raise_for_status()
    return response.json()


def add_to_cart(
    client: httpx.Client, cart_token: str, product_id: str, quantity: int = 1
) -> dict:
    response = client.post(
        "/cart/items",
        headers={"X-Cart-Token": cart_token},
        json={"product_id": product_id, "quantity": quantity},
    )
    response.raise_for_status()
    return response.json()


def remove_from_cart(client: httpx.Client, cart_token: str, product_id: str) -> dict:
    response = client.delete(
        f"/cart/items/{product_id}", headers={"X-Cart-Token": cart_token}
    )
    response.raise_for_status()
    return response.json()


def create_order(client: httpx.Client, access_token: str) -> dict:
    """
    Requires an authenticated access_token (Stage 6/8 decision: checkout
    requires login, no guest checkout yet — see docs/DECISIONS.md). The
    bot's account-linking flow (mapping a Telegram user to a logged-in
    Supabase session) is deferred; see the Telegram-account-linking gap
    noted in docs/DECISIONS.md and NEXT_TASK.md.
    """
    response = client.post(
        "/orders", headers={"Authorization": f"Bearer {access_token}"}
    )
    response.raise_for_status()
    return response.json()


def pay_order(client: httpx.Client, access_token: str, order_id: str) -> dict:
    response = client.post(
        f"/orders/{order_id}/pay",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    return response.json()


def list_orders(client: httpx.Client, access_token: str) -> list[dict]:
    response = client.get(
        "/orders", headers={"Authorization": f"Bearer {access_token}"}
    )
    response.raise_for_status()
    return response.json()


def make_api_client() -> httpx.Client:
    return httpx.Client(base_url=_api_base_url(), timeout=10.0)
