"""SSRF-safe URL fetching for resume ingestion (P2-104).

`urlopen(candidate_supplied_url)` lets an authenticated candidate make the
server fetch arbitrary internal addresses (cloud metadata, VPC-internal
services, localhost) and echoes the response back into the resume-parsing
pipeline. This module is a hardened, stdlib-only replacement.

Three things a naive "validate the hostname, then urlopen it" fix misses,
all handled here:
  1. DNS rebinding (TOCTOU) — the hostname must resolve to the SAME address
     that gets validated and connected to. Re-resolving at connect time
     (which `urlopen`/`http.client` do by default) reopens the gap.
  2. Redirects — `urlopen` follows them by default, so a URL that passes
     validation can still redirect to an internal address. Every hop is
     re-validated here; nothing delegates redirect-following to urllib.
  3. Multi-answer DNS — a hostname can resolve to several addresses in one
     answer. If any of them is internal, the whole hostname is rejected,
     not just the internal record.
"""

from __future__ import annotations

import http.client
import socket
import ssl
import time
from ipaddress import IPv4Address, IPv6Address, ip_address
from urllib.parse import urljoin, urlsplit

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MB — resumes are never this large
DEFAULT_USER_AGENT = "MockInterviewAI/1.0"

# Named explicitly even though is_link_local already covers it — the ticket
# calls this address out specifically, and a future reader auditing this
# module against that checklist should be able to find it at a glance.
_EXPLICITLY_BLOCKED_IPS = {"169.254.169.254"}

_READ_CHUNK_SIZE = 64 * 1024


class UnsafeURLError(Exception):
    """Raised for any validation failure: bad scheme, blocked/unresolvable
    host, too many redirects, or an oversized response. Callers should treat
    this the same as any other fetch failure."""


def _is_public_unicast(ip: IPv4Address | IPv6Address) -> bool:
    """True only for addresses safe to let the server connect to.

    Deliberately spelled out as named checks (not collapsed to an equivalent
    `is_global and not is_multicast`) so this stays auditable against the
    private/loopback/link-local/multicast/reserved/metadata-IP checklist at
    a glance, since this is a security control.
    """
    if isinstance(ip, IPv6Address) and ip.ipv4_mapped is not None:
        # ::ffff:a.b.c.d smuggling — classify the real underlying address.
        ip = ip.ipv4_mapped

    if str(ip) in _EXPLICITLY_BLOCKED_IPS:
        return False

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False

    # Catch-all for anything not explicitly public (e.g. CGNAT 100.64.0.0/10,
    # which reports is_private=False but is_global=False too).
    if not ip.is_global:
        return False

    return True


def resolve_validated_address(hostname: str, port: int) -> tuple[str, int]:
    """Resolve `hostname` exactly once and validate every candidate address.

    Returns (ip_literal, socket_family) for the first validated candidate,
    preferring IPv4. This is the single point of DNS resolution — nothing
    downstream re-resolves the hostname, which is what closes the DNS-
    rebinding TOCTOU window (an attacker's DNS returning a public IP for
    validation and a private IP moments later for the real connection).

    If `hostname` is already an IP literal, getaddrinfo parses it with no
    DNS query, so raw-IP URLs (e.g. http://169.254.169.254/...) go through
    the identical validation path.
    """
    try:
        results = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"could not resolve host: {hostname!r}") from exc

    if not results:
        raise UnsafeURLError(f"no addresses for host: {hostname!r}")

    candidates: list[tuple[str, int]] = []
    for family, _type, _proto, _canonname, sockaddr in results:
        raw_addr = sockaddr[0].split("%", 1)[0]  # strip IPv6 zone id, e.g. fe80::1%eth0
        try:
            ip = ip_address(raw_addr)
        except ValueError as exc:
            # Fail closed on anything we can't parse — this is a "best
            # effort resume text extraction" feature that already fails
            # soft to "" on error, so the conservative choice costs nothing.
            raise UnsafeURLError(f"unparseable address: {raw_addr!r}") from exc

        if not _is_public_unicast(ip):
            # Reject the whole hostname the moment ANY candidate is unsafe —
            # not just skip that record — in case the caller's connection
            # logic (or a retry elsewhere) ends up picking it regardless.
            raise UnsafeURLError(f"{hostname!r} resolves to a non-public address: {ip}")

        candidates.append((str(ip), family))

    for ip_str, family in candidates:
        if family == socket.AF_INET:
            return ip_str, family
    return candidates[0]


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection that dials a pre-validated IP directly instead of
    letting the base class re-resolve `host` at connect time."""

    def __init__(self, hostname: str, ip: str, port: int, timeout: float):
        super().__init__(hostname, port=port, timeout=timeout)
        self._pinned_ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Same pinning for HTTPS, with the TLS handshake (SNI + certificate
    verification) still performed against the real hostname — otherwise
    legitimate CDN-hosted resumes (Drive, Dropbox, Cloudflare-fronted sites)
    would fail cert validation against a bare IP."""

    def __init__(self, hostname: str, ip: str, port: int, timeout: float, ssl_context: ssl.SSLContext):
        super().__init__(hostname, port=port, timeout=timeout, context=ssl_context)
        self._pinned_ip = ip

    def connect(self) -> None:
        raw_sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(raw_sock, server_hostname=self.host)


def _read_capped(response: http.client.HTTPResponse, max_bytes: int) -> bytes:
    """Read the body in bounded chunks, aborting the moment it exceeds
    max_bytes — bounds memory even if Content-Length lies or is absent
    (chunked transfer encoding)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(_READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise UnsafeURLError(f"response exceeded {max_bytes} byte cap")
        chunks.append(chunk)
    return b"".join(chunks)


def _request_once(
    parsed,
    ip: str,
    port: int,
    remaining_timeout: float,
    max_bytes: int,
    user_agent: str,
) -> tuple[int, http.client.HTTPMessage, bytes]:
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    headers = {
        "Host": parsed.hostname,
        "User-Agent": user_agent,
        # Explicit identity encoding: a malicious server can't use gzip to
        # smuggle a large decompressed payload past the byte cap, since the
        # cap is measured on the wire.
        "Accept-Encoding": "identity",
        "Connection": "close",
    }

    if parsed.scheme == "https":
        ctx = ssl.create_default_context()  # verify_mode=CERT_REQUIRED, check_hostname=True — never disabled
        conn = _PinnedHTTPSConnection(parsed.hostname, ip, port, remaining_timeout, ctx)
    else:
        conn = _PinnedHTTPConnection(parsed.hostname, ip, port, remaining_timeout)

    try:
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        body = _read_capped(resp, max_bytes)
        return resp.status, resp.msg, body
    finally:
        conn.close()


def fetch_url_safely(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    max_bytes: int = DEFAULT_MAX_BODY_BYTES,
    user_agent: str = DEFAULT_USER_AGENT,
) -> tuple[bytes, str]:
    """Fetch `url`, following redirects manually with full re-validation on
    every hop. Returns (body_bytes, content_type). Raises UnsafeURLError on
    any validation failure, timeout, or oversized response.
    """
    deadline = time.monotonic() + timeout
    current_url = url

    for _ in range(max_redirects + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise UnsafeURLError("timed out")

        parsed = urlsplit(current_url)
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise UnsafeURLError(f"blocked scheme: {parsed.scheme!r}")
        if not parsed.hostname:
            raise UnsafeURLError("URL has no hostname")

        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        # Re-resolved and re-validated on EVERY hop — a redirect to
        # 169.254.169.254 or file:// is rejected at the hop it appears on,
        # not just checked against the original URL.
        ip, _family = resolve_validated_address(parsed.hostname, port)

        status, headers, body = _request_once(parsed, ip, port, remaining, max_bytes, user_agent)

        if status in (301, 302, 303, 307, 308):
            location = headers.get("Location")
            if not location:
                raise UnsafeURLError("redirect response missing Location header")
            current_url = urljoin(current_url, location)
            continue

        return body, (headers.get("Content-Type") or "")

    raise UnsafeURLError("too many redirects")
