# ComfyUI Keyframe Consistency Pack (KCP)

Standalone ComfyUI custom nodes for keyframe consistency workflows.

## Pillow requirement for image-writing paths
Text-only assets work without Pillow.

Pillow is required for any node path that writes images/thumbnails (for example `KCP_AssetSave` when `image` input is connected).

Install dependencies in your ComfyUI Python environment:

```bash
python -m pip install -r requirements.txt
```

Behavior when Pillow is missing:
- If `KCP_AssetSave.image` is connected, the node fails fast with:
  `kcp_io_write_failed: Pillow required to save IMAGE input; install with pip install pillow`
- No image/thumbnails are written.

## Thumbnail behavior
- Thumbnail format: `webp`
- Default max size: `384px`
- If thumbnail generation fails, KCP saves the original PNG and appends a warning in `asset_json.warnings`.

## json_fields validation (asset schema)
`KCP_AssetSave` validates non-empty `json_fields` strictly against `kcp/schemas/asset.schema.json`.

- If valid: the object is stored in `assets.json_fields`.
- If invalid: node raises `kcp_asset_validation_failed: <reason>`.

## Dropdown refresh pattern
`KCP_AssetPick` and `KCP_StackPick` include a `refresh_token` (`INT`, default `0`).

Usage:
- Increment `refresh_token` (for example `0 -> 1`) to force ComfyUI to treat inputs as changed and repopulate pick-list queries.
- Keep value stable for normal cached graph execution.

## v1 Quickstart (manual render)
This is the supported v1 flow (manual wiring to standard ComfyUI render nodes).

1) **Initialize project root and DB**
- Add `KCP_ProjectInit`.
- Keep default `kcp_root = "output/kcp"` unless you need a custom root.
- Capture outputs:
  - `db_path` (feed to all DB-backed KCP nodes)
  - `kcp_root_resolved` (resolved absolute root)
  - `status_json`
- `KCP_ProjectInit` is an output node (`OUTPUT_NODE=True`) so it can run without Preview/Save nodes.

2) **Create assets**
- Use `KCP_AssetSave` to create character/environment/camera/lighting/action assets.
- If `image` input is connected, Pillow is required.
- `KCP_AssetSave` is `OUTPUT_NODE=True`.

3) **Pick assets (safe on empty libraries)**
- Use `KCP_AssetPick` to retrieve fragments.
- `refresh_token` forces dropdown refresh.
- `strict=False` (default): empty selection returns empty outputs + `warning_json`.
- `strict=True`: missing selection raises (`kcp_asset_not_found`).

4) **Create and pick stacks**
- Use `KCP_StackSave` to persist stack references (`OUTPUT_NODE=True`).
- Use `KCP_StackPick` for retrieval.
- `refresh_token` forces dropdown refresh.
- `strict=False` (default): empty selection returns empty outputs + `warning_json`.
- `strict=True`: missing selection raises (`kcp_stack_not_found`).

5) **Compose prompt**
- Wire fragments into `KCP_PromptCompose`.
- Output:
  - `positive_prompt`
  - `negative_prompt`
  - `breakdown_json`

6) **Generate variants**
- Feed composed prompt into `KCP_VariantPack`.
- Choose built-in policy and count.
- Output `variant_list_json` (entire variant set).

7) **Pick one variant for render**
- Feed `variant_list_json` into `KCP_VariantPick`.
- Set `index` to choose the variant you want to render.
- Use outputs (`positive_prompt`, `negative_prompt`, `seed`, `steps`, `cfg`, `sampler`, `scheduler`, `denoise`, `width`, `height`) for render nodes.

8) **Manual render wiring to standard ComfyUI nodes**
- `positive_prompt` -> `CLIPTextEncode` (positive)
- `negative_prompt` -> `CLIPTextEncode` (negative)
- `seed/steps/cfg/sampler/scheduler/denoise` -> `KSampler`
- `width/height` -> latent/init path for your graph
- `KSampler` latent -> `VAE Decode` -> preview/save nodes

9) **Persist keyframe set metadata**
- Use `KCP_KeyframeSetSave` after variant generation to store set/items (`OUTPUT_NODE=True`).
- Use `KCP_KeyframeSetMarkPicked` after choosing winner to store `picked_index` (+ optional notes) (`OUTPUT_NODE=True`).



## Winner promotion addendum (v1)
- Use `KCP_KeyframeSetItemSaveImage` to attach a rendered IMAGE to `(set_id, idx)` and persist media under `sets/<set_id>/<idx>.*`.
- Use `KCP_KeyframeSetItemLoad` to preview/debug saved set items (image + prompts + gen params).
- Use `KCP_KeyframePromoteToAsset` to promote a winning set item into a reusable `keyframe` asset with provenance in `json_fields`.


## Keyframe set media persistence (v1)
- `KCP_KeyframeSetItemSaveImage` stores rendered item media under:
  - `sets/<set_id>/<idx>.webp` (default format)
  - `sets/<set_id>/<idx>_thumb.webp` (thumb)
- DB fields updated: `keyframe_set_items.image_path`, `keyframe_set_items.thumb_path`.
- With `overwrite=False`, existing media raises `kcp_set_item_media_exists`.
- `KCP_KeyframeSetItemLoad` reads saved media + prompt/params for preview/debug.
- `KCP_KeyframePromoteToAsset` promotes a chosen set item to `assets(type=keyframe)` with provenance in `json_fields`.
