"""Image processing and standardization for product catalog images.

Follows Section 8.8:
- Candidate validation (short side >= 500 px, aspect ratio 0.5 .. 2.0).
- Background removal with Pillow fallback (crop, center on square white canvas).
- WebP export: 1024x1024 high-res and 320x320 thumbnail.
"""

import io
from dataclasses import dataclass
from typing import Protocol

import structlog
from PIL import Image, ImageOps

logger = structlog.get_logger(__name__)

CANVAS_SIZE = 1024
THUMBNAIL_SIZE = 320
MIN_SHORT_SIDE = 500
MIN_ASPECT_RATIO = 0.5
MAX_ASPECT_RATIO = 2.0


@dataclass(frozen=True, slots=True)
class StandardizedImages:
    full: bytes
    thumbnail: bytes


class BackgroundRemover(Protocol):
    def remove_background(self, img: Image.Image) -> Image.Image: ...


class PillowFallbackBackgroundRemover:
    """Removes borders and centers subject on a clean transparent/white canvas.

    Attempts rembg if available; otherwise performs deterministic border trimming.
    """

    def remove_background(self, img: Image.Image) -> Image.Image:
        try:
            import rembg  # type: ignore[import-not-found]

            res = rembg.remove(img)
            return res if isinstance(res, Image.Image) else self._pillow_trim(img)
        except (ImportError, Exception) as exc:
            logger.debug("rembg_unavailable_using_pillow_fallback", error=str(exc))
            return self._pillow_trim(img)

    def _pillow_trim(self, img: Image.Image) -> Image.Image:
        rgba = img.convert("RGBA")
        diff = ImageOps.invert(rgba.convert("RGB"))
        bbox = diff.getbbox()
        if bbox:
            return rgba.crop(bbox)
        return rgba


def validate_image_candidate(image_bytes: bytes) -> tuple[bool, str | None]:
    """Validate image format and dimensions (Section 8.8.2)."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
            short_side = min(w, h)
            if short_side < MIN_SHORT_SIDE:
                return False, f"short_side_too_small: {short_side} < {MIN_SHORT_SIDE}"

            ratio = w / h
            if ratio < MIN_ASPECT_RATIO or ratio > MAX_ASPECT_RATIO:
                msg = (
                    f"invalid_aspect_ratio: {ratio:.2f} "
                    f"not in [{MIN_ASPECT_RATIO}, {MAX_ASPECT_RATIO}]"
                )
                return False, msg

            # Check if nearly empty or solid image (extrema check)
            extrema = img.convert("L").getextrema()  # type: ignore[no-untyped-call]
            if extrema and extrema[0] == extrema[1]:
                return False, "solid_color_image"

            return True, None
    except Exception as exc:
        return False, f"invalid_image_data: {exc}"


def standardize_image(
    image_bytes: bytes,
    remover: BackgroundRemover | None = None,
) -> StandardizedImages:
    """Standardize candidate image to 1024x1024 and 320x320 WebP on white canvas."""
    bg_remover = remover or PillowFallbackBackgroundRemover()

    with Image.open(io.BytesIO(image_bytes)) as raw_img:
        processed = bg_remover.remove_background(raw_img)

        # Create 1024x1024 white canvas
        canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (255, 255, 255, 255))

        # Fit product inside canvas with 10% padding (max target 820 px)
        max_target = int(CANVAS_SIZE * 0.82)
        fitted = ImageOps.contain(processed, (max_target, max_target), Image.Resampling.LANCZOS)

        # Center product on canvas
        offset_x = (CANVAS_SIZE - fitted.width) // 2
        offset_y = (CANVAS_SIZE - fitted.height) // 2
        mask = fitted.split()[-1] if fitted.mode == "RGBA" else None
        canvas.paste(fitted, (offset_x, offset_y), mask=mask)

        final_rgb = canvas.convert("RGB")

        # Full 1024x1024 WebP
        full_buffer = io.BytesIO()
        final_rgb.save(full_buffer, format="WEBP", quality=85, method=4)
        full_bytes = full_buffer.getvalue()

        # Thumbnail 320x320 WebP
        thumb_img = final_rgb.resize((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
        thumb_buffer = io.BytesIO()
        thumb_img.save(thumb_buffer, format="WEBP", quality=80, method=4)
        thumb_bytes = thumb_buffer.getvalue()

        return StandardizedImages(full=full_bytes, thumbnail=thumb_bytes)
