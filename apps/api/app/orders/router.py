"""
Order endpoints. Checkout requires an authenticated user in this slice —
guest checkout is deferred (see docs/DECISIONS.md); a guest would need to
either register or log in before placing an order.

Order creation is the one place price authority really matters (master
instructions section 11's checkout flow): product prices are re-read from
`products.price_cents` at order-creation time and snapshotted into
`order_items`, never taken from the cart response or any client input.
The cart itself already snapshots nothing — it always reflects live
prices — so this is the first and only place a price becomes fixed.

All access goes through the service-role client, same pattern as cart:
authorization ("is this order yours") is enforced in application code by
comparing `orders.user_id` to the verified JWT's subject, not by RLS.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.rbac import require_role
from app.auth.security import VerifiedUser, get_current_user
from app.core.postgrest_deps import get_service_client
from app.core.postgrest_deps import translate_postgrest_error as _translate_postgrest_error
from app.orders.schemas import OrderItemOut, OrderOut, OrderStatusUpdate
from app.orders.state_machine import is_valid_transition

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_out_from_row(order_row: dict, item_rows: list[dict]) -> OrderOut:
    items = [
        OrderItemOut(
            product_id=item["product_id"],
            product_name=item["product_name"],
            unit_price_cents=item["unit_price_cents"],
            quantity=item["quantity"],
            line_total_cents=item["unit_price_cents"] * item["quantity"],
        )
        for item in item_rows
    ]
    return OrderOut(
        id=order_row["id"],
        status=order_row["status"],
        subtotal_cents=order_row["subtotal_cents"],
        items=items,
        created_at=order_row["created_at"],
    )


def _fetch_order_with_items(client: httpx.Client, order_id: str) -> tuple[dict, list[dict]] | None:
    order_response = client.get(
        "/orders",
        params={
            "select": "id,user_id,status,subtotal_cents,created_at",
            "id": f"eq.{order_id}",
            "limit": "1",
        },
    )
    order_response.raise_for_status()
    order_rows = order_response.json()
    if not order_rows:
        return None

    items_response = client.get(
        "/order_items",
        params={
            "select": "product_id,product_name,unit_price_cents,quantity",
            "order_id": f"eq.{order_id}",
        },
    )
    items_response.raise_for_status()
    return order_rows[0], items_response.json()


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    user: VerifiedUser = Depends(get_current_user),
    client: httpx.Client = Depends(get_service_client),
) -> OrderOut:
    try:
        cart_response = client.get(
            "/carts", params={"select": "id", "user_id": f"eq.{user.id}", "limit": "1"}
        )
        cart_response.raise_for_status()
        cart_rows = cart_response.json()
        if not cart_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "CART_EMPTY", "message": "Your cart is empty."}},
            )
        cart_id = cart_rows[0]["id"]

        cart_items_response = client.get(
            "/cart_items",
            params={
                "select": "quantity,product_id,products(id,name,price_cents,is_active)",
                "cart_id": f"eq.{cart_id}",
            },
        )
        cart_items_response.raise_for_status()
        cart_item_rows = cart_items_response.json()

        # Re-validate against the live catalog at the moment of purchase —
        # never trust that what's in the cart is still accurate (a product
        # could have been deactivated or repriced since it was added).
        order_items_payload = []
        subtotal = 0
        for row in cart_item_rows:
            product = row["products"]
            if product is None or not product["is_active"]:
                continue
            line_price = product["price_cents"]
            subtotal += line_price * row["quantity"]
            order_items_payload.append(
                {
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "unit_price_cents": line_price,
                    "quantity": row["quantity"],
                }
            )

        if not order_items_payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "CART_EMPTY",
                        "message": "Your cart has no available items.",
                    }
                },
            )

        order_response = client.post(
            "/orders",
            json={"user_id": user.id, "subtotal_cents": subtotal},
            headers={"Prefer": "return=representation"},
        )
        order_response.raise_for_status()
        order_row = order_response.json()[0]
        order_id = order_row["id"]

        for item in order_items_payload:
            item["order_id"] = order_id
        items_create_response = client.post(
            "/order_items",
            json=order_items_payload,
            headers={"Prefer": "return=representation"},
        )
        items_create_response.raise_for_status()
        created_items = items_create_response.json()

        client.post(
            "/order_status_history",
            json={
                "order_id": order_id,
                "from_status": None,
                "to_status": "pending_payment",
                "changed_by": user.id,
            },
        ).raise_for_status()

        # Cart is consumed by checkout — clear it so the next visit to
        # /cart starts fresh, matching typical e-commerce behavior.
        client.delete("/cart_items", params={"cart_id": f"eq.{cart_id}"}).raise_for_status()

        return _order_out_from_row(order_row, created_items)
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc


@router.get("", response_model=list[OrderOut])
def list_orders(
    user: VerifiedUser = Depends(get_current_user),
    client: httpx.Client = Depends(get_service_client),
) -> list[OrderOut]:
    try:
        response = client.get(
            "/orders",
            params={
                "select": "id,user_id,status,subtotal_cents,created_at",
                "user_id": f"eq.{user.id}",
                "order": "created_at.desc",
            },
        )
        response.raise_for_status()
        order_rows = response.json()

        results = []
        for order_row in order_rows:
            items_response = client.get(
                "/order_items",
                params={
                    "select": "product_id,product_name,unit_price_cents,quantity",
                    "order_id": f"eq.{order_row['id']}",
                },
            )
            items_response.raise_for_status()
            results.append(_order_out_from_row(order_row, items_response.json()))
        return results
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: str,
    user: VerifiedUser = Depends(get_current_user),
    client: httpx.Client = Depends(get_service_client),
) -> OrderOut:
    try:
        result = _fetch_order_with_items(client, order_id)
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    order_row, item_rows = result
    # Same 404 whether the order doesn't exist or belongs to someone else
    # — don't leak which order ids exist to a user who doesn't own them.
    if order_row["user_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    return _order_out_from_row(order_row, item_rows)


@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    dependencies=[Depends(require_role("admin", "owner", "staff"))],
)
def update_order_status(
    order_id: str,
    payload: OrderStatusUpdate,
    user: VerifiedUser = Depends(get_current_user),
    client: httpx.Client = Depends(get_service_client),
) -> OrderOut:
    try:
        result = _fetch_order_with_items(client, order_id)
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    order_row, _ = result
    current_status = order_row["status"]

    if not is_valid_transition(current_status, payload.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INVALID_STATUS_TRANSITION",
                    "message": f"Cannot transition from '{current_status}' to '{payload.status}'.",
                }
            },
        )

    try:
        update_response = client.patch(
            "/orders",
            params={"id": f"eq.{order_id}"},
            json={"status": payload.status},
            headers={"Prefer": "return=representation"},
        )
        update_response.raise_for_status()
        updated_order = update_response.json()[0]

        client.post(
            "/order_status_history",
            json={
                "order_id": order_id,
                "from_status": current_status,
                "to_status": payload.status,
                "changed_by": user.id,
            },
        ).raise_for_status()

        items_response = client.get(
            "/order_items",
            params={
                "select": "product_id,product_name,unit_price_cents,quantity",
                "order_id": f"eq.{order_id}",
            },
        )
        items_response.raise_for_status()
        return _order_out_from_row(updated_order, items_response.json())
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc
