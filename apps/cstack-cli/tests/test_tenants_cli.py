from pathlib import Path

from click.testing import CliRunner
from cstack_cli.main import cli

VALID_TENANT_ID = "11111111-1111-1111-1111-111111111111"
VALID_CLIENT_ID = "22222222-2222-2222-2222-222222222222"


def test_tenant_add_then_list(cli_env: dict[str, str], test_pfx: Path) -> None:
    runner = CliRunner()
    add = runner.invoke(
        cli,
        [
            "tenant",
            "add",
            "--tenant-id",
            VALID_TENANT_ID,
            "--display-name",
            "alpha",
            "--client-id",
            VALID_CLIENT_ID,
            "--cert-pfx-path",
            str(test_pfx),
        ],
        env=cli_env,
    )
    assert add.exit_code == 0, add.output

    listing = runner.invoke(cli, ["tenant", "list"], env=cli_env)
    assert listing.exit_code == 0, listing.output
    assert "alpha" in listing.output
    assert VALID_TENANT_ID in listing.output


def test_tenant_remove(cli_env: dict[str, str], test_pfx: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "tenant",
            "add",
            "--tenant-id",
            VALID_TENANT_ID,
            "--display-name",
            "alpha",
            "--client-id",
            VALID_CLIENT_ID,
            "--cert-pfx-path",
            str(test_pfx),
        ],
        env=cli_env,
    )

    remove = runner.invoke(cli, ["tenant", "remove", "alpha"], env=cli_env)
    assert remove.exit_code == 0, remove.output

    listing = runner.invoke(cli, ["tenant", "list"], env=cli_env)
    assert "alpha" not in listing.output


def test_tenant_create_api_key_persists_hash_only(cli_env: dict[str, str], test_pfx: Path) -> None:
    import hashlib
    import json

    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "tenant",
            "add",
            "--tenant-id",
            VALID_TENANT_ID,
            "--display-name",
            "alpha",
            "--client-id",
            VALID_CLIENT_ID,
            "--cert-pfx-path",
            str(test_pfx),
        ],
        env=cli_env,
    )

    result = runner.invoke(
        cli,
        ["tenant", "create-api-key", "alpha", "--label", "ci"],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output
    plaintext = result.output.strip().splitlines()[0]
    assert plaintext, "plaintext key should be on first stdout line"

    persisted = json.loads(Path(cli_env["CSTACK_TENANTS_FILE"]).read_text(encoding="utf-8"))
    assert plaintext not in json.dumps(persisted), "plaintext must never be persisted"
    expected_hash = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    keys = [k for t in persisted for k in t.get("api_keys", [])]
    assert any(k["key_hash"] == expected_hash and k["label"] == "ci" for k in keys)
