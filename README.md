# ComfyUI Keyframe Consistency Pack (KCP)

Standalone ComfyUI custom nodes for keyframe consistency workflows.

## Pillow requirement for image-writing paths
Text-only assets work without Pillow.

Pillow is required for any node path that writes images/thumbnails (for example `KCP_AssetSave` when `image` input is connected).

Install Pillow in your ComfyUI Python environment:

```bash
python -m pip install Pillow
```

Behavior when Pillow is missing:
- If `KCP_AssetSave.image` is connected, the node fails fast with:
  `kcp_io_write_failed: Pillow required to save IMAGE input; install with pip install pillow`
- No image/thumbnails are written.

## Thumbnail behavior
- Thumbnail format: `webp`
- Default max size: `384px`
- If thumbnail generation fails, KCP still saves the original PNG and appends a warning in `asset_json.warnings`.

## json_fields validation (asset schema)
`KCP_AssetSave` validates non-empty `json_fields` strictly against `kcp/schemas/asset.schema.json`.

- If valid: the object is stored in `assets.json_fields`.
- If invalid: node raises `kcp_asset_validation_failed: <reason>`.

## Dropdown refresh pattern
`KCP_AssetPick` and `KCP_StackPick` include a `refresh_token` (`INT`, default `0`).

Usage:
- Increment `refresh_token` (for example `0 -> 1`) to force ComfyUI to treat inputs as changed and repopulate pick-list queries.
- Keep value stable for normal cached graph execution.
