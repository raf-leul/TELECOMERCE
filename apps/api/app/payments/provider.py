"""
Payment provider abstraction (master instructions section 15). Business
logic in app.payments.router depends only on this interface, never on a
specific provider — so a real provider (Stripe, Chapa, etc.) can be added
later as another implementation without touching the checkout flow.

Only MockPaymentProvider exists right now (see mock_provider.py). It is
explicitly a development/testing sandbox — it never touches real money and
must never be presented as a production payment method. A real integration
would need, at minimum: provider API credentials (server-side secret,
never committed — see .env.example), a webhook signing-secret verification
step in handle_webhook (this mock skips signature verification entirely,
which a real provider must never do), and provider-specific request/response
shapes translated into the same PaymentIntent/PaymentResult shapes used
here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PaymentIntent:
    provider_reference: str
    status: str  # "pending" | "succeeded" | "failed"


@dataclass
class WebhookResult:
    provider_reference: str
    provider_event_id: str
    event_type: str
    status: str  # "succeeded" | "failed" | "refunded"
    raw_payload: dict


class PaymentProvider(ABC):
    @abstractmethod
    def create_payment(self, *, order_id: str, amount_cents: int) -> PaymentIntent:
        """Starts a payment for the given order/amount."""

    @abstractmethod
    def verify_payment(self, *, provider_reference: str) -> str:
        """Returns the current status of a payment at the provider."""

    @abstractmethod
    def handle_webhook(self, *, payload: dict) -> WebhookResult:
        """
        Parses/validates an inbound webhook payload into a normalized
        WebhookResult. A real provider implementation MUST verify the
        webhook signature here before trusting the payload — this mock
        does not, because there is no real signature to verify.
        """

    @abstractmethod
    def refund(self, *, provider_reference: str, amount_cents: int) -> None:
        """Issues a refund. Raises on failure."""
