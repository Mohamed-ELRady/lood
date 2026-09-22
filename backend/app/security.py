import asyncio
import hashlib
import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import Header, HTTPException, status

from .models import Platform

PLATFORM_HOSTS: dict[Platform, tuple[str, ...]] = {
    Platform.youtube: ("youtube.com", "youtu.be", "youtube-nocookie.com"),
    Platform.facebook: ("facebook.com", "fb.watch"),
    Platform.instagram: ("instagram.com",),
    Platform.tiktok: ("tiktok.com",),
    Platform.x: ("x.com", "twitter.com"),
    Platform.vimeo: ("vimeo.com",),
    Platform.soundcloud: ("soundcloud.com", "on.soundcloud.com"),
}


def detect_platform(hostname: str) -> Platform | None:
    host = hostname.rstrip(".").lower()
    for platform, suffixes in PLATFORM_HOSTS.items():
        if any(host == suffix or host.endswith(f".{suffix}") for suffix in suffixes):
            return platform
    return None


def _is_public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


async def validate_media_url(value: str) -> tuple[str, Platform]:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Use a valid HTTP or HTTPS media link")
    if parsed.username or parsed.password or parsed.port not in {None, 80, 443}:
        raise HTTPException(status_code=422, detail="Credentials and custom ports are not allowed")

    platform = detect_platform(parsed.hostname)
    if not platform:
        raise HTTPException(status_code=422, detail="This source is not currently supported")

    loop = asyncio.get_running_loop()
    try:
        records = await loop.run_in_executor(
            None, lambda: socket.getaddrinfo(parsed.hostname, None, proto=socket.IPPROTO_TCP)
        )
    except socket.gaierror as exc:
        raise HTTPException(status_code=422, detail="The link host could not be resolved") from exc
    if not records or any(not _is_public_ip(record[4][0]) for record in records):
        raise HTTPException(status_code=422, detail="The link resolves to a restricted network")
    return value, platform


def owner_hash(client_id: str) -> str:
    return hashlib.sha256(client_id.encode("utf-8")).hexdigest()


def require_client_id(x_client_id: str = Header(min_length=16, max_length=128)) -> str:
    if not x_client_id.replace("-", "").isalnum():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client identifier")
    return x_client_id

