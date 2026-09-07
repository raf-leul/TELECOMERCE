"""
Payment endpoints. POST /orders/{order_id}/pay starts a payment via the
configured provider (currently only MockPaymentProvider — see
app.payments.mock_provider for why it's sandbox-only). POST
/payments/webhook simulates what a real provider's webhook delivery would
look like, and is deliberately idempotent: the same provider_event_id
processed twice must not double-transition the order or create a second
payment record (master instructions section 28-29).

Idempotency mechanism: payment_events has a UNIQUE(provider,
provider_event_id) constraint (migration 0009). The webhook handler tries
to insert the event row FIRST; if PostgREST reports a conflict (the event
was already processed), it stops there and returns the current state
without touching orders/payments again. Only a successful (first-time)
insert proceeds to update payment/order status.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.security import VerifiedUser, get_current_user
from app.core.postgrest_deps import get_service_client
from app.core.postgrest_deps import translate_postgrest_error as _translate_postgrest_error
from app.orders.state_machine import is_valid_transition
from app.payments.mock_provider import MockPaymentProvider
from app.payments.provider import PaymentProvider
from app.payments.schemas import PaymentOut, WebhookPayload

router = APIRouter(tags=["payments"])


def get_payment_provider() -> PaymentProvider:
    """
    Single place that decides which PaymentProvider implementation is
    active. Only ever returns MockPaymentProvider today — swapping in a
    real provider later means adding a branch here (e.g. based on
    settings), not touching the endpoints below.
    """
    return MockPaymentProvider()


def _payment_row_to_out(row: dict) -> PaymentOut:
    return PaymentOut(
        id=row["id"],
        order_id=row["order_id"],
        provider=row["provider"],
        status=row["status"],
        amount_cents=row["amount_cents"],
        provider_reference=row.get("provider_reference"),
    )


@router.post(
    "/orders/{order_id}/pay",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_for_order(
    order_id: str,
    user: VerifiedUser = Depends(get_current_user),
    client: httpx.Client = Depends(get_service_client),
    provider: PaymentProvider = Depends(get_payment_provider),
) -> PaymentOut:
    try:
        order_response = client.get(
            "/orders",
            params={
                "select": "id,user_id,status,subtotal_cents",
                "id": f"eq.{order_id}",
                "limit": "1",
            },
        )
        order_response.raise_for_status()
        order_rows = order_response.json()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    if not order_rows or order_rows[0]["user_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

    order = order_rows[0]
    if order["status"] != "pending_payment":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "ORDER_NOT_PAYABLE",
                    "message": f"Order is '{order['status']}', not awaiting payment.",
                }
            },
        )

    intent = provider.create_payment(order_id=order_id, amount_cents=order["subtotal_cents"])

    try:
        create_response = client.post(
            "/payments",
            json={
                "order_id": order_id,
                "provider": "mock",
                "status": intent.status,
                "amount_cents": order["subtotal_cents"],
                "provider_reference": intent.provider_reference,
            },
            headers={"Prefer": "return=representation"},
        )
        create_response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    return _payment_row_to_out(create_response.json()[0])


@router.post("/payments/webhook", response_model=PaymentOut)
def payment_webhook(
    payload: WebhookPayload,
    client: httpx.Client = Depends(get_service_client),
    provider: PaymentProvider = Depends(get_payment_provider),
) -> PaymentOut:
    result = provider.handle_webhook(payload=payload.model_dump())

    try:
        payment_response = client.get(
            "/payments",
            params={
                "select": "id,order_id,provider,status,amount_cents,provider_reference",
                "provider_reference": f"eq.{result.provider_reference}",
                "limit": "1",
            },
        )
        payment_response.raise_for_status()
        payment_rows = payment_response.json()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    if not payment_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")

    payment_row = payment_rows[0]

    # Idempotency gate: attempt to record this event first. A unique
    # constraint violation means we've already processed this exact
    # event_id before — return the current state unchanged rather than
    # reprocessing.
    event_insert_response = client.post(
        "/payment_events",
        json={
            "payment_id": payment_row["id"],
            "provider": payload.provider,
            "provider_event_id": result.provider_event_id,
            "event_type": result.event_type,
            "raw_payload": result.raw_payload,
        },
    )
    if event_insert_response.status_code == 409:
        return _payment_row_to_out(payment_row)
    try:
        event_insert_response.raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    try:
        payment_update_response = client.patch(
            "/payments",
            params={"id": f"eq.{payment_row['id']}"},
            json={"status": result.status},
            headers={"Prefer": "return=representation"},
        )
        payment_update_response.raise_for_status()
        updated_payment = payment_update_response.json()[0]

        if result.status == "succeeded":
            order_response = client.get(
                "/orders",
                params={"select": "id,status", "id": f"eq.{payment_row['order_id']}", "limit": "1"},
            )
            order_response.raise_for_status()
            order_rows = order_response.json()
            if order_rows and is_valid_transition(order_rows[0]["status"], "paid"):
                client.patch(
                    "/orders",
                    params={"id": f"eq.{payment_row['order_id']}"},
                    json={"status": "paid"},
                ).raise_for_status()
                client.post(
                    "/order_status_history",
                    json={
                        "order_id": payment_row["order_id"],
                        "from_status": order_rows[0]["status"],
                        "to_status": "paid",
                        "changed_by": None,
                    },
                ).raise_for_status()
    except httpx.HTTPError as exc:
        raise _translate_postgrest_error(exc) from exc

    return _payment_row_to_out(updated_payment)
