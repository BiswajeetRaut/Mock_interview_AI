"""P2-104 — resume URL fetching must reject internal/private destinations,
including DNS-rebinding, redirect, and IPv4-mapped-IPv6 smuggling variants."""

import socket
from unittest.mock import patch

import pytest

from services.ssrf_guard import (
    UnsafeURLError,
    _is_public_unicast,
    fetch_url_safely,
    resolve_validated_address,
)
from ipaddress import ip_address


BLOCKED_IPS = [
    "10.0.0.1", "172.16.0.5", "192.168.1.1",       # private
    "127.0.0.1",                                     # loopback
    "169.254.169.254",                               # cloud metadata / link-local
    "100.64.0.1",                                    # CGNAT — not is_private, still must block
    "0.0.0.0",                                        # unspecified
    "224.0.0.1",                                      # multicast — is_global=True, must exclude explicitly
    "255.255.255.255",                                # reserved
    "::1", "fe80::1", "fc00::1", "2001:db8::1",
    "::ffff:127.0.0.1", "::ffff:10.0.0.1",           # IPv4-mapped smuggling
]

PUBLIC_IPS = ["8.8.8.8", "1.1.1.1", "2606:4700:4700::1111", "::ffff:8.8.8.8"]


@pytest.mark.parametrize("ip_str", BLOCKED_IPS)
def test_blocked_addresses(ip_str):
    assert _is_public_unicast(ip_address(ip_str)) is False


@pytest.mark.parametrize("ip_str", PUBLIC_IPS)
def test_public_addresses(ip_str):
    assert _is_public_unicast(ip_address(ip_str)) is True


def _fake_getaddrinfo(*addrs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, 80)) for a in addrs]


@patch("services.ssrf_guard.socket.getaddrinfo")
def test_resolve_all_public_returns_ip(mock_gai):
    mock_gai.return_value = _fake_getaddrinfo("8.8.8.8")
    ip, family = resolve_validated_address("example.com", 80)
    assert ip == "8.8.8.8"


@patch("services.ssrf_guard.socket.getaddrinfo")
def test_resolve_rejects_if_any_record_is_private(mock_gai):
    # DNS returning a public AND a private record in one answer — must
    # reject the whole hostname, not just skip the bad record.
    mock_gai.return_value = _fake_getaddrinfo("8.8.8.8", "10.0.0.1")
    with pytest.raises(UnsafeURLError):
        resolve_validated_address("example.com", 80)


@patch("services.ssrf_guard.socket.getaddrinfo")
def test_resolve_dns_failure_is_unsafe(mock_gai):
    mock_gai.side_effect = socket.gaierror("name not known")
    with pytest.raises(UnsafeURLError):
        resolve_validated_address("nonexistent.invalid", 80)


@patch("services.ssrf_guard.socket.getaddrinfo")
def test_metadata_ip_literal_in_url_is_blocked(mock_gai):
    # A raw IP in the URL still goes through getaddrinfo (no DNS query
    # needed) and must be rejected identically to a resolved hostname.
    mock_gai.return_value = _fake_getaddrinfo("169.254.169.254")
    with pytest.raises(UnsafeURLError):
        fetch_url_safely("http://169.254.169.254/latest/meta-data/")
    mock_gai.assert_called_once()


def test_non_http_scheme_rejected_before_any_network_call():
    with patch("services.ssrf_guard.socket.getaddrinfo") as mock_gai:
        with pytest.raises(UnsafeURLError):
            fetch_url_safely("file:///etc/passwd")
        mock_gai.assert_not_called()


class Headers(dict):
    """Minimal stand-in for http.client.HTTPMessage's .get(key) interface."""
    def get(self, k, default=None):
        return super().get(k, default)


@patch("services.ssrf_guard._request_once")
@patch("services.ssrf_guard.socket.getaddrinfo")
def test_redirect_to_internal_address_is_blocked_on_that_hop(mock_gai, mock_request):
    # Hop 1: public site redirects. Hop 2: redirect target resolves internal.
    mock_gai.side_effect = [
        _fake_getaddrinfo("8.8.8.8"),          # hop 1 resolution
        _fake_getaddrinfo("169.254.169.254"),   # hop 2 resolution — must be rejected
    ]
    mock_request.return_value = (302, Headers({"Location": "http://internal.example/secret"}), b"")

    with pytest.raises(UnsafeURLError):
        fetch_url_safely("http://public.example/resume.pdf")

    # Only the first hop's request should ever have been issued.
    assert mock_request.call_count == 1


@patch("services.ssrf_guard._request_once")
@patch("services.ssrf_guard.socket.getaddrinfo")
def test_too_many_redirects_raises(mock_gai, mock_request):
    mock_gai.return_value = _fake_getaddrinfo("8.8.8.8")
    mock_request.return_value = (302, Headers({"Location": "http://public.example/next"}), b"")

    with pytest.raises(UnsafeURLError):
        fetch_url_safely("http://public.example/start", max_redirects=2)

    assert mock_request.call_count == 3  # initial + 2 redirects, then give up


@patch("services.ssrf_guard.socket.getaddrinfo")
def test_end_to_end_resume_extraction_blocks_metadata_url(mock_gai):
    """The vuln's own attack payload, through the actual function callers use."""
    from services.session_engine import _extract_resume_text

    mock_gai.return_value = _fake_getaddrinfo("169.254.169.254")
    result = _extract_resume_text({"format": "url", "data": "http://169.254.169.254/latest/meta-data/"})
    assert result == ""
