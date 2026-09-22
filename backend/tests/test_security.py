import socket

import pytest
from fastapi import HTTPException

from app.models import Platform
from app.security import detect_platform, validate_media_url


def test_detects_supported_platforms():
    assert detect_platform("www.youtube.com") == Platform.youtube
    assert detect_platform("vm.tiktok.com") == Platform.tiktok
    assert detect_platform("evil-youtube.com") is None


@pytest.mark.asyncio
async def test_rejects_unsupported_host():
    with pytest.raises(HTTPException) as error:
        await validate_media_url("https://example.com/video")
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_rejects_private_resolution(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )
    with pytest.raises(HTTPException, match="restricted"):
        await validate_media_url("https://youtube.com/watch?v=test")

