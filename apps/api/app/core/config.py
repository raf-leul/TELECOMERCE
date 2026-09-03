"""
Application configuration.

Reads settings from environment variables (and a local .env file when present).
Never hardcode secrets here. See /.env.example at the repo root for the full
list of variables this project expects.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TeleCommerce API"
    environment: str = "development"

    # Supabase (public project URL is not secret; keys below must never be
    # the service-role key in this file's defaults).
    supabase_url: str = ""
    supabase_anon_key: str = ""
    # Backend-only, never sent to the client. Used to bypass RLS for
    # legitimate backend operations: admin writes to catalog tables (no
    # client-writable INSERT/UPDATE policy exists on purpose, per
    # docs/DATABASE.md) and reading another user's profiles.role for
    # authorization decisions (RLS only lets a user read their own row).
    supabase_service_role_key: str = ""

    # CORS
    cors_allow_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
