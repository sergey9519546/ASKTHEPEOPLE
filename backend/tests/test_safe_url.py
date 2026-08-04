"""SSRF defense tests for `app.utils.safe_url` and the source-ingestion route.

The endpoint under protection is POST /api/sources/fetch: it accepts caller
supplied URLs and the server retrieves them, so an unguarded fetcher is a read
primitive against the deployment's own network.
"""

import socket
import urllib.error

import pytest

from app import create_app
from app.utils.safe_url import (
    MAX_REDIRECTS,
    SafeUrlError,
    ValidatingRedirectHandler,
    assert_public_http_url,
    build_safe_opener,
)


@pytest.fixture
def api_client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def public_dns(monkeypatch):
    """Resolve every *name* to a public address; leave IP literals alone.

    Keeps the route tests hermetic: without this they depend on live DNS, and
    an offline run would reach the right assertion for the wrong reason.
    """
    real = socket.getaddrinfo

    def _fake(host, *args, **kwargs):
        try:
            import ipaddress

            ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
        return real(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", _fake)


# --------------------------------------------------------------------------- #
# Address classes that must be refused
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.0.0.1:6379/",          # Redis broker
        "https://localhost/admin",
        "http://[::1]/",
        "http://0.0.0.0/",
        "http://169.254.169.254/latest/meta-data/",   # AWS/Azure IMDS
        "http://169.254.169.254/computeMetadata/v1/",  # GCP IMDS
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://[fd00::1]/",               # IPv6 unique-local
        "http://[fe80::1]/",               # IPv6 link-local
    ],
)
def test_rejects_non_public_addresses(url):
    with pytest.raises(SafeUrlError):
        assert_public_http_url(url)


def test_rejects_ipv4_mapped_ipv6_loopback():
    """::ffff:127.0.0.1 is a v6 literal wrapping a v4 loopback.

    Judged as a plain v6 address it looks globally routable, so the guard must
    unwrap ipv4_mapped before classifying.
    """
    with pytest.raises(SafeUrlError):
        assert_public_http_url("http://[::ffff:127.0.0.1]/")


def test_rejects_hostname_resolving_to_private_address(monkeypatch):
    """A public *name* pointing at a private *address* must still be refused."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 0))],
    )
    with pytest.raises(SafeUrlError):
        assert_public_http_url("https://intranet.example.com/")


def test_rejects_when_any_resolved_address_is_private(monkeypatch):
    """Every resolved address must be public, not merely the first one.

    A multi-A-record host that mixes one public and one private address would
    otherwise be reachable on retry.
    """
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ],
    )
    with pytest.raises(SafeUrlError):
        assert_public_http_url("https://mixed.example.com/")


# --------------------------------------------------------------------------- #
# Scheme, credential and shape validation
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://example.com/",
        "ftp://example.com/",
        "redis://127.0.0.1:6379/",
        "//example.com/",       # scheme-relative: no scheme at all
    ],
)
def test_rejects_non_http_schemes(url):
    with pytest.raises(SafeUrlError):
        assert_public_http_url(url)


def test_rejects_embedded_credentials(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    with pytest.raises(SafeUrlError):
        assert_public_http_url("https://user:pw@example.com/")


@pytest.mark.parametrize("url", ["", None, "   ", "http://", "https:///path"])
def test_rejects_empty_or_hostless(url):
    with pytest.raises(SafeUrlError):
        assert_public_http_url(url)


def test_rejects_unresolvable_host(monkeypatch):
    def _boom(*a, **k):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(socket, "getaddrinfo", _boom)
    with pytest.raises(SafeUrlError):
        assert_public_http_url("https://nonexistent.invalid/")


def test_rejection_reason_does_not_disclose_resolved_address(monkeypatch):
    """The error reaches the client, so it must name the address *class* only.

    Echoing the resolved address would turn the endpoint into an internal
    network scanner even while blocking the fetch.
    """
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.11.12.13", 0))],
    )
    with pytest.raises(SafeUrlError) as excinfo:
        assert_public_http_url("https://intranet.example.com/")
    assert "10.11.12.13" not in str(excinfo.value)


# --------------------------------------------------------------------------- #
# Public addresses must still be allowed
# --------------------------------------------------------------------------- #

def test_allows_public_address(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    assert assert_public_http_url("https://example.com/article") == (
        "https://example.com/article"
    )


def test_allows_public_address_on_nonstandard_port(monkeypatch):
    """Port is not a security boundary here — address class is."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    assert assert_public_http_url("https://example.com:8443/x")


# --------------------------------------------------------------------------- #
# Redirect revalidation
# --------------------------------------------------------------------------- #

def test_redirect_to_internal_address_is_blocked():
    """The entry check alone is bypassable: urlopen follows redirects."""
    handler = ValidatingRedirectHandler()
    with pytest.raises(urllib.error.HTTPError):
        handler.redirect_request(
            req=None,
            fp=None,
            code=302,
            msg="Found",
            headers={},
            newurl="http://169.254.169.254/latest/meta-data/",
        )


def test_redirect_chain_is_bounded():
    assert ValidatingRedirectHandler.max_redirections == MAX_REDIRECTS
    assert MAX_REDIRECTS > 0


def test_safe_opener_installs_the_validating_handler():
    opener = build_safe_opener()
    assert any(
        isinstance(h, ValidatingRedirectHandler) for h in opener.handlers
    ), "opener must carry the redirect guard, or redirects go unchecked"


# --------------------------------------------------------------------------- #
# Route-level enforcement
# --------------------------------------------------------------------------- #

def test_fetch_route_rejects_internal_url(api_client):
    resp = api_client.post(
        "/api/sources/fetch",
        json={"urls": ["http://169.254.169.254/latest/meta-data/"]},
    )
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_fetch_route_rejects_when_one_url_of_many_is_internal(api_client, public_dns):
    """One bad URL fails the whole request rather than being fetched alongside."""
    resp = api_client.post(
        "/api/sources/fetch",
        json={"urls": ["https://example.com/ok", "http://127.0.0.1:6379/"]},
    )
    assert resp.status_code == 400


def test_fetch_url_content_refuses_internal_url_without_network(monkeypatch):
    """The service-level guard fires before any tier attempts a request."""
    from app.services import url_fetcher

    def _fail(*a, **k):
        raise AssertionError("no tier may run for a blocked URL")

    monkeypatch.setattr(url_fetcher, "fetch_with_firecrawl", _fail)
    monkeypatch.setattr(url_fetcher, "fetch_with_jina_reader", _fail)
    monkeypatch.setattr(url_fetcher, "fetch_with_custom_extractor", _fail)

    result = url_fetcher.fetch_url_content("http://169.254.169.254/")
    assert result["success"] is False


# --------------------------------------------------------------------------- #
# Response size bound
# --------------------------------------------------------------------------- #

def test_oversized_body_is_bounded_without_reading_to_eof(monkeypatch, public_dns):
    """An origin that omits Content-Length must not stream unbounded into memory.

    The old code called response.read() with no argument, so the size check ran
    only after the whole body was already resident.
    """
    from app.services import url_fetcher

    reads = []

    class _FakeResponse:
        # note: no Content-Length, which is the case the cap has to survive
        def __init__(self):
            self.headers = {"Content-Type": "text/html"}

        def read(self, amt=None):
            reads.append(amt)
            # Honour the cap the caller asked for; a real socket would too.
            return b"x" * (amt if amt is not None else 10**9)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _FakeOpener:
        def open(self, req, timeout=None):
            return _FakeResponse()

    monkeypatch.setattr(url_fetcher, "build_safe_opener", lambda: _FakeOpener())

    result = url_fetcher.fetch_with_custom_extractor("https://example.com/big")

    assert result["success"] is False
    assert "too large" in result["error"].lower()
    assert reads == [url_fetcher.MAX_CONTENT_SIZE + 1], (
        f"read must be capped at the limit + 1 byte, got {reads!r}"
    )
