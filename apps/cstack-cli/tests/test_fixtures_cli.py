from click.testing import CliRunner
from cstack_cli.main import cli


def test_fixtures_list_contains_three(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["fixtures", "list"], env=cli_env)
    assert result.exit_code == 0, result.output
    for name in ("tenant-a", "tenant-b", "tenant-c"):
        assert name in result.output


def test_fixtures_load_then_extract(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    load = runner.invoke(cli, ["fixtures", "load", "tenant-a"], env=cli_env)
    assert load.exit_code == 0, load.output
    assert "ca_policies=8" in load.output

    extract = runner.invoke(cli, ["extract", "ca-policies", "--tenant", "tenant-a"], env=cli_env)
    assert extract.exit_code == 0, extract.output
    assert "ca-policies upserted=8" in extract.output


def test_fixtures_clear(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["fixtures", "load", "tenant-b"], env=cli_env)
    clear = runner.invoke(cli, ["fixtures", "clear", "tenant-b"], env=cli_env)
    assert clear.exit_code == 0, clear.output

    listing = runner.invoke(cli, ["tenant", "list"], env=cli_env)
    assert "tenant-b" not in listing.output


def test_fixtures_load_all_then_extract_all(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    load_all = runner.invoke(cli, ["fixtures", "load-all"], env=cli_env)
    assert load_all.exit_code == 0, load_all.output

    extract_all = runner.invoke(cli, ["extract", "all", "--tenant", "tenant-c"], env=cli_env)
    assert extract_all.exit_code == 0, extract_all.output
    assert "ca_policies=" in extract_all.output
    assert "users=" in extract_all.output
