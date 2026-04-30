from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner
from cstack_cli.main import cli
from cstack_cli.tenants import save_tenants
from cstack_schemas import TenantConfig


def _live_tenant() -> TenantConfig:
    return TenantConfig(
        tenant_id="33333333-3333-3333-3333-333333333333",
        display_name="livealpha",
        client_id="44444444-4444-4444-4444-444444444444",
        cert_thumbprint="B" * 40,
        cert_subject="CN=cstack-test",
        added_at=datetime(2026, 1, 1, tzinfo=UTC),
        is_fixture=False,
    )


def test_verify_fixture_skips_live(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["fixtures", "load", "tenant-a"], env=cli_env)
    result = runner.invoke(cli, ["tenant", "verify", "tenant-a"], env=cli_env)
    assert result.exit_code == 0, result.output
    assert "fixture tenant" in result.output


def test_verify_live_tenant_calls_graph(cli_env: dict[str, str]) -> None:
    """Mock the credential and graph client so verify exercises the live path
    without touching a real tenant."""
    from pathlib import Path

    tenants_file = Path(cli_env["CSTACK_TENANTS_FILE"])
    save_tenants(tenants_file, [_live_tenant()])

    fake_org = MagicMock()
    fake_client = MagicMock()
    fake_client.organization.get = AsyncMock(return_value=fake_org)

    with (
        patch("cstack_cli.main.load_certificate_credential_for_tenant"),
        patch("cstack_cli.main.build_client", return_value=fake_client),
    ):
        runner = CliRunner()
        result = runner.invoke(cli, ["tenant", "verify", "livealpha"], env=cli_env)

    assert result.exit_code == 0, result.output
    assert "graph auth ok" in result.output
    fake_client.organization.get.assert_awaited_once()
