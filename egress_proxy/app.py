"""HTTPS CONNECT-only egress proxy with DNS resolution and IP pinning."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

MAX_HEADER_BYTES = 16_384
CONNECT_TIMEOUT_SECONDS = 10
IDLE_TIMEOUT_SECONDS = 120


def _is_public_unicast(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast and not address.is_reserved


def parse_connect_target(request_line: str) -> tuple[str, int]:
    parts = request_line.strip().split()
    if len(parts) != 3 or parts[0].upper() != "CONNECT" or parts[2] not in {"HTTP/1.0", "HTTP/1.1"}:
        raise ValueError("Only HTTP CONNECT requests are supported")

    authority = parts[1]
    parsed = urlsplit(f"//{authority}")
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError("Invalid CONNECT authority")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid CONNECT port") from exc
    if port != 443:
        raise ValueError("Only TLS connections on port 443 are allowed")

    host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith((".localhost", ".local", ".internal", ".test")):
        raise ValueError("Local and internal destinations are blocked")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and not _is_public_unicast(literal):
        raise ValueError("Only publicly routable unicast IP addresses are allowed")
    return host, port


def validate_global_addresses(values: list[str]) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    if not values:
        raise ValueError("Destination has no resolved addresses")
    addresses = [ipaddress.ip_address(value.split("%", 1)[0]) for value in values]
    if any(not _is_public_unicast(address) for address in addresses):
        raise ValueError("Destination resolves to a non-public or non-unicast address")
    return addresses


async def resolve_public_addresses(host: str, port: int = 443):
    loop = asyncio.get_running_loop()
    records = await asyncio.wait_for(
        loop.getaddrinfo(host, port, type=socket.SOCK_STREAM),
        timeout=CONNECT_TIMEOUT_SECONDS,
    )
    values = list(dict.fromkeys(record[4][0] for record in records))
    addresses = validate_global_addresses(values)
    return [(address.version, str(address)) for address in addresses]


async def open_pinned_connection(host: str, port: int = 443):
    addresses = await resolve_public_addresses(host, port)
    last_error: OSError | None = None
    for version, address in addresses:
        try:
            family = socket.AF_INET6 if version == 6 else socket.AF_INET
            return await asyncio.wait_for(
                asyncio.open_connection(address, port, family=family),
                timeout=CONNECT_TIMEOUT_SECONDS,
            )
        except OSError as exc:
            last_error = exc
    raise OSError("Could not connect to any validated destination address") from last_error


async def _copy_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await asyncio.wait_for(reader.read(64 * 1024), timeout=IDLE_TIMEOUT_SECONDS)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (asyncio.TimeoutError, ConnectionError, OSError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except OSError:
            pass


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    upstream_writer: asyncio.StreamWriter | None = None
    try:
        header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        if len(header) > MAX_HEADER_BYTES:
            raise ValueError("Proxy header too large")
        request_line = header.split(b"\r\n", 1)[0].decode("ascii", errors="strict")
        host, port = parse_connect_target(request_line)
        upstream_reader, upstream_writer = await open_pinned_connection(host, port)
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        await asyncio.gather(
            _copy_stream(reader, upstream_writer),
            _copy_stream(upstream_reader, writer),
        )
    except (ValueError, UnicodeDecodeError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, asyncio.TimeoutError) as exc:
        message = str(exc).replace("\r", " ").replace("\n", " ")[:160]
        try:
            writer.write(f"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: {len(message)}\r\n\r\n{message}".encode())
            await writer.drain()
        except OSError:
            pass
    except (OSError, socket.gaierror):
        try:
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
        except OSError:
            pass
    finally:
        if upstream_writer is not None:
            upstream_writer.close()
            try:
                await upstream_writer.wait_closed()
            except OSError:
                pass
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


async def main() -> None:
    server = await asyncio.start_server(handle_client, "0.0.0.0", 3128, limit=MAX_HEADER_BYTES)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
