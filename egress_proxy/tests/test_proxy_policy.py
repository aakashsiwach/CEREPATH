import ipaddress

import pytest

from app import parse_connect_target, validate_global_addresses


@pytest.mark.parametrize("line,expected", [
    ("CONNECT example.com:443 HTTP/1.1", ("example.com", 443)),
    ("CONNECT EXAMPLE.COM.:443 HTTP/1.1", ("example.com", 443)),
])
def test_accepts_https_connect_target(line, expected):
    assert parse_connect_target(line) == expected


@pytest.mark.parametrize("line", [
    "GET https://example.com/ HTTP/1.1",
    "CONNECT example.com:80 HTTP/1.1",
    "CONNECT localhost:443 HTTP/1.1",
    "CONNECT metadata.google.internal:443 HTTP/1.1",
    "CONNECT 127.0.0.1:443 HTTP/1.1",
    "CONNECT user:password@example.com:443 HTTP/1.1",
])
def test_rejects_unsafe_connect_target(line):
    with pytest.raises(ValueError):
        parse_connect_target(line)


@pytest.mark.parametrize("address", [
    "127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254",
    "::1", "fc00::1", "fe80::1", "224.0.0.1",
])
def test_rejects_non_global_ip_addresses(address):
    with pytest.raises(ValueError):
        validate_global_addresses([address])


def test_rejects_mixed_public_and_private_dns_answers():
    with pytest.raises(ValueError):
        validate_global_addresses(["93.184.216.34", "10.0.0.5"])


def test_accepts_public_address():
    result = validate_global_addresses(["93.184.216.34"])
    assert result == [ipaddress.ip_address("93.184.216.34")]
