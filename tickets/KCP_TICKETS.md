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
