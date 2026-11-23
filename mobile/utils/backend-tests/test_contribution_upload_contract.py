"""Bounded upload and true-format regression tests; no storage or database calls."""
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image
import pytest
from starlette.datastructures import Headers

from app.api.v1.contributions import MAX_PHOTO_SIZE, _validated_photo


def upload(content: bytes, mime: str) -> UploadFile:
    return UploadFile(BytesIO(content), headers=Headers({"content-type": mime}))


@pytest.mark.asyncio
@pytest.mark.parametrize("fmt,mime,extension", [("JPEG", "image/jpeg", "jpg"), ("PNG", "image/png", "png"), ("WEBP", "image/webp", "webp")])
async def test_preserves_actual_image_type(fmt: str, mime: str, extension: str) -> None:
    buffer = BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format=fmt)
    original = buffer.getvalue()
    content, actual_extension, actual_mime = await _validated_photo(upload(original, mime))
    assert content == original
    assert actual_extension == extension
    assert actual_mime == mime


@pytest.mark.asyncio
async def test_rejects_non_image_bytes() -> None:
    with pytest.raises(HTTPException) as caught:
        await _validated_photo(upload(b"not an image", "image/jpeg"))
    assert caught.value.status_code == 415


@pytest.mark.asyncio
async def test_limits_read_size() -> None:
    class OversizedUpload(UploadFile):
        async def read(self, size: int = -1) -> bytes:
            assert size == MAX_PHOTO_SIZE + 1
            return b"x" * size
    oversized = OversizedUpload(BytesIO(), headers=Headers({"content-type": "image/jpeg"}))
    with pytest.raises(HTTPException) as caught:
        await _validated_photo(oversized)
    assert caught.value.status_code == 413


@pytest.mark.asyncio
async def test_uses_detected_format_not_claimed_mime() -> None:
    buffer = BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="PNG")
    _, extension, mime = await _validated_photo(upload(buffer.getvalue(), "image/jpeg"))
    assert extension == "png"
    assert mime == "image/png"
