"""Fetching a remote image safely.

The AI product-creation flow downloads the product photo the model found on
the web, which means this server issues outbound requests to addresses it did
not choose. That is a server-side request forgery (SSRF) primitive unless
every hop is checked, so this module:

  - allows only http/https, closing off file://, gopher://, redis:// and
    friends;
  - resolves each hop's hostname and refuses private, loopback, link-local,
    reserved and multicast addresses — this is what stops a URL from reaching
    the Postgres container on the compose network, the cloud metadata
    endpoint at 169.254.169.254, or localhost;
  - follows redirects one hop at a time, re-validating each, rather than
    letting httpx chase a 302 into the private network after the first host
    passed;
  - caps the download while streaming, so a hostile URL can neither exhaust
    memory nor fill the uploads volume;
  - identifies the format from magic bytes rather than trusting the
    Content-Type a remote server claims.

Residual risk: a DNS record that changes between the check and the connection
(rebinding) is not defeated here — pinning the socket to the validated IP
would be needed for that.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

MAX_IMAGE_BYTES = 5 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 15.0
MAX_REDIRECTS = 3

# (magic prefix, offset, extension). WEBP needs a second check because its
# RIFF container only identifies itself at byte 8.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def detect_extension(data: bytes) -> str | None:
    """The real format, from the bytes themselves."""
    if data.startswith(_PNG_MAGIC):
        return ".png"
    if data.startswith(_JPEG_MAGIC):
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def _reject(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _assert_public_host(hostname: str) -> None:
    """Every address the hostname resolves to must be publicly routable.

    Checking *all* results matters: a host with both a public A record and a
    private one would otherwise pass on the strength of the public one and
    then be connected to on whichever the resolver returns first.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise _reject("Could not resolve the image host")

    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            raise _reject("Image host resolved to an unusable address")
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise _reject("Image host resolves to a non-public address")


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise _reject("Image URL must be http or https")
    if not parsed.hostname:
        raise _reject("Image URL has no host")
    _assert_public_host(parsed.hostname)
    return url


def fetch_image(url: str) -> tuple[bytes, str]:
    """Downloads `url` and returns (bytes, extension).

    Raises HTTPException (400) for anything rejected, so a bad or hostile URL
    surfaces to the admin as a normal failed draft rather than a 500.
    """
    current = _validate_url(url)

    with httpx.Client(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            try:
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise _reject("Image URL redirected without a destination")
                        # Re-validate the new host before following it: the
                        # first host passing the check says nothing about
                        # where it points us next.
                        current = _validate_url(str(response.next_request.url if response.next_request else location))
                        continue

                    if response.status_code != 200:
                        raise _reject(f"Image URL returned HTTP {response.status_code}")

                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_IMAGE_BYTES:
                            raise _reject("Image is too large (max 5MB)")
                        chunks.append(chunk)
                    data = b"".join(chunks)
            except httpx.HTTPError as exc:
                raise _reject(f"Could not download the image: {type(exc).__name__}")

            extension = detect_extension(data)
            if extension is None:
                raise _reject("Downloaded file is not a PNG, JPEG or WEBP image")
            return data, extension

    raise _reject("Image URL redirected too many times")
