import io

from PIL import Image

from app.core.storage import InMemoryStorageClient
from app.modules.enrichment.images import (
    CANVAS_SIZE,
    THUMBNAIL_SIZE,
    standardize_image,
    validate_image_candidate,
)


def _create_test_image(width: int, height: int, pattern: str = "checker") -> bytes:
    img = Image.new("RGB", (width, height), (255, 255, 255))
    if pattern == "checker":
        # Draw some non-solid content
        for x in range(0, width, 40):
            for y in range(0, height, 40):
                if (x // 40 + y // 40) % 2 == 0:
                    for i in range(min(20, width - x)):
                        for j in range(min(20, height - y)):
                            img.putpixel((x + i, y + j), (120, 80, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_validate_image_candidate_success() -> None:
    data = _create_test_image(600, 800)
    is_valid, reason = validate_image_candidate(data)
    assert is_valid is True
    assert reason is None


def test_validate_image_candidate_too_small() -> None:
    data = _create_test_image(300, 300)
    is_valid, reason = validate_image_candidate(data)
    assert is_valid is False
    assert reason is not None
    assert "short_side_too_small" in reason


def test_validate_image_candidate_invalid_aspect_ratio() -> None:
    data = _create_test_image(1200, 500)  # aspect ratio 2.4 > 2.0, short side 500 >= 500
    is_valid, reason = validate_image_candidate(data)
    assert is_valid is False
    assert reason is not None
    assert "invalid_aspect_ratio" in reason


def test_validate_image_candidate_solid_color() -> None:
    data = _create_test_image(600, 600, pattern="solid")
    is_valid, reason = validate_image_candidate(data)
    assert is_valid is False
    assert reason == "solid_color_image"


def test_standardize_image_dimensions_and_formats() -> None:
    data = _create_test_image(600, 800)
    res = standardize_image(data)

    # Full image check
    with Image.open(io.BytesIO(res.full)) as full_img:
        assert full_img.format == "WEBP"
        assert full_img.size == (CANVAS_SIZE, CANVAS_SIZE)

    # Thumbnail check
    with Image.open(io.BytesIO(res.thumbnail)) as thumb_img:
        assert thumb_img.format == "WEBP"
        assert thumb_img.size == (THUMBNAIL_SIZE, THUMBNAIL_SIZE)


async def test_in_memory_storage_client() -> None:
    storage = InMemoryStorageClient(base_url="https://cdn.dermascan.local/assets")
    assert await storage.exists("test/sample.webp") is False

    data = b"fake-webp-bytes"
    url = await storage.put_image("test/sample.webp", data)
    assert url == "https://cdn.dermascan.local/assets/test/sample.webp"
    assert await storage.exists("test/sample.webp") is True

    fetched = await storage.get_image("test/sample.webp")
    assert fetched == data
