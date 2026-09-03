"""
Role-based access control on top of the JWT-verification dependency in
app.auth.security. The Supabase access token's own "role" claim is just
the Postgres role (authenticated/anon/service_role) — see
docs/DECISIONS.md, "profiles.role vs JWT role claim are different things".
Real app-level authorization needs the profiles.role enum from Stage 2,
which this looks up via the service-role client (bypassing RLS, since the
profiles_select_own policy only lets a user read their own row, not an
arbitrary user's role for an authorization check).
"""
from __future__ import annotations

import httpx
from fastapi import Depends, HTTPException, status

from app.auth.security import VerifiedUser, get_current_user
from app.core.supabase_client import service_client


def get_profile_role(user_id: str) -> str | None:
    """
    Looks up profiles.role for a given user id. Returns None if no
    profile row exists (shouldn't normally happen given the Stage 2
    auto-provisioning trigger, but callers should not assume it can't).
    Raises HTTPException(503) if the backend can't be reached at all,
    rather than letting a raw connection error bubble up as an
    unhandled 500.
    """
    try:
        with service_client() as client:
            response = client.get(
                "/profiles",
                params={"id": f"eq.{user_id}", "select": "role"},
            )
            response.raise_for_status()
            rows = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "AUTHORIZATION_BACKEND_ERROR",
                    "message": "Could not verify authorization right now.",
                }
            },
        ) from exc

    if not rows:
        return None
    return rows[0]["role"]


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory. Usage:
        @router.post(..., dependencies=[Depends(require_role("admin", "owner"))])
    """

    def _dependency(user: VerifiedUser = Depends(get_current_user)) -> VerifiedUser:
        role = get_profile_role(user.id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No profile found for this user.",
            )
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}.",
            )
        return user

    return _dependency
