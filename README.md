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
- Opinionated on-ramp for batched renders: wire `KSampler` decoded `IMAGE` output -> `KCP_KeyframeSetItemSaveBatch.images` to persist the full batch in one call.
- Use `KCP_KeyframeSetItemSaveImage` to attach a rendered IMAGE to `(set_id, idx)` and persist media under `sets/<set_id>/<idx>.*`.
- Use `KCP_KeyframeSetItemLoad` to preview/debug saved set items (image + prompts + gen params).
- Use `KCP_KeyframePromoteToAsset` to promote a winning set item into a reusable `keyframe` asset with provenance in `json_fields`.
- For single-queue ordering, wire `KCP_KeyframeSetItemSaveImage.item_json` -> `KCP_KeyframePromoteToAsset.depends_on_item_json` to enforce execution dependency.


## Keyframe set media persistence (v1)
- `idx` selects which keyframe set item row to update in DB (`keyframe_set_items.idx`).
- `batch_index` selects which image from the incoming IMAGE batch gets saved for that row (`0` = first image).
- `KCP_KeyframeSetItemSaveImage` stores rendered item media under:
  - `sets/<set_id>/<idx>.webp` (default format)
  - `sets/<set_id>/<idx>_thumb.webp` (thumb)
- DB fields updated: `keyframe_set_items.image_path`, `keyframe_set_items.thumb_path`.
- With `overwrite=False`, existing media raises `kcp_set_item_media_exists`.
- `KCP_KeyframeSetItemLoad` reads saved media + prompt/params for preview/debug.
- `KCP_KeyframePromoteToAsset` promotes a chosen set item to `assets(type=keyframe)` with provenance in `json_fields`.



## Opinionated On-Ramp: Render & Persist a Variant Pack
- `KCP_ProjectInit` first; wire `db_path` into every DB-backed KCP node.
- `KCP_VariantPack` -> `KCP_KeyframeSetSave` to persist set metadata and create `keyframe_set_items`.
- `KCP_VariantPack.variant_list_json` -> `KCP_VariantUnroll.variant_list_json`.
- `KCP_VariantUnroll` exposes list outputs (`idx_list`, prompts, seed/steps/cfg/sampler/scheduler/denoise/width/height) and uses ComfyUI list mapping so downstream render nodes run once per variant automatically.
- Wire `KCP_VariantUnroll.positive_list`/`negative_list` through CLIP encoders and `seed_list` + other params into `KSampler`.
- `VAE Decode` IMAGE -> `KCP_KeyframeSetItemSaveImage.image`.
- `KCP_KeyframeSetSave.set_id` -> `KCP_KeyframeSetItemSaveImage.set_id`.
- `KCP_VariantUnroll.idx_list` -> `KCP_KeyframeSetItemSaveImage.idx`.
- For full-set persistence in one node call, you can alternatively wire decoded IMAGE batch into `KCP_KeyframeSetItemSaveBatch.images` with `idx_start=0` (recommended for batch tensors).
- Persist full batch wiring: `KSampler IMAGE -> KCP_KeyframeSetItemSaveBatch.images` (use `idx_start` so batch element `0` maps to set item `idx_start`, element `1` maps to `idx_start+1`, etc.).
- Terminology: `idx` is the DB item index in `keyframe_set_items`; `batch_index` selects one image inside an incoming IMAGE batch tensor.
- Example workflow JSON: `examples/workflows/opinionated_onramp_render_persist_variant_pack.json`.

## Troubleshooting db_path
- Expected `db_path` pattern is `.../output/kcp/db/kcp.sqlite` (or another real sqlite file path).
- If you point `db_path` at a directory (for example `.../output/kcp`), nodes raise: `kcp_db_path_is_directory: expected .../db/kcp.sqlite`.
- If the parent directory does not exist, nodes raise: `kcp_db_path_parent_missing: <parent>`.

## db_path: do this every time
- Always wire `KCP_ProjectInit.db_path` into every DB-backed KCP node.
- Canonical relative example: `output/kcp/db/kcp.sqlite`
- Canonical Windows absolute example: `C:\ComfyUI\output\kcp\db\kcp.sqlite`

## Common errors
- `kcp_db_path_is_directory`: you passed a folder like `.../output/kcp` where a sqlite file path is required.
- `kcp_db_path_parent_missing`: the parent directory for the sqlite file does not exist.
- `kcp_io_write_failed`: image/thumb write failed; current diagnostics include `root=`, `image_path=`, and `err=`.

SaveImage format note: invalid `format` values are coerced to `webp`.


## Pick Winner (v1): preview → choose → mark → promote
- `KCP_KeyframeSetPick.set_id` -> `KCP_KeyframeSetLoadBatch.set_id`
- `KCP_KeyframeSetItemPick.item_json` -> `KCP_KeyframeSetMarkPicked.item_json`
- `KCP_KeyframeSetItemPick.item_json` -> `KCP_KeyframePromoteToAsset.item_json`
- This item_json wiring avoids manual typing of set_id/idx for mark/promote.
- Example workflow JSON: `examples/workflows/opinionated_onramp_render_persist_variant_pack.json`.

## Pick Winner (v1): preview grid → choose idx → mark picked → promote
- Use `KCP_KeyframeSetPick` to choose a recent set and output `set_id`.
- Feed `set_id` into `KCP_KeyframeSetLoadBatch` and send `images` (or `thumbs`) to `PreviewImage` to review the saved grid.
- `KCP_KeyframeSetLoadBatch` also returns `labels_json` so each batch slot has an explicit `{idx,status,seed,label}` descriptor.
- Use `KCP_KeyframeSetItemPick` to choose a candidate item and output both `idx` and `item_json` (prefer saved media with `only_with_media=True`).
- Least-typing path: wire `KCP_KeyframeSetItemPick.item_json` → `KCP_KeyframeSetMarkPicked.item_json`, set `picked_index=-1`, and mark is derived automatically.
- Least-typing path: wire the same `item_json` → `KCP_KeyframePromoteToAsset.item_json`, leave `set_id` blank and `idx=-1`, and promote derives set/item automatically.
- Optional: use `KCP_KeyframeSetSummary` to print `N items, M saved media, picked=X` and return status JSON for downstream logs.
- Promote keeps prompt DNA in both `assets.positive_fragment`/`assets.negative_fragment` and `assets.json_fields.prompt.{positive,negative}` and writes media paths on the asset.


## Troubleshooting: why nodes don’t appear
- Confirm the pack root `__init__.py` is present in `ComfyUI/custom_nodes/ComfyUI_Keyframe_Consistency_Pack/` and exports `NODE_CLASS_MAPPINGS`.
- Clear stale bytecode caches (`__pycache__` folders) after updates/reverts.
- Quick import sanity check in Comfy Python:
  - `python -c "import ComfyUI_Keyframe_Consistency_Pack as k; print('KCP_IMPORT_OK', bool(getattr(k, 'NODE_CLASS_MAPPINGS', {})))"`
- Install dependencies using the same Python environment that runs ComfyUI:
  - portable: `python_embeded\python.exe -m pip install -r requirements.txt`
  - other installs: `python -m pip install -r requirements.txt`
