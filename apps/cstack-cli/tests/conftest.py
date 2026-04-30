from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Per-test environment variables that point cstack at scratch paths."""
    db_path = tmp_path / "cstack.duckdb"
    tenants_file = tmp_path / "tenants.json"
    data_dir = tmp_path / "data"
    env = {
        "CSTACK_DB_PATH": str(db_path),
        "CSTACK_TENANTS_FILE": str(tenants_file),
        "CSTACK_DATA_DIR": str(data_dir),
        "CSTACK_LOG_LEVEL": "WARNING",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    yield env


@pytest.fixture
def test_pfx(tmp_path: Path) -> Path:
    """Mint a self-signed unencrypted PFX bundle so ``tenant add`` tests can
    point ``--cert-pfx-path`` at a real PKCS#12 file without depending on
    a Windows cert store or external test fixtures."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "cstack-test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=b"cstack-test",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pfx_path = tmp_path / "tenant.pfx"
    pfx_path.write_bytes(pfx_bytes)
    return pfx_path
