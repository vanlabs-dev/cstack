"""Shared fixtures for the signalguard-api test suite.

The conftest spins up a fresh DuckDB and tenants.json under tmp_path, builds
a FastAPI app via the factory with those settings, and exposes an httpx
AsyncClient wired through asgi-lifespan so the lifespan startup runs (which
the bare-FastAPI test client skips for some routers).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from cstack_schemas import TenantApiKey, TenantConfig
from cstack_storage import connection_scope, register_tenant, run_migrations
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from signalguard_api.config import Settings
from signalguard_api.main import create_app

DEV_KEY = "dev-key-for-tests-only"
TENANT_A = "00000000-aaaa-1111-1111-111111111111"
TENANT_B = "00000000-bbbb-2222-2222-222222222222"
TENANT_A_KEY_PLAIN = "tenant-a-plain-key-abc"
TENANT_B_KEY_PLAIN = "tenant-b-plain-key-xyz"


def _hash(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _seed_tenants(tenants_file: Path) -> list[TenantConfig]:
    now = datetime.now(UTC)
    tenants: list[TenantConfig] = [
        TenantConfig(
            tenant_id=TENANT_A,
            display_name="tenant-a",
            client_id="00000000-1111-2222-3333-aaaabbbbcccc",
            cert_thumbprint="A" * 40,
            cert_subject="CN=cstack-fixture-tenant-a",
            added_at=now,
            is_fixture=True,
            api_keys=[TenantApiKey(key_hash=_hash(TENANT_A_KEY_PLAIN), label="ci", created_at=now)],
        ),
        TenantConfig(
            tenant_id=TENANT_B,
            display_name="tenant-b",
            client_id="00000000-1111-2222-3333-aaaabbbbcccc",
            cert_thumbprint="B" * 40,
            cert_subject="CN=cstack-fixture-tenant-b",
            added_at=now,
            is_fixture=True,
            api_keys=[TenantApiKey(key_hash=_hash(TENANT_B_KEY_PLAIN), label="ci", created_at=now)],
        ),
    ]
    tenants_file.parent.mkdir(parents=True, exist_ok=True)
    tenants_file.write_text(
        json.dumps([t.model_dump(mode="json") for t in tenants], indent=2),
        encoding="utf-8",
    )
    return tenants


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Per-test Settings backed by a tmp_path data dir.

    ``mlflow_tracking_uri`` is left at the default (None) so the lifespan
    skips the explicit MLflow configure step; tests that need MLflow set it
    themselves with a Path.as_uri() value, which avoids the Windows
    ``file://drive:`` parser quirk.
    """
    return Settings(
        db_path=tmp_path / "cstack.duckdb",
        tenants_file=tmp_path / "tenants.json",
        mlflow_tracking_uri=None,
        dev_api_key=DEV_KEY,
        cors_allowed_origins=["http://localhost:3000"],
        log_level="WARNING",
    )


@pytest.fixture
def seeded_tenants(settings: Settings) -> list[TenantConfig]:
    tenants = _seed_tenants(settings.tenants_file)
    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        for t in tenants:
            register_tenant(conn, t)
    return tenants


@pytest.fixture
def app(settings: Settings, seeded_tenants: list[TenantConfig]) -> FastAPI:
    """Build the API with test settings injected via dependency override.

    ``create_app`` stores the settings on ``app.state``, but
    ``require_api_key`` resolves them through ``Depends(get_settings)``,
    which is lru_cached. The override below ensures every dependency sees
    the per-test settings.
    """
    _ = seeded_tenants
    from signalguard_api.config import get_settings

    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac,
    ):
        yield ac


@pytest.fixture
def fixture_corpus(settings: Settings) -> dict[str, Any]:
    """Hydrate tenant-b's bundled CA fixture so audit/findings tests have data.

    Loaded lazily (only when a test pulls this fixture) so tests that just
    poke at auth do not pay the load cost.
    """
    from cstack_fixtures import load_fixture

    with connection_scope(settings.db_path) as conn:
        run_migrations(conn)
        result = load_fixture("tenant-b", conn)
    return {"tenant_b_load": result}
