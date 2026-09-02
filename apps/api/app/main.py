"""
TeleCommerce API entrypoint.

This is a modular monolith (see /docs/ARCHITECTURE.md). Feature modules
(products, cart, orders, ...) are added under app/ as they're built in later
stages. For now this only exposes a health check so Stage 1 can be verified
end-to-end (process boots, responds, deployable).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
