"""
Tests the actual header-setting logic in app.core.supabase_client — this is
what test_products.py deliberately does NOT re-test (it overrides the
FastAPI dependency entirely and works with raw fake clients), so this file
exists to make sure anon_client()/service_client() themselves set the
correct auth headers, without making any real network call.
"""
import pytest

from app.core import supabase_client
from app.core.config import settings


def test_anon_client_sets_anon_apikey_and_bearer(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://test-project.supabase.co")
    monkeypatch.setattr(settings, "supabase_anon_key", "test-anon-key")

    with supabase_client.anon_client() as client:
        assert client.headers["apikey"] == "test-anon-key"
        assert client.headers["authorization"] == "Bearer test-anon-key"
        assert str(client.base_url) == "https://test-project.supabase.co/rest/v1/"


def test_service_client_sets_service_role_apikey_and_bearer(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://test-project.supabase.co")
    monkeypatch.setattr(
        settings, "supabase_service_role_key", "test-service-role-key"
    )

    with supabase_client.service_client() as client:
        assert client.headers["apikey"] == "test-service-role-key"
        assert client.headers["authorization"] == "Bearer test-service-role-key"


def test_service_client_without_key_configured_raises(monkeypatch):
    monkeypatch.setattr(settings, "supabase_service_role_key", "")

    with pytest.raises(RuntimeError):
        supabase_client.service_client()


def test_get_service_client_dependency_returns_503_not_500(monkeypatch):
    """
    Confirms the FastAPI dependency wrapper (app.core.postgrest_deps.
    get_service_client) translates the RuntimeError from a missing
    service-role key into a clean 503, rather than crashing with an
    unhandled 500 — a real bug found by booting the actual server without
    SUPABASE_SERVICE_ROLE_KEY set (see docs/DECISIONS.md).
    """
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(settings, "supabase_service_role_key", "")
    response = TestClient(app).get(
        "/cart", headers={"X-Cart-Token": "11111111-1111-1111-1111-111111111111"}
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "SERVICE_MISCONFIGURED"
