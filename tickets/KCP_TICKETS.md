> Canonical ticket format: `tickets/TEMPLATE.md`.

Ticket KCP-001 — Initialize DB pathing and migration bootstrap
Goal (1 sentence): Implement project initialization that creates KCP filesystem layout and migrates SQLite schema to latest.
Scope:
- Add path resolution and layout creation helpers.
- Add migration runner using PRAGMA user_version.
Must include:
- kcp/db/paths.py
- kcp/db/migrate.py
- KCP_ProjectInit node wiring
Must NOT include:
- Non-v1 schema migrations
- Rendering nodes
Acceptance criteria:
- New DB is created at expected location.
- PRAGMA user_version is set to 1 after init.
Evidence needed (what to paste/verify):
- tools/context output.
- tools/verify receipt with batch label.
Notes / implementation hints:
- Keep all paths pathlib-based and Windows-first portable.
Risks:
- Incorrect relative/absolute path behavior across environments.

Ticket KCP-002 — Add v1 schema DDL and migration script
Goal (1 sentence): Implement schema_v1 with assets, stacks, keyframe sets/items, projects, and shots tables.
Scope:
- Add SQL DDL file and migration application.
Must include:
- kcp/db/schema_v1.sql
- migration application in kcp/db/migrate.py
Must NOT include:
- v2 columns or destructive table rebuilds
Acceptance criteria:
- All expected tables and indexes exist after migration.
Evidence needed (what to paste/verify):
- compileall output and verify pass.
Notes / implementation hints:
- Keep migration additive and idempotent.
Risks:
- SQL typo causes migration failure.

Ticket KCP-003 — Implement asset repository CRUD primitives
Goal (1 sentence): Add repository functions for creating, fetching, and listing assets.
Scope:
- Create connection helper and asset CRUD.
Must include:
- create_asset
- get_asset_by_type_name
- list_asset_names
Must NOT include:
- Cross-pack integrations
Acceptance criteria:
- Asset rows can be inserted and queried by type/name.
Evidence needed (what to paste/verify):
- verify output and touched symbols.
Notes / implementation hints:
- Maintain UNIQUE(type,name) semantics.
Risks:
- Conflict handling for save_mode variants.

Ticket KCP-004 — Implement KCP_AssetSave node
Goal (1 sentence): Persist asset prompt fragments, metadata, and optional image/thumb with warnings.
Scope:
- Add node implementation and persistence wiring.
Must include:
- Environment-without-plate warning.
- Hashing image files when saved.
Must NOT include:
- Custom frontend picker UI
Acceptance criteria:
- Node returns asset_id and asset_json.
Evidence needed (what to paste/verify):
- verify output and sample node payload output.
Notes / implementation hints:
- Use atomic file writes where feasible.
Risks:
- Unsupported incoming IMAGE runtime type.

Ticket KCP-005 — Implement KCP_AssetPick node
Goal (1 sentence): Resolve an asset by type/name and return prompt fragments + JSON payload.
Scope:
- Add DB lookup and missing-image behavior.
Must include:
- kcp_asset_not_found and kcp_asset_image_missing errors.
Must NOT include:
- Thumbnail gallery UI
Acceptance criteria:
- Existing asset returns core fields.
Evidence needed (what to paste/verify):
- verify output and chosen open decision record.
Notes / implementation hints:
- Re-query DB for dropdown refresh strategy.
Risks:
- Stale dropdown values if DB changes externally.

Ticket KCP-006 — Implement stack save/pick repository and nodes
Goal (1 sentence): Save and pick stack bundles that reference assets and expose fragments.
Scope:
- Save stack refs and pick with fragment expansion.
Must include:
- KCP_StackSave and KCP_StackPick.
Must NOT include:
- Shotlist UI orchestration
Acceptance criteria:
- Stack row upsert works and pick returns fragments.
Evidence needed (what to paste/verify):
- verify output and stack JSON example.
Notes / implementation hints:
- Validate FK references through sqlite constraints.
Risks:
- Missing referenced assets causing runtime errors.

Ticket KCP-007 — Implement deterministic prompt composer
Goal (1 sentence): Compose deterministic positive/negative prompts and structured breakdown JSON.
Scope:
- Ordered concatenation and optional light dedupe.
Must include:
- Frozen v1 order: global_rules > style > camera > lighting > environment > action > character.
Must NOT include:
- AI-based rewriting/refinement logic
Acceptance criteria:
- Same inputs always produce same outputs.
Evidence needed (what to paste/verify):
- verify output and composer ordering snippet.
Notes / implementation hints:
- Keep mode behavior minimal and explicit.
Risks:
- Over-dedupe changes semantics unexpectedly.

Ticket KCP-008 — Build policy engine and built-in templates
Goal (1 sentence): Add built-in policy templates and deterministic variant emission logic.
Scope:
- camera_coverage_12_v1, lens_bracket_3x4_v1, seed_sweep_12_v1, micro_variation_12_v1.
Must include:
- Seed derivation from base_seed offsets.
Must NOT include:
- v2 pose/control policy logic
Acceptance criteria:
- Engine returns policy-conformant variant payloads.
Evidence needed (what to paste/verify):
- verify output and policy IDs list.
Notes / implementation hints:
- Keep overrides minimal in v1.
Risks:
- Count/injection mismatch edge cases.

Ticket KCP-009 — Implement KCP_VariantPack node
Goal (1 sentence): Expose policy engine through node outputs as variant_list_json and preview text.
Scope:
- Node input/output contract and JSON serialization.
Must include:
- Built-in policy dropdown.
Must NOT include:
- Internal sampler/render loop
Acceptance criteria:
- Node returns non-empty variants for each built-in policy.
Evidence needed (what to paste/verify):
- verify output and preview snippet.
Notes / implementation hints:
- Parse policy_overrides_json as object.
Risks:
- Invalid overrides JSON handling.

Ticket KCP-010 — Implement keyframe set persistence node
Goal (1 sentence): Save keyframe set headers and all variant items with generation receipts.
Scope:
- Create keyframe_set row and insert set items from variant_list_json.
Must include:
- picked_index handling.
Must NOT include:
- Continuity critic scoring logic
Acceptance criteria:
- Item rows persist with gen_params_json.
Evidence needed (what to paste/verify):
- verify output and saved count.
Notes / implementation hints:
- Preserve variant index from payload when present.
Risks:
- Invalid variant payload shape.

Ticket KCP-011 — Implement ProjectStatus plates-first gating
Goal (1 sentence): Provide readiness signals and warnings for plate-first workflows.
Scope:
- Environment presence and plate-image checks.
Must include:
- status_text, status_json, is_ready_for_keyframes outputs.
Must NOT include:
- Custom panel UI
Acceptance criteria:
- Missing plate states produce warnings and false readiness.
Evidence needed (what to paste/verify):
- verify output and status payload example.
Notes / implementation hints:
- Keep checks simple and deterministic.
Risks:
- False readiness if DB paths are stale.

Ticket KCP-012 — Finalize docs, verify tooling, and v1 stop gate
Goal (1 sentence): Add bootstrap docs/tools, run compile/verify, and stop at v1 scaffolding.
Scope:
- AGENTS/CONSTITUTION/docs + tools/context/verify + ticket set.
Must include:
- verify receipt content with batch and oracle markers.
Must NOT include:
- v2/v3 feature implementation
Acceptance criteria:
- python tools/context.py and tools/verify.py run successfully.
Evidence needed (what to paste/verify):
- exact command outputs and receipt path.
Notes / implementation hints:
- Keep docs append-only where specified.
Risks:
- Receipt output drift from expected key labels.

Ticket KCP-023 — Fix VariantPack UI constraints and defaults
Status: DONE
Goal (1 sentence): Make KCP_VariantPack inputs sane and hard-to-misuse (seed range, defaults, JSON field defaults).
Acceptance criteria:
- base_seed supports standard 32-bit positive seed range.
- sampler/scheduler defaults are non-JSON prompt-friendly defaults.
- verify completes with receipt KCP-023.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-023"

Ticket KCP-024 — Guardrail db_path inputs
Status: DONE
Goal (1 sentence): Validate db_path inputs and raise actionable errors for directory and missing-parent cases.
Acceptance criteria:
- directory db_path raises kcp_db_path_is_directory.
- missing parent raises kcp_db_path_parent_missing.
- verify completes with receipt KCP-024.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-024"

Ticket KCP-025 — Auto-migrate on DB connect
Status: DONE
Goal (1 sentence): Ensure connect() applies migrations so required tables exist on fresh sqlite files.
Acceptance criteria:
- opening empty sqlite file creates v1 schema.
- keyframe_set_items table exists after connect.
- verify completes with receipt KCP-025.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-025"

Ticket KCP-026 — Diagnose SaveImageIntoSetItem failures
Status: DONE
Goal (1 sentence): Include resolved paths and underlying exception details in set-item image write errors.
Acceptance criteria:
- failure message contains image_path and err fields.
- failure message includes set_id/idx context.
- verify completes with receipt KCP-026.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-026"

Ticket KCP-027 — Fix SaveImageIntoSetItem root consistency
Status: DONE
Goal (1 sentence): Ensure set-item image writes use canonical KCP root resolution aligned with ProjectInit behavior.
Acceptance criteria:
- relative output/kcp root resolves under ComfyUI output directory when available.
- no ad-hoc cwd-only write root pathing for set-item save path.
- verify completes with receipt KCP-027.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-027"

Ticket KCP-028 — Promote ordering dependency input
Status: DONE
Goal (1 sentence): Add dependency input to promote node so workflows can enforce save-before-promote ordering.
Acceptance criteria:
- promote input contract includes depends_on_item_json.
- dependency input can be wired to create execution order edge.
- verify completes with receipt KCP-028.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-028"

Ticket KCP-029 — End-to-end persistence smoke
Status: DONE
Goal (1 sentence): Add synthetic end-to-end smoke covering set save-image, load, and promote flow.
Acceptance criteria:
- smoke confirms DB updates and filesystem outputs in one flow.
- no external model/runtime dependencies required for smoke.
- verify completes with receipt KCP-029.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-029"

Ticket KCP-030 — Fix KeyframeSetSave UI constraints and defaults
Status: DONE
Goal (1 sentence): Add safe UI bounds to KeyframeSetSave seed/size/picked_index inputs while preserving DB semantics.
Acceptance criteria:
- base_seed min/max bounds are present.
- width/height min 64 and picked_index min/max bounds are present.
- verify completes with receipt KCP-030.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-030"

Ticket KCP-031 — Make Promote dependency input optional
Status: DONE
Goal (1 sentence): Make depends_on_item_json optional in promote INPUT_TYPES while keeping behavior unchanged.
Acceptance criteria:
- depends_on_item_json is under optional inputs.
- promote still runs when dependency input is not connected.
- verify completes with receipt KCP-031.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-031"

Ticket KCP-032 — Add canonical ticket template file
Status: DONE
Goal (1 sentence): Add explicit canonical ticket template and references to prevent ticket structure drift.
Acceptance criteria:
- tickets/TEMPLATE.md exists with required sections and NONE rule.
- KCP_TICKETS and AGENTS reference the template.
- verify completes with receipt KCP-032.
Evidence needed (what to paste/verify):
- tools/verify.py --receipt "KCP-032"

# Ticket KCP-043 — Visible batch_index on KCP_KeyframeSetItemSaveImage

Status: DONE

Goal (1 sentence): Expose batch_index as a visible input so users can save a chosen image from a batched render.

Scope:

Must include:
- `KCP_KeyframeSetItemSaveImage.INPUT_TYPES.required` includes `batch_index` INT (`default: 0`, `min: 0`).
- `run()` selects batch element for `[B,H,W,C]` tensors and raises `kcp_batch_index_oob` when invalid.

Must NOT include:
- No schema changes.
- No behavior changes beyond UI/input exposure and existing OOB signaling.

Acceptance criteria:
- Node UI shows `batch_index`.
- `batch_index=7` can select the 8th image from a batch.
- Invalid index raises `kcp_batch_index_oob`.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-043"`

Notes / implementation hints:
- Keep `batch_index` non-optional to ensure ComfyUI widget visibility.

Risks:
- NONE.

# Ticket KCP-044 — Promote stores prompt DNA

Status: DONE

Goal (1 sentence): When promoting a set item to a keyframe asset, store prompt text on asset fields and in `json_fields.prompt` for reproducibility.

Scope:

Must include:
- Store `positive_prompt`/`negative_prompt` as `assets.positive_fragment` and `assets.negative_fragment`.
- Persist `json_fields.prompt = {"positive": ..., "negative": ...}` in promoted asset payload.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Promoted asset JSON includes `json_fields.prompt` with both prompts.
- `AssetPick` returns prompt fragments for promoted keyframe assets.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-044"`

Notes / implementation hints:
- Preserve existing provenance fields; append prompt DNA section.

Risks:
- NONE.

# Ticket KCP-045 — AssetPick dropdown refresh reliability

Status: DONE

Goal (1 sentence): Ensure `KCP_AssetPick.asset_name` choices populate from DB and refresh path is reliable when `db_path` is blank/defaulted.

Scope:

Must include:
- Build `asset_name` options from DB via `INPUT_TYPES` helper.
- Normalize blank `db_path` to default db path value for choice-building.
- Keep `refresh_token`-triggered rebuild behavior.

Must NOT include:
- No frontend JS changes.
- No schema changes.

Acceptance criteria:
- Saved assets appear in `asset_name` choices after refresh.
- Existing DB entries are shown on launch when path resolves.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-045"`

Notes / implementation hints:
- INPUT_TYPES-time path context is static; rely on provided/default `db_path`.

Risks:
- Medium-low due to ComfyUI dropdown caching differences.

# Ticket KCP-046 — KeyframeSetSave policy-id fallback

Status: DONE

Goal (1 sentence): If `variant_policy_id` input is blank, derive it from `variant_list_json.policy_id` without overriding non-empty input.

Scope:

Must include:
- Add fallback logic in `KCP_KeyframeSetSave` for blank policy ID.
- Preserve explicit user-entered `variant_policy_id` when non-empty.

Must NOT include:
- No schema changes.

Acceptance criteria:
- VariantPack → KeyframeSetSave flow works without manually typing policy ID.
- Stored `keyframe_sets.variant_policy_id` matches derived policy.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-046"`

Notes / implementation hints:
- Use parsed `variant_list_json` object and `policy_id` key.

Risks:
- NONE.

# Ticket KCP-047 — Robust ComfyUI pack entrypoint

Status: DONE

Goal (1 sentence): Ensure ComfyUI loads KCP nodes by making pack-root `__init__.py` add its directory to `sys.path` before importing `kcp` mappings.

Scope:

Must include:
- In repo-root `__init__.py`, insert:
  - `_THIS_DIR = os.path.dirname(os.path.abspath(__file__))`
  - prepend `_THIS_DIR` to `sys.path` when missing.
- Export `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` from `kcp` via `__all__`.
- Add verify smoke simulating `custom_nodes/<pack>` import path with non-empty mappings assertion.

Must NOT include:
- No node behavior changes.

Acceptance criteria:
- Importing package from custom_nodes-style path yields non-empty `NODE_CLASS_MAPPINGS`.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-047"`

Notes / implementation hints:
- Validate with importlib spec loading from copied temp package directory.

Risks:
- NONE.

# Ticket KCP-048 — Save an entire render batch into a keyframe set (single node)

Status: DONE

Goal (1 sentence): Enable users to persist all images from a single ComfyUI render batch into `keyframe_set_items` in one step.

Scope:

Must include:
- New node `KCP_KeyframeSetItemSaveBatch` in `kcp/nodes/keyframe_set_item_save_batch.py`.
- Required inputs: `db_path`, `set_id`, `idx_start`, `images`, `format`, `overwrite`.
- Batch mapping: `batch[0] -> idx_start`, `batch[1] -> idx_start+1`, etc.
- Canonical media writes under `sets/<set_id>/<idx>.*` plus DB media field updates.
- Actionable missing-index error listing first missing idx.
- README on-ramp wiring note (`KSampler IMAGE -> KCP_KeyframeSetItemSaveBatch.images`).
- Verify smoke for 3-item synthetic batch + DB/file assertions.

Must NOT include:
- No schema changes.
- No behavior changes to existing nodes.
- No custom UI panels.

Acceptance criteria:
- One node call persists an entire render batch to matching set items.
- `python tools/verify.py --receipt "KCP-048"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-048"`

Notes / implementation hints:
- Reuse `save_comfy_image_atomic()` and `make_thumbnail()`.

Risks:
- Medium due to IMAGE batch-shape variability.

# Ticket KCP-049 — Expose batch_index on KCP_KeyframeSetItemSaveImage (UI-visible)

Status: DONE

Goal (1 sentence): Make `batch_index` visible so users can select any image from a render batch for single-item saves.

Scope:

Must include:
- `batch_index` in required visible INPUT_TYPES (`INT`, default `0`, min `0`).
- Batched selection behavior in `run()`.
- Out-of-bounds raises `kcp_batch_index_oob` and is not swallowed.
- README clarification for `idx` (DB row) vs `batch_index` (render-batch index).
- Verify asserts both selection and OOB behavior.

Must NOT include:
- No schema changes.
- No changes to successful non-batched behavior.

Acceptance criteria:
- UI shows `batch_index` and selection works.
- `python tools/verify.py --receipt "KCP-049"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-049"`

Notes / implementation hints:
- Keep node for surgical one-item writes.

Risks:
- Low.

# Ticket KCP-050 — Promote stores prompt DNA on keyframe assets

Status: DONE

Goal (1 sentence): Ensure promoted keyframe assets keep full prompt DNA in fragments and `json_fields.prompt`.

Scope:

Must include:
- `assets.positive_fragment = item["positive_prompt"]`.
- `assets.negative_fragment = item["negative_prompt"]`.
- `assets.json_fields.prompt = {"positive": ..., "negative": ...}` while preserving existing JSON provenance.
- Verify smoke checking fragment fields and JSON prompt payload.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Promoted assets contain full prompt DNA in both storage locations.
- `python tools/verify.py --receipt "KCP-050"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-050"`

Notes / implementation hints:
- Reuse existing promote provenance structure.

Risks:
- Low.

# Ticket KCP-051 — Clean up KeyframeSetSave policy fallback (no duplicate dict keys)

Status: DONE

Goal (1 sentence): Keep policy-id fallback while ensuring the set payload contains exactly one `variant_policy_id` key.

Scope:

Must include:
- Use user input policy when non-empty, else `variant_list_json.policy_id`.
- Keep payload dict unambiguous with a single `variant_policy_id` entry.
- Verify smoke for fallback behavior and source-hygiene check.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Fallback behavior remains correct and source payload is clean.
- `python tools/verify.py --receipt "KCP-051"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-051"`

Notes / implementation hints:
- Count key occurrences in source as a safety smoke.

Risks:
- Very low.

# Ticket KCP-052 — Unroll VariantPack into ComfyUI lists (auto-run N variants)

Status: DONE

Goal (1 sentence): Turn `variant_list_json` into list outputs so ComfyUI can automatically render N variants via list-mapped execution.

Scope:

Must include:
- Add node `KCP_VariantUnroll` in `kcp/nodes/variant_unroll.py`.
- Input: `variant_list_json` (`STRING`, multiline).
- Return list outputs for idx/prompts/gen params and mark `OUTPUT_IS_LIST` for each.
- Register node in `kcp/__init__.py` mappings.

Must NOT include:
- No DB writes.
- No sampling loop / no KSampler calls.
- No dependency on other node packs.

Acceptance criteria:
- Given N variants, output lists have length N and values match payload.
- `python -m compileall kcp` passes.
- `python tools/verify.py --receipt "KCP-052"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-052"`

Notes / implementation hints:
- Use `parse_json_object` and fallback to enumerate index.
- Emit `gen_params_json_list` as one JSON string per variant.

Risks:
- Medium due to list-mapping behavior differences across user graphs.

# Ticket KCP-053 — Opinionated on-ramp: render + persist all variants (README + workflow)

Status: DONE

Goal (1 sentence): Make the happy path obvious for rendering and persisting all variants from one variant pack.

Scope:

Must include:
- README section: `Opinionated On-Ramp: Render & Persist a Variant Pack`.
- Explicit wiring with `KCP_ProjectInit`, `KCP_VariantPack`, `KCP_KeyframeSetSave`, `KCP_VariantUnroll`, render nodes, and save node.
- Add example workflow JSON under `examples/workflows/`.

Must NOT include:
- No feature changes beyond docs/example asset.
- No schema changes.

Acceptance criteria:
- README explains why list mapping renders N variants automatically.
- Example workflow file is present and wiring is documented.
- `python tools/verify.py --receipt "KCP-053"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-053"`

Notes / implementation hints:
- Keep `idx` vs `batch_index` explanation short and explicit.

Risks:
- Low.

# Ticket KCP-054 — Full-set save: save N images reliably (standardized path)

Status: DONE

Goal (1 sentence): Ensure there is one reliable way to persist all rendered variants into the set without manual repetition.

Scope:

Must include:
- Standardize on full-set persistence via `KCP_KeyframeSetItemSaveBatch` for batch tensors.
- Keep `KCP_KeyframeSetItemSaveImage` for single-item surgical saves.
- Verify smoke confirms N images saved and N DB rows updated.

Must NOT include:
- No render loop.
- No schema changes.

Acceptance criteria:
- N synthetic images are written under `sets/<set_id>/...` and N DB rows are updated.
- `python tools/verify.py --receipt "KCP-054"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-054"`

Notes / implementation hints:
- Smoke should validate both filesystem and DB updates.

Risks:
- Medium due to IMAGE shape differences across environments.

# Ticket KCP-055 — Make pick & promote winner retain full prompt DNA

Status: DONE

Goal (1 sentence): Ensure promoted keyframe assets retain full positive/negative prompt DNA for reproducibility.

Scope:

Must include:
- Ensure `json_fields.prompt` stores full `positive` and `negative` prompt values.
- Keep `positive_fragment` / `negative_fragment` aligned to full prompts on promoted assets.
- Verify smoke asserts prompt DNA values after promote.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Promoted asset JSON contains prompt DNA values matching set-item prompts.
- `python tools/verify.py --receipt "KCP-055"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-055"`

Notes / implementation hints:
- Preserve existing provenance fields while adding prompt DNA.

Risks:
- Low.

# Ticket KCP-056 — Make VariantUnroll sampler/scheduler wire-compatible with KSampler

Status: DONE

Goal (1 sentence): Ensure VariantUnroll outputs sampler/scheduler in a wire-compatible type for KSampler.

Scope:

Must include:
- Update `KCP_VariantUnroll.RETURN_TYPES` sampler/scheduler slots to ComfyUI-compatible typed outputs (`SAMPLER_NAME`, `SCHEDULER`).
- Update workflow example notes to reflect direct wiring.

Must NOT include:
- No DB changes.
- No variant policy behavior changes.
- No render loop node.

Acceptance criteria:
- Example wiring has no type-mismatch broken links for sampler/scheduler.
- `python -m compileall kcp` passes.
- `python tools/verify.py --receipt "KCP-056"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-056"`

Notes / implementation hints:
- Keep semantics unchanged; type compatibility only.

Risks:
- Medium due to ComfyUI type strictness.

# Ticket KCP-057 — Add KeyframeSetLoadBatch for previewing saved variants as a grid

Status: DONE

Goal (1 sentence): Let users preview an entire saved set via a single IMAGE batch output.

Scope:

Must include:
- Add `KCP_KeyframeSetLoadBatch` in `kcp/nodes/keyframe_set_load_batch.py`.
- Inputs: `db_path`, `set_id`, `strict`, optional `only_with_media`.
- Outputs: `images`, `thumbs`, `items_json`.
- Missing media behavior: strict raises `kcp_set_media_missing`, non-strict skips and emits warning payload.

Must NOT include:
- No schema changes.
- No custom UI panel.

Acceptance criteria:
- Set with N saved images returns batch size N.
- Verify smoke writes/loads two images and asserts count=2.
- `python tools/verify.py --receipt "KCP-057"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-057"`

Notes / implementation hints:
- Reuse existing image IO loader for format consistency.

Risks:
- Medium due to batch-shape handling variance.

# Ticket KCP-058 — Add KeyframeSetPick (dropdown set selector)

Status: DONE

Goal (1 sentence): Provide ergonomic set selection via dropdown with `set_id` output.

Scope:

Must include:
- Add `KCP_KeyframeSetPick` node in `kcp/nodes/keyframe_set_pick.py`.
- Inputs: `db_path`, `include_empty`, `refresh_token`, `strict`, dropdown `set_choice`.
- Outputs: `set_id`, `set_json`, `warning_json`.
- strict=False blank selection returns warning payload; strict=True raises `kcp_set_not_found`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Created sets appear in dropdown choices ordered newest first.
- Verify smoke confirms INPUT_TYPES contains created set after refresh.
- `python tools/verify.py --receipt "KCP-058"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-058"`

Notes / implementation hints:
- Normalize blank db_path using the same default pattern as picker nodes.

Risks:
- Low.

# Ticket KCP-059 — Add KeyframeSetItemPick (dropdown index selector)

Status: DONE

Goal (1 sentence): Let users pick set item index via dropdown with saved-media preference.

Scope:

Must include:
- Add `KCP_KeyframeSetItemPick` node in `kcp/nodes/keyframe_set_item_pick.py`.
- Inputs: `db_path`, `set_id`, `only_with_media`, `refresh_token`, `strict`, dropdown `item_choice`.
- Outputs: `idx`, `item_json`, `warning_json`.
- strict True missing raises `kcp_set_item_not_found`; strict False returns warning payload.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Dropdown labels include saved/missing status and filter correctly with `only_with_media`.
- Verify smoke confirms filtered vs unfiltered choices differ as expected.
- `python tools/verify.py --receipt "KCP-059"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-059"`

Notes / implementation hints:
- Keep refresh-token and safe-choice behavior aligned with existing picker conventions.

Risks:
- Medium due to dropdown refresh behavior variability.

# Ticket KCP-060 — Opinionated “Pick Winner” loop (docs-only)

Status: DONE

Goal (1 sentence): Document a straightforward v1 winner-pick loop using set pick, grid preview, item pick, mark picked, and promote.

Scope:

Must include:
- README section `Pick Winner (v1): preview grid → choose idx → mark picked → promote`.
- Explicit wiring for `KCP_KeyframeSetPick`, `KCP_KeyframeSetLoadBatch`, `KCP_KeyframeSetItemPick`, `KCP_KeyframeSetMarkPicked`, `KCP_KeyframePromoteToAsset`.
- Clarify promote outcome: reusable keyframe asset with prompt DNA and media paths.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Docs are explicit enough to follow without guessing.
- `python tools/verify.py --receipt "KCP-060"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-060"`

Notes / implementation hints:
- Keep wording concise but actionable.

Risks:
- Low.

# Ticket KCP-061 — KeyframeSetSave auto-fills stack_id from Stack JSON

Status: DONE

Goal (1 sentence): Reduce wiring friction by deriving `stack_id` when user input is blank and stack JSON is provided.

Scope:

Must include:
- In `KCP_KeyframeSetSave`, if `stack_id` is blank, derive from `stack_json.stack_id` or `stack_json.id`.
- Do not override non-empty user `stack_id`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Variant flow saves set when `stack_json` is wired and `stack_id` is blank.
- Verify smoke passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-061"`

Notes / implementation hints:
- Parse with existing `parse_json_object` and raise actionable error when unresolved.

Risks:
- Low.

# Ticket KCP-062 — KeyframeSetSave stores model_ref + compose breakdown

Status: DONE

Goal (1 sentence): Capture reproducibility provenance by storing model reference and compose breakdown JSON with set metadata.

Scope:

Must include:
- Add optional `model_ref` and `breakdown_json` inputs on `KCP_KeyframeSetSave`.
- Persist `model_ref` to `keyframe_sets.model_ref`.
- Persist breakdown payload into existing `variant_policy_json` structure (e.g., `compose_breakdown`).

Must NOT include:
- No schema changes.

Acceptance criteria:
- DB row includes `model_ref` and breakdown content.
- Verify smoke passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-062"`

Notes / implementation hints:
- Use existing schema columns only.

Risks:
- Medium if provenance payload collides; keep additive merge.

# Ticket KCP-063 — AssetPick returns image/thumb tensors on success

Status: DONE

Goal (1 sentence): Make `KCP_AssetPick` return media tensors when referenced media exists.

Scope:

Must include:
- On successful pick with existing `image_path`/`thumb_path`, load and return tensors.
- Keep strict/non-strict missing-media behavior unchanged.

Must NOT include:
- No behavior changes for missing or empty-media paths.

Acceptance criteria:
- Verify smoke confirms non-None `image` and `thumb_image` outputs for media-backed assets.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-063"`

Notes / implementation hints:
- Reuse existing `load_image_as_comfy` helper.

Risks:
- Medium due to image IO path/loading variance.

# Ticket KCP-064 — Refresh UX convention across Pick nodes

Status: DONE

Goal (1 sentence): Standardize refresh-token-driven dropdown rebuild behavior across all pick nodes.

Scope:

Must include:
- Ensure AssetPick / StackPick / KeyframeSetPick / KeyframeSetItemPick accept `refresh_token` and rebuild choices path with it.
- Add verify smoke toggling refresh flow and asserting updated choices.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Verify smoke confirms updated choices are visible after data changes + refresh token.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-064"`

Notes / implementation hints:
- Keep same convention used by existing pickers.

Risks:
- Low.

# Ticket KCP-065 — README troubleshooting for missing nodes

Status: DONE

Goal (1 sentence): Prevent missing-node regressions with a concise troubleshooting checklist.

Scope:

Must include:
- README section covering: pack root `__init__.py`, clearing `__pycache__`, import sanity snippet (`KCP_IMPORT_OK`), and using Comfy Python env for pip installs.

Must NOT include:
- No code changes.

Acceptance criteria:
- Troubleshooting section exists and is actionable.
- Verify run for receipt passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-065"`

Notes / implementation hints:
- Keep checklist short and copy-pasteable.

Risks:
- None.

# Ticket KCP-066 — KeyframeSetMarkPicked derives idx from item_json

Status: DONE

Goal (1 sentence): Make mark-picked one-click by allowing idx derivation from item_json when picked_index is default/blank sentinel.

Scope:

Must include:
- Add optional `item_json` input on `KCP_KeyframeSetMarkPicked`.
- When `picked_index == -1` and `item_json` is provided, derive `idx` from JSON.
- Do not override explicit non-negative `picked_index`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Workflow wiring `KCP_KeyframeSetItemPick.item_json -> KCP_KeyframeSetMarkPicked.item_json` succeeds with `picked_index=-1`.
- Verify smoke passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-066"`

Notes / implementation hints:
- Reuse existing JSON parser helper and keep failure code actionable.

Risks:
- Low.

# Ticket KCP-067 — Promote derives set/idx from item_json

Status: DONE

Goal (1 sentence): Allow promote to consume `item_json` directly to avoid manual set_id/idx re-entry.

Scope:

Must include:
- Add optional `item_json` input on `KCP_KeyframePromoteToAsset`.
- Derive `set_id` and `idx` when missing (`set_id==""` and/or `idx==-1`) from `item_json`.
- Do not override explicit `set_id`/`idx` values.

Must NOT include:
- No schema changes.

Acceptance criteria:
- `KCP_KeyframeSetItemPick.item_json -> KCP_KeyframePromoteToAsset.item_json` works with blank `set_id` and `idx=-1`.
- Verify smoke passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-067"`

Notes / implementation hints:
- Keep existing promote semantics and prompt DNA behavior unchanged.

Risks:
- Low.

# Ticket KCP-068 — SetLoadBatch returns labels_json

Status: DONE

Goal (1 sentence): Improve batch-preview clarity by returning per-item labels metadata aligned with batch ordering.

Scope:

Must include:
- Add `labels_json` output to `KCP_KeyframeSetLoadBatch`.
- Include label records with `idx`, `status`, `seed`, and optional DB `label`.
- Keep `images`, `thumbs`, and `items_json` outputs intact.

Must NOT include:
- No schema changes.

Acceptance criteria:
- `labels_json` ordering matches returned image batch ordering.
- Verify smoke passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-068"`

Notes / implementation hints:
- Keep payload minimal and deterministic for downstream UI/logging.

Risks:
- Low.

# Ticket KCP-069 — Add KeyframeSetSummary node

Status: DONE

Goal (1 sentence): Provide a single status node summarizing set size, saved media count, and picked index.

Scope:

Must include:
- Add `KCP_KeyframeSetSummary` node.
- Inputs: `db_path`, `set_id`.
- Outputs: `summary_text`, `status_json`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Verify smoke with 12 items and 3 saved media reports `12 items, 3 saved media, picked=2` and matching JSON.
- `python tools/verify.py --receipt "KCP-069"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-069"`

Notes / implementation hints:
- Return stable key names for status payload.

Risks:
- Low.

# Ticket KCP-070 — Update on-ramp workflow to least-typing winner path

Status: DONE

Goal (1 sentence): Keep example workflow aligned with least-typing pick/promote ergonomics using new item_json wiring.

Scope:

Must include:
- Update `examples/workflows/opinionated_onramp_render_persist_variant_pack.json` to include SetPick/LoadBatch/ItemPick/MarkPicked/Promote path.
- Demonstrate wiring `item_json` into MarkPicked and Promote.
- Include SetSummary as optional status/logging node in notes/wiring.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Workflow file reflects the full ergonomic loop.
- Verify run for `KCP-070` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-070"`

Notes / implementation hints:
- Keep file as concise wiring guidance JSON (not full Comfy export).

Risks:
- NONE.

# Ticket KCP-071 — KeyframeSetSave derives defaults from variant_list_json

Status: DONE

Goal (1 sentence): Reduce mismatch risk by deriving base_seed/width/height from variant payload only when users leave default values.

Scope:

Must include:
- Add safe derivation in `KCP_KeyframeSetSave.run` for `base_seed`, `width`, `height` from `variant_list_json` payload.
- Derive `base_seed` from payload-level `base_seed`.
- Derive `width`/`height` from first variant `gen_params.width`/`gen_params.height` with variant-level fallback.
- Only override when current inputs are defaults (`base_seed==0`, `width==1024`, `height==1024`) and derived values differ.

Must NOT include:
- No DB schema changes.

Acceptance criteria:
- Defaulted inputs derive from payload values when provided.
- Non-default user inputs are preserved.
- `python tools/verify.py --receipt "KCP-071"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-071"`

Notes / implementation hints:
- Missing derivation fields are tolerated; fall back to user values.

Risks:
- Low.

# Ticket KCP-072 — KeyframeSetSave policy_json fallback from variant_list_json

Status: DONE

Goal (1 sentence): Ensure policy provenance is stored even when `variant_policy_json` is left empty.

Scope:

Must include:
- In `KCP_KeyframeSetSave`, if parsed `variant_policy_json` is `{}` and policy_id is available from variant payload/input, store minimal fallback payload containing policy_id.
- Preserve non-empty user-provided policy JSON (additive compose breakdown merge retained).

Must NOT include:
- No DB schema changes.

Acceptance criteria:
- Empty policy JSON + policy_id in variant payload stores non-empty JSON containing policy_id.
- Non-empty policy JSON remains preserved.
- `python tools/verify.py --receipt "KCP-072"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-072"`

Notes / implementation hints:
- Fallback remains minimal to avoid implying full policy template persistence.

Risks:
- Low.

# Ticket KCP-073 — Add RenderPackStatus node

Status: DONE

Goal (1 sentence): Provide a read-only status node reporting expected vs saved vs missing set media.

Scope:

Must include:
- Add `KCP_RenderPackStatus` node with inputs `db_path`, `set_id`, `strict`.
- Outputs: `summary_text`, `status_json` containing `total_items`, `items_with_media`, `missing_idxs`.
- strict mode raises `kcp_set_media_missing: ...` when missing media exists.
- Register node in `kcp/__init__.py` mappings.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Synthetic verify scenario reports accurate counts and missing indexes.
- strict mode raises prefixed error when missing exists.
- `python tools/verify.py --receipt "KCP-073"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-073"`

Notes / implementation hints:
- Uses canonical `kcp_root_from_db_path` + absolute existence checks.

Risks:
- Medium-low.

# Ticket KCP-074 — KeyframeSetItemPick defaults and saved/missing labels

Status: DONE

Goal (1 sentence): Make picker default to saved-only items and show explicit saved/missing labels when expanded.

Scope:

Must include:
- Ensure `only_with_media` default remains `True`.
- Update dropdown labels to `idx=<n> [saved|missing] seed=<seed>`.
- Keep missing entries hidden by default, visible when `only_with_media=False`.
- Add verify smoke for default filtering and expanded labels.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Default picker choices include only saved entries.
- Expanded choices include both with deterministic `[saved]`/`[missing]` labels.
- `python tools/verify.py --receipt "KCP-074"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-074"`

Notes / implementation hints:
- Parse `item_choice` robustly with new `idx=<n>` label format.

Risks:
- Low.


# Ticket KCP-075 — KeyframeSetSave derive stack_id from stack_json when blank

Status: DONE

Goal (1 sentence): Prevent orphaned sets by deriving `stack_id` from `stack_json` whenever `stack_id` input is blank.

Scope:

Must include:
- In `kcp/nodes/keyframe_set_save.py`, derive `stack_id` from parsed `stack_json` when `stack_id` is blank.
- Never override non-empty user `stack_id`.
- Add verify smoke.

Must NOT include:
- No DB schema changes.

Acceptance criteria:
- Blank `stack_id` with valid `stack_json` persists expected stack id.
- Non-blank `stack_id` is preserved.
- `python tools/verify.py --receipt "KCP-075"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-075"`

Notes / implementation hints:
- Missing/empty `stack_json` is not force-failed during derivation; explicit value still takes precedence.

Risks:
- Low.

# Ticket KCP-076 — RenderPackStatus add expected_count and sort missing_idxs

Status: DONE

Goal (1 sentence): Make render-pack status deterministic and more informative for debugging.

Scope:

Must include:
- Add `expected_count` to `status_json`.
- Sort `missing_idxs` ascending before return/strict checks.
- Add verify smoke.

Must NOT include:
- No DB schema changes.

Acceptance criteria:
- `missing_idxs` ordering is stable and ascending.
- `python tools/verify.py --receipt "KCP-076"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-076"`

Notes / implementation hints:
- Determinism reduces UI jitter in downstream consumers.

Risks:
- Low.

# Ticket KCP-077 — KeyframeSetLoadBatch stable idx ordering + saved-only default

Status: DONE

Goal (1 sentence): Make batch preview predictable by enforcing sorted idx output ordering and keeping saved-only default behavior.

Scope:

Must include:
- Ensure output processing in `KCP_KeyframeSetLoadBatch` uses ascending idx order.
- Keep `only_with_media` default `True`.
- Add verify smoke asserting output order alignment.

Must NOT include:
- No schema changes.

Acceptance criteria:
- `images`/`thumbs`/`items_json`/`labels_json` align to sorted idx order.
- `python tools/verify.py --receipt "KCP-077"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-077"`

Notes / implementation hints:
- Keep change append-only and deterministic.

Risks:
- Medium-low.

# Ticket KCP-078 — KeyframeSetItemSaveBatch persists full render batch

Status: DONE

Goal (1 sentence): Ensure saving a render batch writes N sequential item media files and updates N DB rows in one node run.

Scope:

Must include:
- Confirm `KCP_KeyframeSetItemSaveBatch` handles batch size and sequential idx mapping via `idx_start`.
- Validate per-item media writes + thumb writes + DB updates.
- Keep missing-row diagnostic with `kcp_set_item_not_found` and first missing idx details.
- Add/adjust verify smoke to assert N files exist and N rows updated.

Must NOT include:
- No DB schema changes.

Acceptance criteria:
- Batch size N writes N files and updates N rows.
- `python tools/verify.py --receipt "KCP-078"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-078"`

Notes / implementation hints:
- Batch handling remains conservative for tensor/list-like IMAGE inputs.

Risks:
- Medium.

# Ticket KCP-079 — Add KeyframeSetPick (dropdown set chooser)

Status: DONE

Goal (1 sentence): Let users pick a keyframe set via DB-backed dropdown and return `set_id` + `set_json` without typing IDs.

Scope:

Must include:
- Implement/refresh `KCP_KeyframeSetPick` in `kcp/nodes/keyframe_set_pick.py`.
- Required inputs: `db_path`, `set_choice`, `refresh_token`, `strict`.
- Dropdown labels include `set_id + created_at + optional name`, ordered newest first.
- Outputs: `set_id`, `set_json`, `warning_json`.
- strict=False empty selection returns warning payload; strict=True missing/not-found raises `kcp_set_not_found`.
- Node registered in `kcp/__init__.py`.
- Verify smoke `smoke_set_pick_input_choices`.

Must NOT include:
- No DB schema changes.

Acceptance criteria:
- Dropdown populates after creating sets in temp DB.
- Node returns matching set_id and set_json containing id.
- `python tools/verify.py --receipt "KCP-079"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-079"`

Notes / implementation hints:
- Robust parsing: split choice on first `|` to recover set_id.

Risks:
- Low.

# Ticket KCP-080 — Add KeyframeSetLoadBatch (load preview grid)

Status: DONE

Goal (1 sentence): Load a set’s media in stable idx order so winner-preview workflows are deterministic.

Scope:

Must include:
- Implement/refresh `KCP_KeyframeSetLoadBatch` in `kcp/nodes/keyframe_set_load_batch.py`.
- Required inputs: `db_path`, `set_id`, `strict`.
- Optional input: `only_with_media` default `True`.
- Outputs: `images`, `thumbs`, `items_json` with `OUTPUT_IS_LIST` enabled for all outputs.
- Sorted idx ASC output alignment.
- strict=False missing media returns `None` entries + warning JSON per item (`kcp_set_media_missing`).
- strict=True missing raises `kcp_set_media_missing` with first missing idx/path context.
- Verify smoke `smoke_set_load_batch_sorted_idx_order`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Output lists are sorted and aligned by idx.
- saved-only mode length matches rows with media.
- `python tools/verify.py --receipt "KCP-080"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-080"`

Notes / implementation hints:
- Reuse existing image load helper and root resolution.

Risks:
- Medium-low.

# Ticket KCP-081 — Add KeyframeSetItemPick (winner selection without typing idx)

Status: DONE

Goal (1 sentence): Provide deterministic set-item dropdown labels and return idx/item_json for downstream mark/promote nodes.

Scope:

Must include:
- Implement/refresh `KCP_KeyframeSetItemPick` in `kcp/nodes/keyframe_set_item_pick.py`.
- Required inputs: `db_path`, `set_id`, `item_choice`, `refresh_token`, `strict`.
- Optional input: `only_with_media` default `True`.
- Label format deterministic: `idx=<n> [saved|missing] seed=<seed>`.
- strict=False empty returns warning payload; strict=True missing/not-found raises `kcp_set_item_not_found`.
- Robust idx parsing tolerant to spacing (`idx = 3` etc).
- Verify smoke `smoke_set_item_pick_input_choices`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Dropdown populates and filters by media flag.
- Label parsing returns correct idx.
- `python tools/verify.py --receipt "KCP-081"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-081"`

Notes / implementation hints:
- Regex parse path used for tolerance.

Risks:
- Low.

# Ticket KCP-082 — MarkPicked accepts item_json (no manual set_id/idx)

Status: DONE

Goal (1 sentence): Allow mark-picked via item_json derivation while preserving explicit picked_index/set_id precedence.

Scope:

Must include:
- Keep existing mark-picked inputs and add optional `item_json`.
- `picked_index=-1` sentinel derives idx/set_id from item_json if present.
- Explicit `picked_index>=0` path unchanged.
- If set_id still blank after derivation, raise `kcp_set_id_missing`.
- Verify smoke `smoke_mark_picked_derives_from_item_json`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Sentinel + valid item_json updates picked index correctly.
- Explicit picked_index behavior unchanged.
- `python tools/verify.py --receipt "KCP-082"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-082"`

Notes / implementation hints:
- item_json may include extra fields; only set_id/idx are required.

Risks:
- Low.

# Ticket KCP-083 — Promote accepts item_json (no manual set_id/idx)

Status: DONE

Goal (1 sentence): Allow promote path to derive set/item reference from item_json without breaking explicit input workflows.

Scope:

Must include:
- Add optional `item_json` on `KCP_KeyframePromoteToAsset`.
- `idx=-1` sentinel allows derivation from item_json; explicit values preserved.
- If unresolved reference remains, raise `kcp_set_item_ref_missing`.
- Preserve prompt DNA persistence behavior.
- Verify smoke `smoke_promote_derives_from_item_json`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- Promote works with db_path + item_json + name when refs omitted/sentinel.
- Existing explicit set_id/idx workflow continues working.
- `python tools/verify.py --receipt "KCP-083"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-083"`

Notes / implementation hints:
- Derivation fills blanks only; no explicit override.

Risks:
- Low.

# Ticket KCP-084 — README winner loop + example workflow JSON

Status: DONE

Goal (1 sentence): Document and exemplify the opinionated Winner Loop wiring using pick/load/item_json flows.

Scope:

Must include:
- README section with exact wiring lines:
  - `KCP_KeyframeSetPick.set_id -> KCP_KeyframeSetLoadBatch.set_id`
  - `KCP_KeyframeSetItemPick.item_json -> KCP_KeyframeSetMarkPicked.item_json`
  - `KCP_KeyframeSetItemPick.item_json -> KCP_KeyframePromoteToAsset.item_json`
- Example workflow JSON under `examples/workflows/` showing VariantPack->SetSave, Render(batch)->SaveBatch, and SetPick/LoadBatch/ItemPick->Mark/Pomote.
- Verify smoke `smoke_readme_mentions_winner_loop_wiring`.

Must NOT include:
- No schema changes.

Acceptance criteria:
- README contains the exact winner-loop strings.
- Example workflow exists and is referenced.
- `python tools/verify.py --receipt "KCP-084"` passes.

Evidence needed (what to paste/verify):
- `python tools/verify.py --receipt "KCP-084"`

Notes / implementation hints:
- Keep workflow JSON minimal as a wiring reference.

Risks:
- Low.
