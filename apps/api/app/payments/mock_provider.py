"""
MOCK PAYMENT PROVIDER — SANDBOX ONLY. NEVER PROCESSES REAL MONEY.

Used for local development and testing until a real provider (Stripe,
Chapa, etc.) is integrated — see app.payments.provider for what a real
implementation would additionally need (signature verification, real
credentials).

create_payment() always returns "pending" — this mock deliberately does
NOT auto-succeed, so the checkout flow's webhook-driven completion path
(POST /payments/webhook) is exercised the same way a real asynchronous
provider would drive it, rather than short-circuiting straight to
"succeeded" and never testing the webhook path at all.
"""
from __future__ import annotations

import uuid

from app.payments.provider import PaymentIntent, PaymentProvider, WebhookResult


class MockPaymentProvider(PaymentProvider):
    def create_payment(self, *, order_id: str, amount_cents: int) -> PaymentIntent:
        return PaymentIntent(
            provider_reference=f"mock_txn_{uuid.uuid4()}",
            status="pending",
        )

    def verify_payment(self, *, provider_reference: str) -> str:
        # A real provider would call out to check; the mock has no
        # external state to check against, so this always reports
        # "pending" — status changes only arrive via handle_webhook,
        # matching how most real providers actually work (webhook-driven,
        # not poll-driven).
        return "pending"

    def handle_webhook(self, *, payload: dict) -> WebhookResult:
        required = {"provider_event_id", "event_type", "provider_reference", "status"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"Webhook payload missing fields: {sorted(missing)}")

        return WebhookResult(
            provider_reference=payload["provider_reference"],
            provider_event_id=payload["provider_event_id"],
            event_type=payload["event_type"],
            status=payload["status"],
            raw_payload=payload,
        )

    def refund(self, *, provider_reference: str, amount_cents: int) -> None:
        # No-op in the mock — there's no real charge to reverse.
        return None
