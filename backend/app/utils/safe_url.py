"""SSRF defense for operator- and user-supplied URLs the server itself fetches.

The threat: ``POST /api/sources/fetch`` accepts arbitrary URLs and the backend
retrieves them. Without a guard, a caller can aim the server at cloud metadata
(``169.254.169.254``, ``metadata.google.internal``), at Redis on ``127.0.0.1``,
or at any service reachable only from inside the deployment network, and read
the response back through the source-material record.

Two layers are required and neither is sufficient alone:

1. :func:`assert_public_http_url` — resolves the hostname and rejects the
   request unless *every* address it resolves to is publicly routable.
2. :class:`ValidatingRedirectHandler` — re-runs that check on each redirect
   target. A host-level allowlist applied only at the entry point is bypassed
   by a public URL that 302s to ``http://169.254.169.254/``.

Residual risk (documented, not closed here): DNS rebinding. The name is
resolved once for validation and again by the socket layer at connect time, so
a resolver the attacker controls with a sub-second TTL could return a public
address to the first lookup and a private one to the second. Closing it means
pinning the validated address at connect time, which urllib cannot express
without replacing the connection layer. The window is small, requires
attacker-controlled authoritative DNS, and every fetch is already behind
``APP_TOKEN`` in production.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.request
from urllib.parse import urlsplit

__all__ = [
    "ALLOWED_SCHEMES",
    "MAX_REDIRECTS",
    "SafeUrlError",
    "ValidatingRedirectHandler",
    "assert_public_http_url",
    "build_safe_opener",
]


class SafeUrlError(ValueError):
    """Raised when a URL is not safe for the server to fetch."""


ALLOWED_SCHEMES = ("http", "https")

# urllib's own default is 10. Kept explicit so the redirect chain is bounded by
# this module rather than by a library default that could change.
MAX_REDIRECTS = 5


def _addresses_for(host: str) -> list[ipaddress._BaseAddress]:
    """Resolve ``host`` to every address it maps to, v4 and v6.

    A bare address literal resolves to itself, which is what makes the
    ``http://127.0.0.1/`` and ``http://[::1]/`` cases fall out of the same code
    path as the DNS case instead of needing a separate branch.
    """
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise SafeUrlError(f"Host does not resolve: {host}") from exc

    addresses = []
    for info in infos:
        sockaddr = info[4]
        try:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    if not addresses:
        raise SafeUrlError(f"Host does not resolve to a usable address: {host}")
    return addresses


def _reject_reason(address: ipaddress._BaseAddress) -> str | None:
    """Return why ``address`` must not be fetched, or None when it is fine.

    ``is_global`` is the primary test; it already excludes private, loopback,
    link-local, reserved and unspecified ranges. The explicit checks that follow
    are not redundant — they turn a single opaque "not global" into a reason the
    operator can act on, and they keep the intent legible when reviewing.
    """
    # IPv6 addresses that merely wrap a v4 address must be judged on the v4
    # address, or ::ffff:127.0.0.1 slips through as a "global" v6 address.
    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        address = mapped

    if address.is_loopback:
        return "loopback address"
    if address.is_link_local:
        # Covers 169.254.0.0/16, i.e. AWS/Azure/GCP instance metadata.
        return "link-local address (cloud instance metadata range)"
    if address.is_private:
        return "private address"
    if address.is_reserved:
        return "reserved address"
    if address.is_multicast:
        return "multicast address"
    if address.is_unspecified:
        return "unspecified address"
    if not address.is_global:
        return "non-globally-routable address"
    return None


def assert_public_http_url(url: str) -> str:
    """Validate that ``url`` is an http(s) URL on a publicly routable host.

    Returns the URL unchanged so it can be used inline. Raises
    :class:`SafeUrlError` with a caller-safe reason otherwise. The reason names
    the class of address, never the resolved address itself, so a rejection
    cannot be used to map the deployment's internal network.
    """
    if not url or not isinstance(url, str):
        raise SafeUrlError("URL must be a non-empty string")

    parts = urlsplit(url.strip())

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise SafeUrlError("Only HTTP/HTTPS URLs supported")

    # Credentials in the URL are never needed for source ingestion and are a
    # standard way to smuggle a different authority past naive parsers.
    if parts.username or parts.password:
        raise SafeUrlError("Credentials in URL are not allowed")

    host = parts.hostname
    if not host:
        raise SafeUrlError("URL has no host")

    for address in _addresses_for(host):
        reason = _reject_reason(address)
        if reason is not None:
            raise SafeUrlError(f"Refusing to fetch a {reason}")

    return url


class ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect target before urllib follows it.

    ``urlopen`` follows redirects by default, so validating only the URL the
    caller supplied leaves the guard trivially bypassable: a public URL that
    replies ``302 Location: http://169.254.169.254/`` reaches the metadata
    service with the entry check already satisfied.
    """

    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            assert_public_http_url(newurl)
        except SafeUrlError as exc:
            raise urllib.error.HTTPError(
                newurl, code, f"Blocked redirect: {exc}", headers, fp
            ) from exc
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_safe_opener() -> urllib.request.OpenerDirector:
    """An opener that validates the initial URL's redirects.

    Built per call rather than cached at import time: it holds no state worth
    reusing, and a module-level opener would be shared across Celery worker
    forks.
    """
    return urllib.request.build_opener(ValidatingRedirectHandler())
