"""
Tests for bot.handlers.products. Telegram's Update/CallbackQuery objects
are mocked with unittest.mock.AsyncMock — no real Telegram API access is
needed or used. bot.services.api_client.make_api_client is monkeypatched
to return an httpx.Client wired to a MockTransport, so the handler's HTTP
calls to apps/api are also fully offline.
"""
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bot.handlers import products
from bot.services import api_client


def _make_update_with_callback(callback_data: str):
    update = MagicMock()
    query = AsyncMock()
    query.data = callback_data
    update.callback_query = query
    return update, query


@pytest.fixture
def fake_api(monkeypatch):
    """Yields a function to install a handler function for the mocked API."""

    def _install(handler):
        fake_client = httpx.Client(
            base_url="http://test-api", transport=httpx.MockTransport(handler)
        )
        monkeypatch.setattr(api_client, "make_api_client", lambda: fake_client)
        return fake_client

    return _install


async def test_browse_callback_shows_categories(fake_api):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": "c1", "name": "Electronics", "slug": "electronics", "parent_category_id": None}])

    fake_api(handler)
    update, query = _make_update_with_callback("browse")

    await products.browse_callback(update, context=MagicMock())

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited_once()
    args, kwargs = query.edit_message_text.call_args
    assert "category" in kwargs["reply_markup"].inline_keyboard[0][0].callback_data


async def test_browse_callback_handles_api_failure_gracefully():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network unreachable", request=request)

    fake_client = httpx.Client(base_url="http://test-api", transport=httpx.MockTransport(handler))

    import bot.services.api_client as api_client_module

    orig = api_client_module.make_api_client
    api_client_module.make_api_client = lambda: fake_client
    try:
        update, query = _make_update_with_callback("browse")
        await products.browse_callback(update, context=MagicMock())
        query.edit_message_text.assert_awaited_once()
        text = query.edit_message_text.call_args[0][0]
        assert "Couldn't load" in text
    finally:
        api_client_module.make_api_client = orig
        fake_client.close()


async def test_product_selected_callback_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    fake_client = httpx.Client(base_url="http://test-api", transport=httpx.MockTransport(handler))

    import bot.services.api_client as api_client_module

    orig = api_client_module.make_api_client
    api_client_module.make_api_client = lambda: fake_client
    try:
        update, query = _make_update_with_callback("product:does-not-exist")
        await products.product_selected_callback(update, context=MagicMock())
        text = query.edit_message_text.call_args[0][0]
        assert "no longer available" in text
    finally:
        api_client_module.make_api_client = orig
        fake_client.close()
