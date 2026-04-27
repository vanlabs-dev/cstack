from click.testing import CliRunner
from cstack_cli.main import cli

VALID_TENANT_ID = "11111111-1111-1111-1111-111111111111"
VALID_CLIENT_ID = "22222222-2222-2222-2222-222222222222"
VALID_THUMB = "A" * 40


def test_tenant_add_then_list(cli_env: dict[str, str]) -> None:
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
            "--cert-thumbprint",
            VALID_THUMB,
        ],
        env=cli_env,
    )
    assert add.exit_code == 0, add.output

    listing = runner.invoke(cli, ["tenant", "list"], env=cli_env)
    assert listing.exit_code == 0, listing.output
    assert "alpha" in listing.output
    assert VALID_TENANT_ID in listing.output


def test_tenant_remove(cli_env: dict[str, str]) -> None:
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
            "--cert-thumbprint",
            VALID_THUMB,
        ],
        env=cli_env,
    )

    remove = runner.invoke(cli, ["tenant", "remove", "alpha"], env=cli_env)
    assert remove.exit_code == 0, remove.output

    listing = runner.invoke(cli, ["tenant", "list"], env=cli_env)
    assert "alpha" not in listing.output
