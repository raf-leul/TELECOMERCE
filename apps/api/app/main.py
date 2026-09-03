"""
TeleCommerce API entrypoint.

This is a modular monolith (see /docs/ARCHITECTURE.md). Feature modules
(products, cart, orders, ...) are added under app/ as they're built in later
stages. For now this exposes a health check and a minimal /me endpoint used
to verify the Supabase JWT-verification dependency end to end.
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.security import VerifiedUser, get_current_user
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me")
def me(user: VerifiedUser = Depends(get_current_user)) -> dict[str, str | None]:
    """
    Echoes back the identity extracted from a verified Supabase access
    token. Exists in this stage purely to prove the JWT-verification
    dependency works; real protected business endpoints arrive in later
    stages.
    """
    return {"id": user.id, "postgres_role": user.postgres_role}

