import pytest

from app.payments.mock_provider import MockPaymentProvider


def test_create_payment_returns_pending_not_auto_succeeded():
    provider = MockPaymentProvider()
    intent = provider.create_payment(order_id="order-1", amount_cents=1000)
    assert intent.status == "pending"
    assert intent.provider_reference.startswith("mock_txn_")


def test_create_payment_references_are_unique():
    provider = MockPaymentProvider()
    a = provider.create_payment(order_id="order-1", amount_cents=1000)
    b = provider.create_payment(order_id="order-1", amount_cents=1000)
    assert a.provider_reference != b.provider_reference


def test_handle_webhook_parses_valid_payload():
    provider = MockPaymentProvider()
    result = provider.handle_webhook(
        payload={
            "provider": "mock",
            "provider_event_id": "evt_1",
            "event_type": "payment.succeeded",
            "provider_reference": "mock_txn_abc",
            "status": "succeeded",
        }
    )
    assert result.provider_event_id == "evt_1"
    assert result.status == "succeeded"


def test_handle_webhook_rejects_incomplete_payload():
    provider = MockPaymentProvider()
    with pytest.raises(ValueError):
        provider.handle_webhook(payload={"provider_event_id": "evt_1"})
