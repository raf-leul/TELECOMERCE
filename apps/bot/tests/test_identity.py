from bot.services.identity import cart_token_for_telegram_user


def test_same_telegram_user_always_gets_same_token():
    a = cart_token_for_telegram_user(123456789)
    b = cart_token_for_telegram_user(123456789)
    assert a == b


def test_different_telegram_users_get_different_tokens():
    a = cart_token_for_telegram_user(111)
    b = cart_token_for_telegram_user(222)
    assert a != b


def test_token_is_a_valid_uuid_string():
    import uuid

    token = cart_token_for_telegram_user(42)
    # Raises ValueError if not a valid UUID — this is the format
    # apps/api/app/cart/identity.py requires for X-Cart-Token.
    parsed = uuid.UUID(token)
    assert str(parsed) == token
