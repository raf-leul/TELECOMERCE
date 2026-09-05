"""
Cart identity resolution: every cart request is either from an
authenticated user (verified JWT) or a guest (a client-generated UUID sent
as the X-Cart-Token header). Exactly one cart exists per identity — see
supabase/migrations/0007_cart.sql's carts_exactly_one_owner constraint.

All cart data access goes through the service-role client. Authorization
is enforced here in application code (matching user_id/guest_token to the
resolved identity), not by RLS — see docs/DECISIONS.md for why.
"""
from __future__ import annotations

import uuid

import httpx
from fastapi import Depends, Header, HTTPException, status

from app.auth.security import VerifiedUser, get_optional_user


class CartIdentity:
    def __init__(self, user_id: str | None, guest_token: str | None):
        self.user_id = user_id
        self.guest_token = guest_token

    @property
    def filter_params(self) -> dict[str, str]:
        if self.user_id is not None:
            return {"user_id": f"eq.{self.user_id}"}
        return {"guest_token": f"eq.{self.guest_token}"}

    @property
    def owner_fields(self) -> dict[str, str | None]:
        return {"user_id": self.user_id, "guest_token": self.guest_token}


def resolve_cart_identity(
    user: VerifiedUser | None,
    x_cart_token: str | None,
) -> CartIdentity:
    if user is not None:
        return CartIdentity(user_id=user.id, guest_token=None)

    if not x_cart_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "MISSING_CART_IDENTITY",
                    "message": (
                        "Log in, or send an X-Cart-Token header (any "
                        "client-generated UUID) to use a guest cart."
                    ),
                }
            },
        )

    try:
        uuid.UUID(x_cart_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_CART_TOKEN",
                    "message": "X-Cart-Token must be a valid UUID.",
                }
            },
        ) from exc

    return CartIdentity(user_id=None, guest_token=x_cart_token)


def cart_identity_dependency(
    user: VerifiedUser | None = Depends(get_optional_user),
    x_cart_token: str | None = Header(default=None),
) -> CartIdentity:
    return resolve_cart_identity(user, x_cart_token)


def get_or_create_cart(client: httpx.Client, identity: CartIdentity) -> str:
    """Returns the cart id for this identity, creating one if needed."""
    response = client.get(
        "/carts", params={"select": "id", **identity.filter_params}
    )
    response.raise_for_status()
    rows = response.json()
    if rows:
        return rows[0]["id"]

    response = client.post(
        "/carts",
        json=identity.owner_fields,
        headers={"Prefer": "return=representation"},
    )
    response.raise_for_status()
    return response.json()[0]["id"]
