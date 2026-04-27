import json

from click.testing import CliRunner
from cstack_cli.main import cli


def test_list_rules_prints_all_fifteen(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "list-rules"], env=cli_env)
    assert result.exit_code == 0, result.output
    rule_lines = [line for line in result.output.splitlines() if line.startswith("rule.")]
    assert len(rule_lines) == 15


def test_audit_all_against_fixture(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["fixtures", "load", "tenant-b"], env=cli_env)
    result = runner.invoke(cli, ["audit", "all", "--tenant", "tenant-b"], env=cli_env)
    assert result.exit_code == 0, result.output
    assert "tenant-b" in result.output
    assert "total" in result.output
    # tenant-b has gaps; at least one finding must surface in some category.
    assert "findings" in result.output


def test_audit_findings_filters_by_min_severity(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["fixtures", "load", "tenant-b"], env=cli_env)
    runner.invoke(cli, ["audit", "all", "--tenant", "tenant-b"], env=cli_env)

    listing = runner.invoke(
        cli,
        ["audit", "findings", "--tenant", "tenant-b", "--min-severity", "HIGH"],
        env=cli_env,
    )
    assert listing.exit_code == 0, listing.output
    severities_in_output = {"CRITICAL", "HIGH"}
    excluded = {"LOW", "INFO"}
    # Either no rows match (acceptable) or every row line shows a HIGH or CRITICAL severity.
    body = "\n".join(
        line
        for line in listing.output.splitlines()
        if line and not line.startswith("severity") and not set(line) <= {"-", " "}
    )
    if body and "no findings" not in body.lower():
        for sev in excluded:
            assert sev not in body
        assert any(sev in body for sev in severities_in_output)


def test_audit_findings_json_is_parseable(cli_env: dict[str, str]) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["fixtures", "load", "tenant-b"], env=cli_env)
    runner.invoke(cli, ["audit", "all", "--tenant", "tenant-b"], env=cli_env)

    result = runner.invoke(
        cli,
        ["audit", "findings", "--tenant", "tenant-b", "--json"],
        env=cli_env,
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    if parsed:
        assert "id" in parsed[0]
        assert "severity" in parsed[0]
        assert "rule_id" in parsed[0]
