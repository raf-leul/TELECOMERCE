"""
Order status state machine (master instructions section 13). Transitions
not listed here are rejected — an admin sending an arbitrary status string
cannot skip states.
"""
from __future__ import annotations

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending_payment": {"paid", "cancelled"},
    "paid": {"processing", "cancelled", "refunded"},
    "processing": {"packed", "cancelled"},
    "packed": {"shipped"},
    "shipped": {"delivered"},
    "delivered": {"refunded"},
    "cancelled": set(),
    "refunded": set(),
}

ALL_STATUSES = set(ALLOWED_TRANSITIONS.keys())


def is_valid_transition(from_status: str, to_status: str) -> bool:
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())
