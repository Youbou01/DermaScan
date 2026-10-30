# ADR-0017: Self-Hosted Image Pipeline and Asset Standardization
- Status: Accepted
- Date: 2026-10-30

## Context
Product images gathered from public sources (Open Beauty Facts, brand websites, retailer product pages) vary wildly in dimensions, aspect ratios, background clutter, and compression. Hotlinking third-party images creates privacy risks, broken links on third-party removals, and slow mobile loading times.

We require:
1. Complete elimination of hotlinked external assets in public catalog responses.
2. Production-grade standardization: high-resolution, centered packaging on a clean white square background with thumbnail generation.
3. Offline, zero-cost processing that runs asynchronously via the background worker queue.

## Decision

1. **Storage Layer Abstraction (`app/core/storage.py`):**
   - The application defines a `StorageClient` protocol (`put_image(key, data, content_type) -> public_url`, `get_image(key)`, `exists(key)`).
   - In development: MinIO runs locally in `docker-compose.yml`.
   - In production: Any free-tier S3-compatible object storage (Cloudflare R2, Backblaze B2, or self-hosted MinIO).
   - In tests and CI: `InMemoryStorageClient` operates 100% offline with zero external network dependencies.
   - Storage keys follow a deterministic, collision-free structure: `products/<barcode>/<sha256[:16]>.webp` and `products/<barcode>/<sha256[:16]>_thumb.webp`.

2. **Image Processing Pipeline (`app/modules/enrichment/images.py`):**
   - **Pre-filtering:** Rejects images with short side < 500 px, aspect ratio outside `[0.5, 2.0]`, or solid/empty color blocks.
   - **Background Normalization:** Uses a `BackgroundRemover` protocol. When `rembg` is present, it removes complex packaging backgrounds; otherwise, a robust Pillow fallback automatically trims border margins and transparent padding.
   - **Square Canvas Padding:** Centers the product on a pure white (`#FFFFFF`) 1024x1024 canvas with 10% outer padding.
   - **WebP Formatting:** Encodes full 1024x1024 WebP (quality 85) and 320x320 thumbnail WebP (quality 80) for optimal mobile delivery.

3. **Asynchronous Execution (`app/modules/enrichment/tasks.py`):**
   - Image downloading, validation, processing, and S3 uploads run via the background job `process_product_image(product_id)`.
   - The public HTTP request path never performs image downloads or transformations.
   - If no qualifying candidate image exists, the product sets `image_status = none` and `image_url = null`, prompting client applications to render native category illustration placeholders. Synthetic or generative AI product images are strictly forbidden.

## Consequences
- Every catalog image served to clients is optimized, self-hosted, deterministic, and fast to load.
- No third-party network requests occur when clients render product listings.
- Automated tests run completely offline and hermetically.
