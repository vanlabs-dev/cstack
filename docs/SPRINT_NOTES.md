# Sprint notes

## Sprint 1 fixture smoke (2026-04-27)

End-to-end run from a clean working tree. No live tenant touched.

### Commands

```sh
rm -rf data tenants.json
uv run cstack fixtures load-all
uv run cstack tenant list
uv run cstack extract ca-policies --tenant tenant-a
uv run cstack extract all --tenant tenant-b
```

### Observed counts

| Fixture  | ca_policies | named_locations | users | groups | directory_roles |
|----------|-------------|-----------------|-------|--------|------------------|
| tenant-a |           8 |               3 |    60 |     12 |                8 |
| tenant-b |           5 |               1 |    80 |     11 |                5 |
| tenant-c |          11 |               4 |    75 |     13 |                8 |

`tenant list` shows all three rows with `fixture=yes`.

### Raw outputs

The `extract` commands wrote raw JSON snapshots under
`data/raw/<tenant_id>/2026-04-27/`:

- tenant-a: `ca-policies.json` (single resource extracted)
- tenant-b: `ca-policies.json`, `named-locations.json`, `users.json`,
  `groups.json`, `directory-roles.json` (full extract via `extract all`)

### Database checks

- `SELECT tenant_id, COUNT(*) FROM ca_policies GROUP BY tenant_id` returns
  the same row counts as the metadata above.
- `SELECT * FROM ca_policies WHERE tenant_id = '<tenant-a id>' AND (id IS
  NULL OR display_name IS NULL)` returns zero rows. No nulls slip into
  non-nullable columns.

### Issues

None. The pipeline ran cleanly without warnings.

### Hand-off

Sprint 2 can build the audit logic against the DB shape produced by this
run. Expect to consume `ca_policies`, `named_locations`, `users`,
`groups`, and `directory_roles` for tenant-scoped queries.
