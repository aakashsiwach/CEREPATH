import pytest

from app.main import validate_public_url


def test_rejects_non_http_schemes():
    with pytest.raises(ValueError):
        validate_public_url("file:///etc/passwd")
    with pytest.raises(ValueError):
        validate_public_url("javascript:alert(1)")


def test_rejects_embedded_credentials_and_nonstandard_ports():
    with pytest.raises(ValueError):
        validate_public_url("https://user:password@example.com")
    with pytest.raises(ValueError):
        validate_public_url("https://example.com:8443")


def test_rejects_loopback_and_private_ip_addresses():
    for address in ("127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254", "::1"):
        with pytest.raises(ValueError):
            validate_public_url(f"http://{address}")


def test_rejects_local_hostnames():
    for host in ("localhost", "printer.local", "service.internal", "box.test"):
        with pytest.raises(ValueError):
            validate_public_url(f"http://{host}")


def test_accepts_https_when_dns_resolves_to_public_addresses(monkeypatch):
    monkeypatch.setattr("app.main._resolve_public_host", lambda host: None)
    validate_public_url("https://example.com/some/path")
