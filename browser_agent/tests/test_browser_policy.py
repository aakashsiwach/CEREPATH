import pytest

from app.main import validate_public_url


@pytest.mark.parametrize("url", [
    "http://example.com",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "ftp://example.com/file",
])
def test_rejects_non_https_schemes(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


@pytest.mark.parametrize("url", [
    "https://user:password@example.com",
    "https://example.com:8443",
    "https://localhost",
    "https://metadata.google.internal",
    "https://service.internal",
    "https://printer.local",
    "https://127.0.0.1",
    "https://10.0.0.1",
    "https://192.168.1.1",
    "https://169.254.169.254",
    "https://[::1]",
    "https://[fc00::1]",
])
def test_rejects_credentials_nonstandard_ports_and_private_destinations(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_accepts_https_hostname_for_proxy_side_dns_validation():
    validate_public_url("https://example.com/some/path")
