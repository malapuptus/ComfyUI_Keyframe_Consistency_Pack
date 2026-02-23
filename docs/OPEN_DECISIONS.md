# OPEN_DECISIONS (append-only)

## 2026-02-23
- Assumption: `KCP_AssetPick` returns a warning/error when image path is recorded but file is missing; node currently raises `kcp_asset_image_missing`.
- Assumption: v1 render strategy remains Option 1 (manual wiring to KSampler); `KCP_RenderVariants` deferred to backlog.
- Assumption: compose ordering frozen as `global_rules -> style -> camera -> lighting -> environment -> action -> character`.
- Assumption: when Pillow is unavailable, KCP stores IMAGE payloads as `original.ppm` (stdlib fallback) and skips thumbnails with a warning.
- Assumption: strict `json_fields` validation is implemented via stdlib structural checks aligned to `asset.schema.json` (not a third-party JSON Schema engine).
- Assumption: `refresh_token` is a cache-busting input for picker nodes and is intentionally not persisted.
- Assumption: if thumbnail generation fails, KCP keeps the original PNG and returns a warning instead of failing the whole asset save.
- Assumption: if `assets.image_path` exists in DB but the file is missing on disk, `KCP_AssetPick` continues to raise `kcp_asset_image_missing`.
- Assumption: PPM fallback is removed; when IMAGE input is provided and Pillow is unavailable, `KCP_AssetSave` fails fast with `kcp_io_write_failed` and install guidance.
