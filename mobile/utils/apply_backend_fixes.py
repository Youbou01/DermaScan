"""Apply the reviewed backend-only fixes. Dry run by default; never accesses the database.
Usage: python utils/apply_backend_fixes.py /path/to/dermascan/backend [--apply]
Run against the current linked backend revision, not an older deployed checkout.
"""
import argparse
import ast
from pathlib import Path

HOME_ROW = 'src/app/modules/catalog/home_repository.py'
HOME = 'src/app/modules/catalog/home_service.py'
SEARCH_ROUTER = 'src/app/modules/catalog/search_router.py'
SEARCH = 'src/app/modules/catalog/search_service.py'
CONTRIBUTIONS = 'src/app/api/v1/contributions.py'
VALIDATOR = '''IMAGE_FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}


async def _validated_photo(photo: UploadFile) -> tuple[bytes, str, str]:
    if photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG, or WebP photo.")
    photo_bytes = await photo.read(MAX_PHOTO_SIZE + 1)
    if not photo_bytes:
        raise HTTPException(status_code=400, detail="Uploaded photo file is empty.")
    if len(photo_bytes) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=413, detail="Photo file exceeds 10MB limit.")
    try:
        with Image.open(BytesIO(photo_bytes)) as image:
            image_format = image.format
            image.verify()
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=415, detail="Use a valid JPEG, PNG, or WebP photo.") from exc
    if image_format is None or image_format not in IMAGE_FORMATS:
        raise HTTPException(status_code=415, detail="Use a JPEG, PNG, or WebP photo.")
    extension, content_type = IMAGE_FORMATS[image_format]
    return photo_bytes, extension, content_type'''
OLD_UPLOAD = '''    # 2. Validate file type
    if photo.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type '{photo.content_type}'. Must be JPEG, PNG, or WebP.",
        )

    # Read and validate size
    photo_bytes = await photo.read()
    if len(photo_bytes) > MAX_PHOTO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Photo file exceeds 10MB limit.",
        )
    if len(photo_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded photo file is empty.",
        )

    # 3. Store photo securely
    file_id = uuid.uuid7()
    storage = get_storage_client()
    path = f"contributions/{file_id}.webp"
    image_url = await storage.put_image(path, photo_bytes, "image/webp")'''
NEW_UPLOAD = '''    # Validate bounded input and preserve its actual detected image format.
    photo_bytes, extension, content_type = await _validated_photo(photo)

    # 3. Store photo securely
    file_id = uuid.uuid7()
    storage = get_storage_client()
    path = f"contributions/{file_id}.{extension}"
    image_url = await storage.put_image(path, photo_bytes, content_type)'''
EDITS: dict[str, list[tuple[str, str, int]]] = {
    HOME_ROW: [
        ('    name_i18n: dict[str, str] | None = None', '    name_i18n: dict[str, str] | None = None\n    score_is_estimated: bool = False', 1),
        ('                name_i18n=product.name_i18n,', '                name_i18n=product.name_i18n,\n                score_is_estimated=product.score_is_estimated,', 2),
    ],
    HOME: [('        category_slug=row.category_slug,', '        category_slug=row.category_slug,\n        score_is_estimated=row.score_is_estimated,', 1)],
    SEARCH_ROUTER: [
        ('from app.core.dependencies import SessionDep', 'from app.core.dependencies import LocaleDep, SessionDep', 1),
        ('async def search_products(\n    service: SearchServiceDep,', 'async def search_products(\n    service: SearchServiceDep,\n    locale: LocaleDep,', 1),
        ('    return await service.search_by_name(q, limit=limit, cursor=cursor)', '    return await service.search_by_name(q, limit=limit, cursor=cursor, locale=locale)', 1),
        ('async def filter_products(\n    service: SearchServiceDep,', 'async def filter_products(\n    service: SearchServiceDep,\n    locale: LocaleDep,', 1),
        ('        cursor=cursor,\n    )', '        cursor=cursor,\n        locale=locale,\n    )', 1),
    ],
    SEARCH: [
        ('        self, q: str, *, limit: int, cursor: str | None', '        self, q: str, *, limit: int, cursor: str | None, locale: str = DEFAULT_LOCALE', 1),
        ('            items=[_summary(p) for p in rows[:page_size]],', '            items=[_summary(p, locale) for p in rows[:page_size]],', 1),
        ('        cursor: str | None,\n    ) -> Page[ProductSummary]:', '        cursor: str | None,\n        locale: str = DEFAULT_LOCALE,\n    ) -> Page[ProductSummary]:', 1),
        ('        return Page[ProductSummary](items=[_summary(p) for p in items], next_cursor=next_cursor)', '        return Page[ProductSummary](items=[_summary(p, locale) for p in items], next_cursor=next_cursor)', 1),
    ],
    CONTRIBUTIONS: [
        ('import uuid\n', 'from io import BytesIO\nimport uuid\n', 1),
        ('from pydantic import BaseModel, ConfigDict', 'from pydantic import BaseModel, ConfigDict\nfrom PIL import Image, UnidentifiedImageError', 1),
        ('from app.core.dependencies import get_session', 'from app.core.dependencies import get_session\nfrom app.core.errors import ProblemDetails', 1),
        ('ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}', 'ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}\n' + VALIDATOR, 1),
        ('@router.post("", response_model=ContributionResponse, status_code=status.HTTP_202_ACCEPTED)', '@router.post(\n    "", response_model=ContributionResponse, status_code=status.HTTP_202_ACCEPTED,\n    responses={code: {"model": ProblemDetails} for code in (400, 413, 415, 422)},\n)', 1),
        (OLD_UPLOAD, NEW_UPLOAD, 1),
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backend', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.backend.resolve()
    aggregator = root / 'src/app/api/v1/router.py'
    if not aggregator.exists() or 'router.include_router(suitability_router' not in aggregator.read_text():
        parser.error('Update to the linked backend revision including suitability before applying these fixes.')
    staged: dict[Path, str] = {}
    for relative, changes in EDITS.items():
        target = root / relative
        original = target.read_text()
        content = original
        for before, after, expected in changes:
            if content.count(after) == expected:
                continue
            if content.count(before) != expected:
                parser.error(f'{relative}: source differs from reviewed revision. No files changed; merge manually.')
            content = content.replace(before, after)
        ast.parse(content, filename=str(target))
        if content != original:
            staged[target] = content
    for source in sorted((Path(__file__).parent / 'backend-tests').glob('test_*.py')):
        target = root / 'tests/unit' / source.name
        content = source.read_text()
        ast.parse(content, filename=str(target))
        if not target.exists() or target.read_text() != content:
            staged[target] = content
    for target, content in staged.items():
        print(('Applying: ' if args.apply else 'Would update: ') + str(target))
        if args.apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
    if not staged:
        print('Reviewed fixes already present.')
    elif not args.apply:
        print('Dry run only. Review changes, then add --apply. No database access or deployment is performed.')


if __name__ == '__main__':
    main()
