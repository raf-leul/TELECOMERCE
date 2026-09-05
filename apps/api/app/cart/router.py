"""
Cart endpoints. Works for both guests (X-Cart-Token header) and
authenticated users (Authorization bearer token) — see
app.cart.identity.resolve_cart_identity.

Pricing is always looked up server-side from the products table at both
add-time (to reject inactive/nonexistent products) and read-time (so a
price change is reflected without a stale copy sitting in cart_items) —
never trust a client-supplied price (master instructions section 27).
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.cart.identity import CartIdentity, cart_identity_dependency, get_or_create_cart
from app.cart.schemas import CartItemAdd, CartItemOut, CartItemUpdate, CartOut
from app.core.postgrest_deps import get_service_client
from app.core.postgrest_deps import translate_postgrest_error as _translate_postgrest_error

router = APIRouter(prefix="/cart", tags=["cart"])


def _fetch_cart_out(client: httpx.Client, cart_id: str) -> CartOut:
    response = client.get(
        "/cart_items",
        params={
            "select": "quantity,product_id,products(id,name,slug,price_cents,is_active)",
            "cart_id": f"eq.{cart_id}",
        },
    )
    response.raise_for_status()
    rows = response.json()

    items: list[CartItemOut] = []
    subtotal = 0
    for row in rows:
        product = row["products"]
        # A product could have been deactivated/deleted after being added;
        # skip it from the cart view rather than showing stale/wrong data.
        # (Cleaning these rows up is a Stage 6 concern once order creation
        # needs to reconcile the cart anyway — not done here to keep this
        # endpoint read-only and side-effect-free.)
        if product is None or not product["is_active"]:
            continue
        line_total = row["quantity"] * product["price_cents"]
        subtotal += line_total
        items.append(
            CartItemOut(
                product_id=product["id"],
                name=product["name"],
                slug=product["slug"],
                quantity=row["quantity"],
                unit_price_cents=product["price_cents"],
                line_total_cents=line_total,
            )
        )

    return CartOut(cart_id=cart_id, items=items, subtotal_cents=subtotal)


@router.get("", response_model=CartOut)
def get_cart(
    identity: CartIdentity = Depends(cart_identity_dependency),
    client: httpx.Client = Depends(get_service_client),
) -> CartOut:
    try:
        cart_id = get_or_create_cart(client, identity)
        return _fetch_cart_out(client, cart_id)
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def add_item(
    payload: CartItemAdd,
    identity: CartIdentity = Depends(cart_identity_dependency),
    client: httpx.Client = Depends(get_service_client),
) -> CartOut:
    try:
        product_response = client.get(
            "/products",
            params={
                "select": "id,is_active",
                "id": f"eq.{payload.product_id}",
                "limit": "1",
            },
        )
        product_response.raise_for_status()
        product_rows = product_response.json()
        if not product_rows or not product_rows[0]["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or unavailable.",
            )

        cart_id = get_or_create_cart(client, identity)

        existing_response = client.get(
            "/cart_items",
            params={
                "select": "id,quantity",
                "cart_id": f"eq.{cart_id}",
                "product_id": f"eq.{payload.product_id}",
                "limit": "1",
            },
        )
        existing_response.raise_for_status()
        existing_rows = existing_response.json()

        if existing_rows:
            new_quantity = existing_rows[0]["quantity"] + payload.quantity
            update_response = client.patch(
                "/cart_items",
                params={"id": f"eq.{existing_rows[0]['id']}"},
                json={"quantity": new_quantity},
            )
            update_response.raise_for_status()
        else:
            create_response = client.post(
                "/cart_items",
                json={
                    "cart_id": cart_id,
                    "product_id": payload.product_id,
                    "quantity": payload.quantity,
                },
            )
            create_response.raise_for_status()

        return _fetch_cart_out(client, cart_id)
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc


@router.patch("/items/{product_id}", response_model=CartOut)
def update_item(
    product_id: str,
    payload: CartItemUpdate,
    identity: CartIdentity = Depends(cart_identity_dependency),
    client: httpx.Client = Depends(get_service_client),
) -> CartOut:
    try:
        cart_id = get_or_create_cart(client, identity)
        response = client.patch(
            "/cart_items",
            params={"cart_id": f"eq.{cart_id}", "product_id": f"eq.{product_id}"},
            json={"quantity": payload.quantity},
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
        if not response.json():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not in cart.",
            )
        return _fetch_cart_out(client, cart_id)
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc


@router.delete("/items/{product_id}", response_model=CartOut)
def remove_item(
    product_id: str,
    identity: CartIdentity = Depends(cart_identity_dependency),
    client: httpx.Client = Depends(get_service_client),
) -> CartOut:
    try:
        cart_id = get_or_create_cart(client, identity)
        response = client.delete(
            "/cart_items",
            params={"cart_id": f"eq.{cart_id}", "product_id": f"eq.{product_id}"},
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
        if not response.json():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not in cart.",
            )
        return _fetch_cart_out(client, cart_id)
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc
