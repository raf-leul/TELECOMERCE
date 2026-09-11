"""
Maps a Telegram user id to a stable UUID used as the X-Cart-Token guest
identity for apps/api's cart endpoints (see
apps/api/app/cart/identity.py). Using uuid5 (deterministic, namespace +
name) means the same Telegram user always gets the same cart token across
messages/sessions without needing to store a mapping table ourselves —
the token is *derived*, not looked up.

This is explicitly a guest cart, not an authenticated one — see
docs/DECISIONS.md, "Telegram account linking deferred". A Telegram user
who wants an authenticated cart/order history tied to a real account has
no way to do that yet; this is the documented gap for a future stage.
"""
from __future__ import annotations

import uuid

# Fixed, arbitrary namespace UUID for this application's Telegram-id
# derivation. Must never change once real users depend on it — changing
# it would silently give every existing Telegram user a new, empty cart.
TELECOMMERCE_TELEGRAM_NAMESPACE = uuid.UUID("6f6e65e0-2c1a-4c1e-9d9b-1a2b3c4d5e6f")


def cart_token_for_telegram_user(telegram_user_id: int) -> str:
    return str(
        uuid.uuid5(TELECOMMERCE_TELEGRAM_NAMESPACE, str(telegram_user_id))
    )
