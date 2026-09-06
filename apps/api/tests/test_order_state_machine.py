from app.orders.state_machine import is_valid_transition


def test_valid_transitions():
    assert is_valid_transition("pending_payment", "paid")
    assert is_valid_transition("pending_payment", "cancelled")
    assert is_valid_transition("paid", "processing")
    assert is_valid_transition("processing", "packed")
    assert is_valid_transition("packed", "shipped")
    assert is_valid_transition("shipped", "delivered")


def test_invalid_transitions_are_rejected():
    assert not is_valid_transition("pending_payment", "delivered")
    assert not is_valid_transition("pending_payment", "shipped")
    assert not is_valid_transition("delivered", "pending_payment")
    assert not is_valid_transition("cancelled", "paid")


def test_terminal_states_have_limited_or_no_outgoing_transitions():
    assert not is_valid_transition("cancelled", "processing")
    assert not is_valid_transition("refunded", "paid")


def test_unknown_status_is_rejected():
    assert not is_valid_transition("not_a_real_status", "paid")
