# Deterministic UUIDs for the bundled fixture tenants. Persisted in the
# metadata.json of each fixture and referenced from tests so callers can
# resolve a fixture by tenant_id without re-reading metadata.

FIXTURE_TENANT_A_ID = "00000000-aaaa-1111-1111-111111111111"
FIXTURE_TENANT_B_ID = "00000000-bbbb-2222-2222-222222222222"
FIXTURE_TENANT_C_ID = "00000000-cccc-3333-3333-333333333333"

# Stand-in app registration ID used by every fixture. Real tenants get a real
# client_id during tenant add; fixtures share this placeholder so the schema
# round-trips (TenantConfig requires a UUID).
FIXTURE_CLIENT_ID = "00000000-1111-2222-3333-aaaabbbbcccc"

# A 40-char hex string that satisfies the SHA-1-thumbprint validator without
# claiming to identify a real cert. Fixtures never authenticate to Graph.
FIXTURE_CERT_THUMBPRINT = "F" * 40
