from __future__ import annotations

import ipaddress
import os
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit

from service_boundary.errors import PublicError, public_error

Resolver = Callable[[str, int], Iterable[str]]
DEFAULT_METADATA_RANGES = (
    ipaddress.ip_network("169.254.169.254/32"),
    ipaddress.ip_network("100.100.100.200/32"),
    ipaddress.ip_network("fd00:ec2::254/128"),
)


@dataclass(frozen=True)
class ValidatedURL:
    url: str
    host: str
    port: int
    addresses: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]


def system_resolver(host: str, port: int) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(item[4][0]) for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        )
    )


def _trusted_private_mode() -> bool:
    return os.getenv("ALLOW_PRIVATE_NETWORK_FETCH", "").lower() in {"1", "true", "yes"}


def _extra_metadata_ranges() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    ranges: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = list(DEFAULT_METADATA_RANGES)
    for value in os.getenv("BLOCKED_METADATA_CIDRS", "").split(","):
        if value.strip():
            try:
                ranges.append(ipaddress.ip_network(value.strip(), strict=False))
            except ValueError as exc:
                raise RuntimeError("BLOCKED_METADATA_CIDRS contains an invalid network") from exc
    return tuple(ranges)


def parse_http_url(value: str, *, maximum_length: int = 2_048) -> SplitResult:
    if not isinstance(value, str) or not value or len(value) > maximum_length:
        raise public_error("url_not_allowed", field="url")
    if any(ord(character) < 32 or character.isspace() for character in value):
        raise public_error("url_not_allowed", field="url")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise public_error("url_not_allowed", field="url") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise public_error("url_not_allowed", field="url")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise public_error("url_not_allowed", field="url")
    if port is not None and not 1 <= port <= 65_535:
        raise public_error("url_not_allowed", field="url")
    try:
        parsed.hostname.encode("idna")
    except UnicodeError as exc:
        raise public_error("url_not_allowed", field="url") from exc
    return parsed


def _is_prohibited(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    allow_private: bool,
) -> bool:
    if any(address in network for network in _extra_metadata_ranges()):
        return True
    if (
        address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    ):
        return True
    if allow_private:
        return False
    return address.is_private or not address.is_global


def validate_url(
    value: str,
    *,
    resolver: Resolver = system_resolver,
    allow_private: bool | None = None,
    maximum_length: int = 2_048,
) -> ValidatedURL:
    parsed = parse_http_url(value, maximum_length=maximum_length)
    host = parsed.hostname or ""
    ascii_host = host.encode("idna").decode("ascii").lower()
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    raw_addresses: tuple[str, ...]
    try:
        literal = ipaddress.ip_address(ascii_host.strip("[]"))
        raw_addresses = (str(literal),)
    except ValueError:
        try:
            raw_addresses = tuple(resolver(ascii_host, port))
        except (OSError, socket.gaierror) as exc:
            raise public_error("url_not_allowed", field="url") from exc
    if not raw_addresses:
        raise public_error("url_not_allowed", field="url")
    try:
        addresses = tuple(dict.fromkeys(ipaddress.ip_address(item) for item in raw_addresses))
    except ValueError as exc:
        raise public_error("url_not_allowed", field="url") from exc
    private_allowed = _trusted_private_mode() if allow_private is None else allow_private
    if any(_is_prohibited(address, allow_private=private_allowed) for address in addresses):
        raise public_error("url_not_allowed", field="url")
    netloc_host = f"[{ascii_host}]" if ":" in ascii_host else ascii_host
    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    netloc = netloc_host if default_port else f"{netloc_host}:{port}"
    normalized = urlunsplit(
        (parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, "")
    )
    return ValidatedURL(normalized, ascii_host, port, addresses)


def validate_redirect(
    current_url: str,
    location: str,
    *,
    resolver: Resolver = system_resolver,
    allow_private: bool | None = None,
) -> ValidatedURL:
    if not location:
        raise public_error("url_not_allowed", field="url")
    return validate_url(
        urljoin(current_url, location), resolver=resolver, allow_private=allow_private
    )


def safe_url_or_error(value: str, **kwargs: object) -> str:
    try:
        return validate_url(value, **kwargs).url  # type: ignore[arg-type]
    except PublicError:
        raise
