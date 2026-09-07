from __future__ import annotations

from pydantic import BaseModel


class PaymentOut(BaseModel):
    id: str
    order_id: str
    provider: str
    status: str
    amount_cents: int
    provider_reference: str | None


class WebhookPayload(BaseModel):
    """
    Shape of an inbound provider webhook. Field names deliberately mirror
    what a real provider's webhook would carry (an event id, an event
    type, a reference to the payment/transaction, and a status) so
    swapping MockPaymentProvider for a real one later means adapting the
    provider's actual payload into this shape, not changing this schema.
    """

    provider: str
    provider_event_id: str
    event_type: str
    provider_reference: str
    status: str
