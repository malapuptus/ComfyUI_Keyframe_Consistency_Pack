#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def write_receipt(batch: str, oracles: list[str], passed: bool) -> None:
    cache_dir = Path(".cache")
    cache_dir.mkdir(exist_ok=True)
    receipt_path = cache_dir / "verify-last.txt"
    ts = dt.datetime.now(dt.timezone.utc).isoformat()
    receipt_path.write_text(
        "\n".join(
            [
                f"BATCH={batch}",
                f"ORACLES_RUN={','.join(oracles)}",
                f"VERIFY_{'PASS' if passed else 'FAIL'}",
                f"TIMESTAMP={ts}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def smoke_asset_thumb() -> tuple[bool, str]:
    """Smoke: ensure KCP_AssetSave returns non-None thumb_image when image input exists."""
    from kcp.nodes.project_init import KCP_ProjectInit
    from kcp.nodes import asset_nodes

    original_pillow_available = asset_nodes.pillow_available
    original_save_optional_image = asset_nodes.save_optional_image
    original_make_thumbnail = asset_nodes.make_thumbnail
    original_load_image_as_comfy = asset_nodes.load_image_as_comfy

    def _fake_save_optional_image(_image, path: Path, fmt: str | None = None) -> bool:
        _ = fmt
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake")
        return True

    try:
        asset_nodes.pillow_available = lambda: True
        asset_nodes.save_optional_image = _fake_save_optional_image
        asset_nodes.make_thumbnail = lambda *_args, **_kwargs: False
        asset_nodes.load_image_as_comfy = lambda *_args, **_kwargs: [[[[1.0, 0.0, 0.0]]]]

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "kcp"
            db_path, _, _ = KCP_ProjectInit().run(str(root), "kcp.sqlite", True)
            image_input = [[[[1.0, 0.0, 0.0]]]]
            _, thumb_image, asset_json = asset_nodes.KCP_AssetSave().run(
                db_path,
                "character",
                "verify_thumb_asset",
                "",
                "positive",
                "",
                "",
                "",
                "new",
                image_input,
            )
            if thumb_image is None:
                return False, "thumb_image was None"
            payload = json.loads(asset_json)
            if not payload.get("image_path", "").endswith("original.png"):
                return False, f"unexpected image_path: {payload.get('image_path')}"
        return True, "thumb smoke ok"
    except Exception as e:
        return False, str(e)
    finally:
        asset_nodes.pillow_available = original_pillow_available
        asset_nodes.save_optional_image = original_save_optional_image
        asset_nodes.make_thumbnail = original_make_thumbnail
        asset_nodes.load_image_as_comfy = original_load_image_as_comfy


def smoke_asset_overwrite_preserves_media_without_image() -> tuple[bool, str]:
    """Smoke: overwrite_by_name with image=None preserves existing media fields."""
    from kcp.nodes.project_init import KCP_ProjectInit
    from kcp.nodes import asset_nodes

    original_pillow_available = asset_nodes.pillow_available
    original_save_optional_image = asset_nodes.save_optional_image
    original_make_thumbnail = asset_nodes.make_thumbnail
    original_load_image_as_comfy = asset_nodes.load_image_as_comfy

    def _fake_save_optional_image(_image, path: Path, fmt: str | None = None) -> bool:
        _ = fmt
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake")
        return True

    try:
        asset_nodes.pillow_available = lambda: True
        asset_nodes.save_optional_image = _fake_save_optional_image
        asset_nodes.make_thumbnail = lambda *_args, **_kwargs: False
        asset_nodes.load_image_as_comfy = lambda *_args, **_kwargs: [[[[1.0, 0.0, 0.0]]]]

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "kcp"
            db_path, _, _ = KCP_ProjectInit().run(str(root), "kcp.sqlite", True)
            image_input = [[[[1.0, 0.0, 0.0]]]]
            _, _, first_asset_json = asset_nodes.KCP_AssetSave().run(
                db_path,
                "character",
                "overwrite_preserve",
                "",
                "positive",
                "",
                "",
                "",
                "new",
                image_input,
            )
            first_payload = json.loads(first_asset_json)
            _, _, second_asset_json = asset_nodes.KCP_AssetSave().run(
                db_path,
                "character",
                "overwrite_preserve",
                "updated",
                "positive2",
                "",
                "",
                "",
                "overwrite_by_name",
                None,
            )
            second_payload = json.loads(second_asset_json)
            if second_payload.get("image_path") != first_payload.get("image_path"):
                return False, "image_path was cleared on overwrite_by_name with no image"
            if second_payload.get("thumb_path") != first_payload.get("thumb_path"):
                return False, "thumb_path was cleared on overwrite_by_name with no image"
        return True, "asset overwrite preserves media when image is omitted"
    except Exception as e:
        return False, str(e)
    finally:
        asset_nodes.pillow_available = original_pillow_available
        asset_nodes.save_optional_image = original_save_optional_image
        asset_nodes.make_thumbnail = original_make_thumbnail
        asset_nodes.load_image_as_comfy = original_load_image_as_comfy


def smoke_project_init_respects_create_if_missing() -> tuple[bool, str]:
    """Smoke: ProjectInit create_if_missing=False does not create missing layout/DB."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "missing_kcp"
            try:
                KCP_ProjectInit().run(str(root), "kcp.sqlite", False)
                return False, "expected kcp_project_missing for create_if_missing=False"
            except RuntimeError as e:
                msg = str(e)
                if "kcp_project_missing" not in msg:
                    return False, f"unexpected error: {msg}"
                if root.exists():
                    return False, "root directory was created despite create_if_missing=False"
        return True, "project init respects create_if_missing=False"
    except Exception as e:
        return False, str(e)


def smoke_pack_root_entrypoint_import() -> tuple[bool, str]:
    """Smoke: custom_nodes-style package import exposes non-empty node mappings."""
    try:
        import importlib.util
        import shutil

        with tempfile.TemporaryDirectory() as td:
            custom_nodes = Path(td) / "custom_nodes"
            pack_dir = custom_nodes / "keyframe_consistency_pack"
            shutil.copytree(REPO_ROOT, pack_dir)

            spec = importlib.util.spec_from_file_location(
                "keyframe_consistency_pack",
                pack_dir / "__init__.py",
                submodule_search_locations=[str(pack_dir)],
            )
            if spec is None or spec.loader is None:
                return False, "failed to create import spec"
            mod = importlib.util.module_from_spec(spec)
            sys.modules.pop("keyframe_consistency_pack", None)
            sys.path.insert(0, str(custom_nodes))
            try:
                spec.loader.exec_module(mod)
            finally:
                if str(custom_nodes) in sys.path:
                    sys.path.remove(str(custom_nodes))

            mappings = getattr(mod, "NODE_CLASS_MAPPINGS", {})
            if not isinstance(mappings, dict) or len(mappings) == 0:
                return False, f"unexpected node mappings: {type(mappings)} size={len(mappings) if hasattr(mappings, '__len__') else 'n/a'}"
        return True, "pack root entrypoint import ok"
    except Exception as e:
        return False, str(e)


def smoke_variant_unroll_lists() -> tuple[bool, str]:
    """Smoke: VariantUnroll returns list outputs aligned to variant payload."""
    try:
        from kcp.nodes.variant_unroll import KCP_VariantUnroll

        payload = {
            "variants": [
                {
                    "index": 3,
                    "positive": "p3",
                    "negative": "n3",
                    "gen_params": {
                        "seed": 103,
                        "steps": 23,
                        "cfg": 6.5,
                        "sampler": "euler",
                        "scheduler": "normal",
                        "denoise": 1.0,
                        "width": 768,
                        "height": 512,
                    },
                },
                {
                    "index": 4,
                    "positive": "p4",
                    "negative": "n4",
                    "gen_params": {
                        "seed": 104,
                        "steps": 24,
                        "cfg": 7.0,
                        "sampler": "heun",
                        "scheduler": "karras",
                        "denoise": 0.9,
                        "width": 1024,
                        "height": 576,
                    },
                },
            ]
        }
        if KCP_VariantUnroll.RETURN_TYPES[6] != "SAMPLER_NAME" or KCP_VariantUnroll.RETURN_TYPES[7] != "SCHEDULER":
            return False, f"unexpected sampler/scheduler types: {KCP_VariantUnroll.RETURN_TYPES[6:8]}"
        out = KCP_VariantUnroll().run(json.dumps(payload))
        if len(out) != 12:
            return False, f"unexpected output arity={len(out)}"
        idx_list, pos_list, neg_list, seed_list, steps_list, cfg_list, sampler_list, scheduler_list, denoise_list, width_list, height_list, gp_json_list = out
        if not (len(idx_list) == len(pos_list) == len(seed_list) == 2):
            return False, f"unexpected list lengths idx={len(idx_list)} pos={len(pos_list)} seed={len(seed_list)}"
        if idx_list != [3, 4] or pos_list != ["p3", "p4"] or neg_list != ["n3", "n4"]:
            return False, f"unexpected prompt/index lists: idx={idx_list} pos={pos_list} neg={neg_list}"
        if seed_list != [103, 104] or steps_list != [23, 24]:
            return False, f"unexpected seed/steps lists seed={seed_list} steps={steps_list}"
        if sampler_list != ["euler", "heun"] or scheduler_list != ["normal", "karras"]:
            return False, f"unexpected sampler/scheduler lists {sampler_list} / {scheduler_list}"
        if width_list != [768, 1024] or height_list != [512, 576]:
            return False, f"unexpected size lists {width_list} / {height_list}"
        try:
            gp0 = json.loads(gp_json_list[0])
            gp1 = json.loads(gp_json_list[1])
            if gp0.get("seed") != 103 or gp1.get("seed") != 104:
                return False, f"unexpected gen_params_json_list: {gp_json_list}"
        except Exception as e:
            return False, f"gen_params_json_list parse failed: {e}"
        return True, "variant unroll list mapping ok"
    except Exception as e:
        return False, str(e)


def smoke_keyframe_set_save_stack_json_fallback_and_provenance() -> tuple[bool, str]:
    """Smoke: KeyframeSetSave derives stack_id from stack_json and stores model/breakdown provenance."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_save import KCP_KeyframeSetSave
        from kcp.db.repo import connect

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
            finally:
                conn.close()

            variants = json.dumps({"policy_id": "seed_sweep_12_v1", "variants": []})
            stack_json = json.dumps({"stack_id": "stack1"})
            set_id, _, _ = KCP_KeyframeSetSave().run(db_path, "", stack_json, "", "{}", variants, 0, 64, 64, "", -1, "", "ckptA", '{"tokens":["x"]}')
            conn = connect(Path(db_path))
            try:
                row = conn.execute("SELECT stack_id,variant_policy_json,model_ref FROM keyframe_sets WHERE id=?", (set_id,)).fetchone()
                if not row or row[0] != "stack1":
                    return False, f"stack fallback failed row={row}"
                vp = json.loads(row[1] or "{}")
                if row[2] != "ckptA":
                    return False, f"model_ref missing row={row}"
                if vp.get("compose_breakdown", {}).get("tokens") != ["x"]:
                    return False, f"compose_breakdown missing in variant_policy_json: {vp}"
            finally:
                conn.close()
        return True, "keyframe set save stack/provenance fallback ok"
    except Exception as e:
        return False, str(e)




def smoke_keyframe_set_save_derives_dims_seed_when_defaulted() -> tuple[bool, str]:
    """Smoke: set save derives base_seed/width/height only when defaults are used."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_save import KCP_KeyframeSetSave
        from kcp.db.repo import connect

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
            finally:
                conn.close()

            variants = {
                "policy_id": "seed_sweep_12_v1",
                "base_seed": 777,
                "variants": [
                    {"index": 0, "gen_params": {"width": 832, "height": 1216, "seed": 777}, "positive": "p", "negative": "n"}
                ],
            }
            saver = KCP_KeyframeSetSave()
            set_id, _, _ = saver.run(db_path, "stack1", "{}", "", "{}", json.dumps(variants), 0, 1024, 1024, "", -1, "")
            conn = connect(Path(db_path))
            try:
                row = conn.execute("SELECT base_seed,width,height FROM keyframe_sets WHERE id=?", (set_id,)).fetchone()
                if not row or int(row["base_seed"]) != 777 or int(row["width"]) != 832 or int(row["height"]) != 1216:
                    return False, f"derived mismatch row={dict(row) if row else row}"
            finally:
                conn.close()

            set_id2, _, _ = saver.run(db_path, "stack1", "{}", "", "{}", json.dumps(variants), 12, 640, 480, "", -1, "")
            conn = connect(Path(db_path))
            try:
                row2 = conn.execute("SELECT base_seed,width,height FROM keyframe_sets WHERE id=?", (set_id2,)).fetchone()
                if not row2 or int(row2["base_seed"]) != 12 or int(row2["width"]) != 640 or int(row2["height"]) != 480:
                    return False, f"explicit override mismatch row={dict(row2) if row2 else row2}"
            finally:
                conn.close()

        return True, "set save derives dims/seed when defaulted ok"
    except Exception as e:
        return False, str(e)


def smoke_keyframe_set_save_policy_json_fallback() -> tuple[bool, str]:
    """Smoke: policy_json falls back to policy_id when empty and preserves non-empty input."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_save import KCP_KeyframeSetSave
        from kcp.db.repo import connect

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
            finally:
                conn.close()

            variants = json.dumps({"policy_id": "seed_sweep_12_v1", "variants": []})
            saver = KCP_KeyframeSetSave()
            set_id, _, _ = saver.run(db_path, "stack1", "{}", "", "{}", variants, 0, 1024, 1024, "", -1, "")
            conn = connect(Path(db_path))
            try:
                row = conn.execute("SELECT variant_policy_json FROM keyframe_sets WHERE id=?", (set_id,)).fetchone()
                payload = json.loads(row["variant_policy_json"]) if row else {}
                if payload.get("policy_id") != "seed_sweep_12_v1":
                    return False, f"fallback policy_id missing payload={payload}"
            finally:
                conn.close()

            custom = {"custom": True, "policy_id": "manual"}
            set_id2, _, _ = saver.run(db_path, "stack1", "{}", "", json.dumps(custom), variants, 0, 1024, 1024, "", -1, "")
            conn = connect(Path(db_path))
            try:
                row2 = conn.execute("SELECT variant_policy_json FROM keyframe_sets WHERE id=?", (set_id2,)).fetchone()
                payload2 = json.loads(row2["variant_policy_json"]) if row2 else {}
                if payload2.get("custom") is not True:
                    return False, f"custom policy payload not preserved payload={payload2}"
            finally:
                conn.close()

        return True, "set save policy_json fallback ok"
    except Exception as e:
        return False, str(e)


def smoke_render_pack_status_counts_missing() -> tuple[bool, str]:
    """Smoke: render pack status counts saved/missing and strict mode errors."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.render_pack_status import KCP_RenderPackStatus
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            root = Path(db_path).parent.parent
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
                set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                for i in range(3):
                    add_keyframe_set_item(conn, {"set_id": set_id, "idx": i, "seed": i + 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                good_rel = f"sets/{set_id}/0.webp"
                (root / good_rel).parent.mkdir(parents=True, exist_ok=True)
                (root / good_rel).write_bytes(b"img")
                update_set_item_media(conn, set_id, 0, good_rel, "")
                conn.execute("UPDATE keyframe_set_items SET image_path=? WHERE set_id=? AND idx=?", (f"sets/{set_id}/2.webp", set_id, 2))
                conn.commit()
            finally:
                conn.close()

            node = KCP_RenderPackStatus()
            summary_text, status_json = node.run(db_path, set_id, False)
            status = json.loads(status_json)
            if status.get("expected_count") != 3 or status.get("total_items") != 3 or status.get("items_with_media") != 1 or status.get("missing_idxs") != [1, 2]:
                return False, f"status mismatch status={status}"
            if "saved=1" not in summary_text:
                return False, f"summary mismatch summary={summary_text}"
            try:
                node.run(db_path, set_id, True)
                return False, "expected strict missing error"
            except RuntimeError as e:
                if not str(e).startswith("kcp_set_media_missing:"):
                    return False, f"unexpected strict error: {e}"

        return True, "render pack status missing counts ok"
    except Exception as e:
        return False, str(e)


def smoke_set_item_pick_defaults_saved_only() -> tuple[bool, str]:
    """Smoke: item pick defaults to saved-only and labels show saved/missing with seed."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_item_pick import KCP_KeyframeSetItemPick
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            root = Path(db_path).parent.parent
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
                set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                add_keyframe_set_item(conn, {"set_id": set_id, "idx": 0, "seed": 111, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                add_keyframe_set_item(conn, {"set_id": set_id, "idx": 1, "seed": 222, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                rel = f"sets/{set_id}/0.webp"
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes(b"img")
                update_set_item_media(conn, set_id, 0, rel, "")
            finally:
                conn.close()

            default_inputs = KCP_KeyframeSetItemPick.INPUT_TYPES(db_path=db_path, set_id=set_id)
            if default_inputs["optional"]["only_with_media"][1].get("default") is not True:
                return False, f"only_with_media default changed: {default_inputs['optional']['only_with_media']}"
            default_choices = default_inputs["required"]["item_choice"][0]
            if default_choices != ["idx=0 [saved] seed=111"]:
                return False, f"unexpected default choices: {default_choices}"

            all_inputs = KCP_KeyframeSetItemPick.INPUT_TYPES(db_path=db_path, set_id=set_id, only_with_media=False, refresh_token=1)
            all_choices = all_inputs["required"]["item_choice"][0]
            if len(all_choices) != 2 or "[saved]" not in all_choices[0] or "[missing]" not in all_choices[1]:
                return False, f"unexpected all choices: {all_choices}"

        return True, "set item pick defaults saved-only ok"
    except Exception as e:
        return False, str(e)
def smoke_variant_pick() -> tuple[bool, str]:
    """Smoke: build a variant list and ensure VariantPick returns scalar outputs."""
    try:
        from kcp.policies.engine import build_variants
        from kcp.nodes.variant_pick import KCP_VariantPick

        payload = build_variants(
            positive_prompt="cinematic portrait",
            negative_prompt="low quality",
            policy_id="seed_sweep_12_v1",
            count=1,
            base_seed=123,
            width=1024,
            height=576,
            steps=20,
            cfg=6.0,
            sampler="euler",
            scheduler="normal",
            denoise=1.0,
            policy_overrides={},
        )
        out = KCP_VariantPick().run(json.dumps(payload), 0)
        label, pos, neg, seed, steps, cfg, sampler, scheduler, denoise, width, height, gp_json = out
        if not isinstance(label, str) or not label:
            return False, "empty label"
        if not isinstance(pos, str) or not pos:
            return False, "empty positive"
        if not isinstance(neg, str):
            return False, "negative type invalid"
        checks = [
            isinstance(seed, int),
            isinstance(steps, int),
            isinstance(cfg, float),
            isinstance(sampler, str),
            isinstance(scheduler, str),
            isinstance(denoise, float),
            isinstance(width, int),
            isinstance(height, int),
            isinstance(gp_json, str),
        ]
        if not all(checks):
            return False, "scalar output types invalid"
        return True, "variant pick smoke ok"
    except Exception as e:
        return False, str(e)


def smoke_mark_picked() -> tuple[bool, str]:
    """Smoke: create set, mark picked index, then verify DB state."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, set_picked_index

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "kcp"
            db_path, _, _ = KCP_ProjectInit().run(str(root), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                conn.execute(
                    "INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)",
                    ("stack_verify", "stack_verify", 1, 1),
                )
                conn.commit()
                set_id = create_keyframe_set(
                    conn,
                    {
                        "stack_id": "stack_verify",
                        "variant_policy_id": "seed_sweep_12_v1",
                        "variant_policy_json": {},
                        "base_seed": 1,
                        "width": 512,
                        "height": 512,
                    },
                )
                row = set_picked_index(conn, set_id, 2, "winner")
                if row is None:
                    return False, "row not found after update"
                if int(row["picked_index"]) != 2:
                    return False, f"picked_index mismatch: {row['picked_index']}"
                if row["notes"] != "winner":
                    return False, f"notes mismatch: {row['notes']}"
                return True, "mark picked smoke ok"
            finally:
                conn.close()
    except Exception as e:
        return False, str(e)


def smoke_root_resolution() -> tuple[bool, str]:
    """Smoke: resolve_root uses folder_paths output dir for relative roots when available."""
    try:
        import kcp.db.paths as db_paths

        original_module = sys.modules.get("folder_paths")
        with tempfile.TemporaryDirectory() as td:
            fake_out = Path(td).resolve()
            fake = types.ModuleType("folder_paths")
            fake.get_output_directory = lambda: str(fake_out)
            sys.modules["folder_paths"] = fake

            resolved = db_paths.resolve_root("output/kcp")
            expected = (fake_out / "kcp").resolve()
            if resolved != expected:
                return False, f"relative mismatch expected={expected} actual={resolved}"

            absolute = (fake_out / "absolute_target").resolve()
            resolved_abs = db_paths.resolve_root(str(absolute))
            if resolved_abs != absolute:
                return False, f"absolute mismatch expected={absolute} actual={resolved_abs}"

        return True, f"root resolution ok expected={expected} actual={resolved}"
    except Exception as e:
        return False, str(e)
    finally:
        # restore folder_paths module if any
        if "original_module" in locals():
            if original_module is None:
                sys.modules.pop("folder_paths", None)
            else:
                sys.modules["folder_paths"] = original_module


def smoke_output_nodes() -> tuple[bool, str]:
    """Smoke: side-effect nodes are marked OUTPUT_NODE=True."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.asset_nodes import KCP_AssetSave
        from kcp.nodes.stack_nodes import KCP_StackSave
        from kcp.nodes.keyframe_set_save import KCP_KeyframeSetSave
        from kcp.nodes.keyframe_set_mark_picked import KCP_KeyframeSetMarkPicked

        classes = [KCP_ProjectInit, KCP_AssetSave, KCP_StackSave, KCP_KeyframeSetSave, KCP_KeyframeSetMarkPicked]
        bad = [c.__name__ for c in classes if not getattr(c, "OUTPUT_NODE", False)]
        if bad:
            return False, f"missing OUTPUT_NODE: {', '.join(bad)}"
        return True, "output nodes flag ok"
    except Exception as e:
        return False, str(e)


def smoke_picker_empty_ok() -> tuple[bool, str]:
    """Smoke: pickers return safely on empty selection when strict=False."""
    try:
        from kcp.nodes.asset_nodes import KCP_AssetPick
        from kcp.nodes.stack_nodes import KCP_StackPick

        aout = KCP_AssetPick().run("output/kcp/db/kcp.sqlite", "character", "", False, 0, False)
        sout = KCP_StackPick().run("output/kcp/db/kcp.sqlite", "", False, 0, False)
        if len(aout) != 7:
            return False, f"asset pick output len {len(aout)}"
        if len(sout) != 11:
            return False, f"stack pick output len {len(sout)}"
        aw = json.loads(aout[-1]) if isinstance(aout[-1], str) and aout[-1] else {}
        sw = json.loads(sout[-1]) if isinstance(sout[-1], str) and sout[-1] else {}
        if aw.get("code") != "kcp_asset_no_selection":
            return False, f"asset no-selection warning invalid: {aw}"
        if sw.get("code") != "kcp_stack_no_selection":
            return False, f"stack no-selection warning invalid: {sw}"
        return True, "picker empty non-strict ok"
    except Exception as e:
        return False, str(e)


def smoke_asset_pick_returns_media_tensors() -> tuple[bool, str]:
    """Smoke: AssetPick returns non-None image/thumb tensors when media exists."""
    try:
        import kcp.nodes.asset_nodes as mod
        from kcp.nodes.project_init import KCP_ProjectInit

        orig_load = mod.load_image_as_comfy
        orig_pillow = mod.pillow_available
        try:
            mod.pillow_available = lambda: True
            mod.load_image_as_comfy = lambda *_a, **_k: [[[[1.0, 0.0, 0.0]]]]
            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                root = Path(db_path).parent.parent
                conn = mod.connect(mod.normalize_db_path(db_path))
                try:
                    aid = mod.create_asset(conn, {
                        "type": "character",
                        "name": "has_media",
                        "description": "",
                        "tags": [],
                        "positive_fragment": "p",
                        "negative_fragment": "n",
                        "json_fields": {},
                        "version": 1,
                        "parent_id": None,
                    })
                    img_rel = f"images/character/{aid}/original.png"
                    th_rel = f"thumbs/character/{aid}/thumb.webp"
                    (root / img_rel).parent.mkdir(parents=True, exist_ok=True)
                    (root / img_rel).write_bytes(b"img")
                    (root / th_rel).parent.mkdir(parents=True, exist_ok=True)
                    (root / th_rel).write_bytes(b"th")
                    conn.execute("UPDATE assets SET image_path=?, thumb_path=? WHERE id=?", (img_rel, th_rel, aid))
                    conn.commit()
                finally:
                    conn.close()
                _id, _p, _n, _jf, thumb, image, warn = mod.KCP_AssetPick().run(db_path, "character", "has_media", False, 0, False)
                if warn != "{}" or thumb is None or image is None:
                    return False, f"unexpected outputs warn={warn} thumb={thumb is not None} image={image is not None}"
        finally:
            mod.load_image_as_comfy = orig_load
            mod.pillow_available = orig_pillow
        return True, "asset pick returns media tensors ok"
    except Exception as e:
        return False, str(e)


def smoke_asset_pick_missing_media_strictness() -> tuple[bool, str]:
    """Smoke: AssetPick warns when strict=False and errors when strict=True for missing media files."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.asset_nodes import KCP_AssetPick
        from kcp.db.repo import connect, create_asset

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                create_asset(
                    conn,
                    {
                        "type": "character",
                        "name": "missing_media_char",
                        "description": "",
                        "tags": [],
                        "positive_fragment": "p",
                        "negative_fragment": "n",
                        "json_fields": {},
                        "image_path": "images/character/not_there/original.png",
                        "thumb_path": "thumbs/character/not_there/thumb.webp",
                    },
                )
            finally:
                conn.close()

            picker = KCP_AssetPick()
            out = picker.run(db_path, "character", "missing_media_char", False, 0, False)
            warning = json.loads(out[-1]) if isinstance(out[-1], str) and out[-1] else {}
            if warning.get("code") != "kcp_asset_media_missing":
                return False, f"unexpected warning code: {warning}"
            if out[4] is not None or out[5] is not None:
                return False, "expected empty media outputs for non-strict missing media"

            try:
                picker.run(db_path, "character", "missing_media_char", False, 0, True)
                return False, "strict=True did not raise on missing media"
            except RuntimeError as e:
                if "kcp_asset_image_missing" not in str(e):
                    return False, f"unexpected strict error: {e}"

        return True, "asset pick missing media strictness ok"
    except Exception as e:
        return False, str(e)


def smoke_picker_not_found_codes() -> tuple[bool, str]:
    """Smoke: pickers use code-based warning_json for non-strict not-found cases."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.asset_nodes import KCP_AssetPick
        from kcp.nodes.stack_nodes import KCP_StackPick

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            aout = KCP_AssetPick().run(db_path, "character", "missing_asset", False, 0, False)
            sout = KCP_StackPick().run(db_path, "missing_stack", False, 0, False)
            aw = json.loads(aout[-1]) if isinstance(aout[-1], str) and aout[-1] else {}
            sw = json.loads(sout[-1]) if isinstance(sout[-1], str) and sout[-1] else {}
            if aw.get("code") != "kcp_asset_not_found":
                return False, f"asset not-found code invalid: {aw}"
            if sw.get("code") != "kcp_stack_not_found":
                return False, f"stack not-found code invalid: {sw}"
        return True, "picker not-found code warnings ok"
    except Exception as e:
        return False, str(e)


def smoke_default_db_path_hint() -> tuple[bool, str]:
    """Smoke: default db_path failures include ProjectInit wiring tip."""
    try:
        from kcp.nodes.asset_nodes import KCP_AssetPick

        try:
            KCP_AssetPick().run("output/kcp/db/kcp.sqlite", "character", "any", False, 0, True)
            return False, "expected db-open failure did not occur"
        except RuntimeError as e:
            msg = str(e)
            if "Tip: wire KCP_ProjectInit.db_path into this node" not in msg:
                return False, f"missing wiring tip in error: {msg}"
        return True, "default db_path wiring tip ok"
    except Exception as e:
        return False, str(e)


def smoke_stack_pick_missing_refs_strictness() -> tuple[bool, str]:
    """Smoke: StackPick warns for missing refs when strict=False and raises when strict=True."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.stack_nodes import KCP_StackPick
        from kcp.db.repo import connect, save_stack

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                # Create a deliberately broken reference row for strictness behavior checks.
                conn.execute("PRAGMA foreign_keys = OFF")
                save_stack(
                    conn,
                    {
                        "name": "stack_missing_refs",
                        "character_id": "asset_missing_character",
                    },
                )
                conn.execute("PRAGMA foreign_keys = ON")
            finally:
                conn.close()

            picker = KCP_StackPick()
            out = picker.run(db_path, "stack_missing_refs", False, 0, False)
            warning = json.loads(out[-1]) if isinstance(out[-1], str) and out[-1] else {}
            if warning.get("code") != "kcp_stack_ref_missing":
                return False, f"unexpected warning code: {warning}"
            missing = warning.get("missing_refs", [])
            if not missing or missing[0].get("slot") != "character_id":
                return False, f"missing ref payload invalid: {warning}"

            try:
                picker.run(db_path, "stack_missing_refs", False, 0, True)
                return False, "strict=True did not raise for missing stack refs"
            except RuntimeError as e:
                if "kcp_stack_ref_missing" not in str(e):
                    return False, f"unexpected strict error: {e}"

        return True, "stack pick missing refs strictness ok"
    except Exception as e:
        return False, str(e)



def smoke_set_item_media_update() -> tuple[bool, str]:
    """Smoke: update_set_item_media persists DB paths for existing set item."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "kcp"
            db_path, _, _ = KCP_ProjectInit().run(str(root), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack_m", "stack_m", 1, 1))
                conn.commit()
                set_id = create_keyframe_set(conn, {
                    "stack_id": "stack_m",
                    "variant_policy_id": "seed_sweep_12_v1",
                    "variant_policy_json": {},
                    "base_seed": 1,
                    "width": 512,
                    "height": 512,
                })
                add_keyframe_set_item(conn, {
                    "set_id": set_id,
                    "idx": 0,
                    "seed": 1,
                    "positive_prompt": "p",
                    "negative_prompt": "n",
                    "gen_params_json": {"seed": 1},
                })
                row = update_set_item_media(conn, set_id, 0, f"sets/{set_id}/0.webp", f"sets/{set_id}/0_thumb.webp")
                if row is None:
                    return False, "row missing"
                if row["image_path"] != f"sets/{set_id}/0.webp":
                    return False, f"image_path mismatch {row['image_path']}"
                if row["thumb_path"] != f"sets/{set_id}/0_thumb.webp":
                    return False, f"thumb_path mismatch {row['thumb_path']}"
                return True, "set item media update ok"
            finally:
                conn.close()
    except Exception as e:
        return False, str(e)


def smoke_set_item_load() -> tuple[bool, str]:
    """Smoke: keyframe set item load returns non-None tensors when media exists."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media
        from kcp.nodes import keyframe_set_item_load as mod

        orig_loader = mod.load_image_as_comfy
        mod.load_image_as_comfy = lambda _p: [[[[1.0, 0.0, 0.0]]]]
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td) / "kcp"
                db_path, _, _ = KCP_ProjectInit().run(str(root), "kcp.sqlite", True)
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack_l", "stack_l", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {
                        "stack_id": "stack_l",
                        "variant_policy_id": "seed_sweep_12_v1",
                        "variant_policy_json": {},
                        "base_seed": 1,
                        "width": 512,
                        "height": 512,
                    })
                    add_keyframe_set_item(conn, {
                        "set_id": set_id,
                        "idx": 0,
                        "seed": 1,
                        "positive_prompt": "p",
                        "negative_prompt": "n",
                        "gen_params_json": {"seed": 1},
                    })
                    img_rel = f"sets/{set_id}/0.webp"
                    thumb_rel = f"sets/{set_id}/0_thumb.webp"
                    img_path = Path(db_path).parent.parent / img_rel
                    thumb_path = Path(db_path).parent.parent / thumb_rel
                    img_path.parent.mkdir(parents=True, exist_ok=True)
                    img_path.write_bytes(b"img")
                    thumb_path.write_bytes(b"thumb")
                    update_set_item_media(conn, set_id, 0, img_rel, thumb_rel)
                finally:
                    conn.close()

                image, thumb, item_json = mod.KCP_KeyframeSetItemLoad().run(db_path, set_id, 0, True)
                if image is None or thumb is None:
                    return False, "image/thumb was None"
                if "positive_prompt" not in item_json:
                    return False, "item_json missing prompt"
                return True, "set item load ok"
        finally:
            mod.load_image_as_comfy = orig_loader
    except Exception as e:
        return False, str(e)


def smoke_promote_keyframe() -> tuple[bool, str]:
    """Smoke: promote set item to keyframe asset with media/provenance."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media, get_asset_by_type_name
        from kcp.nodes import keyframe_promote as mod

        orig_pillow = mod.pillow_available
        orig_load = mod.load_image_as_comfy
        orig_save = mod.save_optional_image
        orig_thumb = mod.make_thumbnail

        mod.pillow_available = lambda: True
        mod.load_image_as_comfy = lambda _p: [[[[1.0, 0.0, 0.0]]]]
        def _fake_save(_img, path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"img")
            return True
        mod.save_optional_image = _fake_save
        mod.make_thumbnail = lambda _s, t, max_px=384: (t.parent.mkdir(parents=True, exist_ok=True) or t.write_bytes(b"thumb") or True)

        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td) / "kcp"
                db_path, _, _ = KCP_ProjectInit().run(str(root), "kcp.sqlite", True)
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack_p", "stack_p", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {
                        "stack_id": "stack_p",
                        "variant_policy_id": "seed_sweep_12_v1",
                        "variant_policy_json": {},
                        "base_seed": 1,
                        "width": 512,
                        "height": 512,
                    })
                    add_keyframe_set_item(conn, {
                        "set_id": set_id,
                        "idx": 0,
                        "seed": 1,
                        "positive_prompt": "p",
                        "negative_prompt": "n",
                        "gen_params_json": json.dumps({"seed": 1}),
                    })
                    src_rel = f"sets/{set_id}/0.webp"
                    src_path = Path(db_path).parent.parent / src_rel
                    src_path.parent.mkdir(parents=True, exist_ok=True)
                    src_path.write_bytes(b"source")
                    update_set_item_media(conn, set_id, 0, src_rel, src_rel)
                finally:
                    conn.close()

                asset_id, out_json = mod.KCP_KeyframePromoteToAsset().run(db_path, set_id, 0, "winner_asset", "", "", "new")
                conn = connect(Path(db_path))
                try:
                    arow = get_asset_by_type_name(conn, "keyframe", "winner_asset", include_archived=True)
                    if not arow:
                        return False, "asset row missing"
                    if arow["id"] != asset_id:
                        return False, "asset_id mismatch"
                    payload = json.loads(out_json)
                    if "source" not in payload.get("json_fields", {}):
                        return False, "provenance missing"
                    img_path = Path(db_path).parent.parent / payload["image_path"]
                    if not img_path.exists():
                        return False, "promoted image missing"
                    return True, "promote keyframe ok"
                finally:
                    conn.close()
        finally:
            mod.pillow_available = orig_pillow
            mod.load_image_as_comfy = orig_load
            mod.save_optional_image = orig_save
            mod.make_thumbnail = orig_thumb
    except Exception as e:
        return False, str(e)


def smoke_asset_save_modes() -> tuple[bool, str]:
    """Smoke: AssetSave honors new/overwrite_by_name/new_version_of_name."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.asset_nodes import KCP_AssetSave
        from kcp.db.repo import connect

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "kcp"
            db_path, _, _ = KCP_ProjectInit().run(str(root), "kcp.sqlite", True)
            saver = KCP_AssetSave()

            aid1, _, _ = saver.run(db_path, "character", "hero", "d1", "p1", "n1", "", "tag1", "new", None)
            conn = connect(Path(db_path))
            try:
                row1 = conn.execute("SELECT id, updated_at FROM assets WHERE type='character' AND name='hero'").fetchone()
            finally:
                conn.close()
            if not row1 or row1[0] != aid1:
                return False, "initial save failed"

            aid2, _, _ = saver.run(db_path, "character", "hero", "d2", "p2", "n2", "", "tag2", "overwrite_by_name", None)
            if aid2 != aid1:
                return False, "overwrite_by_name changed asset_id"

            conn = connect(Path(db_path))
            try:
                count1 = conn.execute("SELECT COUNT(*) FROM assets WHERE type='character' AND name LIKE 'hero%'").fetchone()[0]
                row2 = conn.execute("SELECT updated_at, positive_fragment FROM assets WHERE id=?", (aid1,)).fetchone()
            finally:
                conn.close()
            if count1 != 1:
                return False, f"overwrite_by_name count mismatch: {count1}"
            if row2[1] != "p2":
                return False, "overwrite_by_name failed to update content"

            aid3, _, out_json = saver.run(db_path, "character", "hero", "d3", "p3", "n3", "", "tag3", "new_version_of_name", None)
            payload = json.loads(out_json)
            if "__v2" not in payload.get("name", ""):
                return False, f"versioned name missing __v2: {payload.get('name')}"

            conn = connect(Path(db_path))
            try:
                count2 = conn.execute("SELECT COUNT(*) FROM assets WHERE type='character' AND (name='hero' OR name LIKE 'hero__v%')").fetchone()[0]
                new_row = conn.execute("SELECT parent_id, version, name FROM assets WHERE id=?", (aid3,)).fetchone()
            finally:
                conn.close()
            if count2 != 2:
                return False, f"new_version_of_name count mismatch: {count2}"
            if not new_row or new_row[0] != aid1 or int(new_row[1]) != 2:
                return False, "parent/version linkage invalid"

        return True, "asset save modes ok"
    except Exception as e:
        return False, str(e)


def smoke_image_format_headers() -> tuple[bool, str]:
    """Smoke: encoded file bytes match PNG/WEBP headers."""
    try:
        from kcp.util import image_io

        orig_pillow = image_io.pillow_available
        orig_conv = image_io.comfy_image_to_pil

        class _FakeImage:
            def save(self, path, format=None):
                p = Path(path)
                if (format or "").upper() == "PNG":
                    p.write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
                elif (format or "").upper() == "WEBP":
                    p.write_bytes(b"RIFFxxxxWEBPVP8 ")
                else:
                    p.write_bytes(b"BAD")

        image_io.pillow_available = lambda: True
        image_io.comfy_image_to_pil = lambda _img: _FakeImage()
        try:
            with tempfile.TemporaryDirectory() as td:
                base = Path(td)
                png_path = base / "a.png"
                webp_path = base / "b.webp"
                image_io.save_comfy_image_atomic([[[[1, 0, 0]]]], png_path, fmt="PNG")
                image_io.save_comfy_image_atomic([[[[1, 0, 0]]]], webp_path, fmt="WEBP")
                pb = png_path.read_bytes()
                wb = webp_path.read_bytes()
                if not pb.startswith(b"\x89PNG"):
                    return False, "png header mismatch"
                if not (wb.startswith(b"RIFF") and b"WEBP" in wb[:16]):
                    return False, "webp header mismatch"
            return True, "image format headers ok"
        finally:
            image_io.pillow_available = orig_pillow
            image_io.comfy_image_to_pil = orig_conv
    except Exception as e:
        return False, str(e)


def smoke_db_path_guardrails() -> tuple[bool, str]:
    """Smoke: db_path validator reports actionable directory/missing-parent errors."""
    try:
        from kcp.db.paths import normalize_db_path

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            d = base / "output" / "kcp"
            d.mkdir(parents=True, exist_ok=True)
            try:
                normalize_db_path(str(d))
                return False, "directory path did not fail"
            except RuntimeError as e:
                if "kcp_db_path_is_directory" not in str(e):
                    return False, f"unexpected directory error: {e}"

            missing_parent = base / "missing" / "db" / "kcp.sqlite"
            try:
                normalize_db_path(str(missing_parent))
                return False, "missing-parent path did not fail"
            except RuntimeError as e:
                if "kcp_db_path_parent_missing" not in str(e):
                    return False, f"unexpected parent error: {e}"
        return True, "db_path guardrails ok"
    except Exception as e:
        return False, str(e)


def smoke_db_path_trim_quotes() -> tuple[bool, str]:
    """Smoke: normalize_db_path trims whitespace and surrounding quotes."""
    try:
        from kcp.db.paths import normalize_db_path
        from kcp.nodes.project_init import KCP_ProjectInit

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            clean = normalize_db_path(db_path)
            spaced = normalize_db_path(f"  {db_path}   ")
            quoted = normalize_db_path(f'"{db_path}"')
            single_quoted = normalize_db_path(f"'{db_path}'")
            if not (clean == spaced == quoted == single_quoted):
                return False, f"normalize mismatch clean={clean} spaced={spaced} quoted={quoted} single={single_quoted}"
        return True, "db_path trim/quote normalization ok"
    except Exception as e:
        return False, str(e)


def smoke_connect_migrates() -> tuple[bool, str]:
    """Smoke: connect() auto-runs migrations on empty sqlite file."""
    try:
        from kcp.db.repo import connect

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "db" / "auto.sqlite"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = connect(db_path)
            try:
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='keyframe_set_items'"
                ).fetchone()
                if not row:
                    return False, "keyframe_set_items table missing"
            finally:
                conn.close()
        return True, "connect auto-migrate table exists"
    except Exception as e:
        return False, str(e)


def smoke_set_item_save_error_details() -> tuple[bool, str]:
    """Smoke: save-image failures include image_path and underlying err details."""
    try:
        import kcp.nodes.keyframe_set_item_save_image as mod
        from kcp.nodes.project_init import KCP_ProjectInit
        in_types = mod.KCP_KeyframeSetItemSaveImage.INPUT_TYPES()
        if "batch_index" not in in_types.get("required", {}):
            return False, f"batch_index not in required inputs: {in_types}"
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item

        orig_pillow = mod.pillow_available
        orig_save = mod.save_comfy_image_atomic
        try:
            mod.pillow_available = lambda: True

            def _boom(*_args, **_kwargs):
                raise ValueError("forced-write-failure")

            mod.save_comfy_image_atomic = _boom
            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                    add_keyframe_set_item(conn, {"set_id": set_id, "idx": 0, "seed": 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                finally:
                    conn.close()

                try:
                    mod.KCP_KeyframeSetItemSaveImage().run(db_path, set_id, 0, [[[[1, 0, 0]]]], "webp", True)
                    return False, "expected failure did not occur"
                except RuntimeError as e:
                    msg = str(e)
                    if "image_path=" not in msg or "err=" not in msg or "root=" not in msg:
                        return False, f"missing diagnostics in error: {msg}"
        finally:
            mod.pillow_available = orig_pillow
            mod.save_comfy_image_atomic = orig_save
        return True, "save-image diagnostics ok"
    except Exception as e:
        return False, str(e)


def smoke_set_item_not_found_diagnostic() -> tuple[bool, str]:
    """Smoke: set-item-not-found includes set_id/idx/db_path/root diagnostic fields."""
    try:
        import kcp.nodes.keyframe_set_item_save_image as mod
        from kcp.nodes.project_init import KCP_ProjectInit

        orig_pillow = mod.pillow_available
        try:
            mod.pillow_available = lambda: True
            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                try:
                    mod.KCP_KeyframeSetItemSaveImage().run(db_path, "missing_set", 7, [[[[1, 0, 0]]]], "webp", True)
                    return False, "expected set-item-not-found error"
                except RuntimeError as e:
                    msg = str(e)
                    if "kcp_set_item_not_found:" not in msg:
                        return False, f"missing error code: {msg}"
                    if "set_id=missing_set" not in msg or "idx=7" not in msg:
                        return False, f"missing set_id/idx diagnostics: {msg}"
                    if "db_path=" not in msg or "root=" not in msg:
                        return False, f"missing db/root diagnostics: {msg}"
        finally:
            mod.pillow_available = orig_pillow
        return True, "set-item-not-found diagnostics ok"
    except Exception as e:
        return False, str(e)


def smoke_set_item_save_batch_node() -> tuple[bool, str]:
    """Smoke: SaveBatch persists all batch images into consecutive set item rows."""
    try:
        import kcp.nodes.keyframe_set_item_save_batch as mod
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item

        orig_pillow = mod.pillow_available
        orig_save = mod.save_comfy_image_atomic
        orig_thumb = mod.make_thumbnail
        try:
            mod.pillow_available = lambda: True
            saved = []

            def _fake_save(image_obj, path, fmt=None):
                _ = fmt
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fake")
                data = image_obj
                if hasattr(data, "detach"):
                    data = data.detach()
                if hasattr(data, "cpu"):
                    data = data.cpu()
                if hasattr(data, "numpy"):
                    data = data.numpy()
                try:
                    v = float(data[0, 0, 0, 0])
                except Exception:
                    v = 0.0
                saved.append((path, v))
                return True

            def _fake_thumb(source, target, max_px=384):
                _ = source, max_px
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"thumb")
                return True

            mod.save_comfy_image_atomic = _fake_save
            mod.make_thumbnail = _fake_thumb

            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                    for i in range(3):
                        add_keyframe_set_item(conn, {"set_id": set_id, "idx": i, "seed": i + 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                finally:
                    conn.close()

                try:
                    import numpy as np  # type: ignore
                    batch = np.zeros((3, 2, 2, 3), dtype=np.float32)
                    batch[0] += 0.1
                    batch[1] += 0.5
                    batch[2] += 0.9
                except Exception:
                    class _FakeBatch:
                        def __init__(self):
                            self.shape = (3, 1, 1, 3)
                            self._vals = [0.1, 0.5, 0.9]

                        def __getitem__(self, s):
                            start = int(s.start or 0)
                            return [[[[self._vals[start], self._vals[start], self._vals[start]]]]]

                    batch = _FakeBatch()
                sid, count, payload_json = mod.KCP_KeyframeSetItemSaveBatch().run(db_path, set_id, 0, batch, "webp", True)
                if sid != set_id or count != 3:
                    return False, f"unexpected output sid={sid} count={count}"
                payload = json.loads(payload_json)
                if payload.get("saved_count") != 3:
                    return False, f"unexpected payload: {payload}"

                conn = connect(Path(db_path))
                try:
                    rows = conn.execute("SELECT idx,image_path,thumb_path FROM keyframe_set_items WHERE set_id=? ORDER BY idx", (set_id,)).fetchall()
                    if len(rows) != 3:
                        return False, f"expected 3 rows got {len(rows)}"
                    for idx, image_path, thumb_path in rows:
                        if not image_path or not thumb_path:
                            return False, f"row not updated idx={idx} row={(image_path, thumb_path)}"
                        root = Path(db_path).parent.parent
                        if not (root / image_path).exists() or not (root / thumb_path).exists():
                            return False, f"missing files for idx={idx}"
                finally:
                    conn.close()

                conn = connect(Path(db_path))
                try:
                    conn.execute("DELETE FROM keyframe_set_items WHERE set_id=? AND idx=?", (set_id, 2))
                    conn.commit()
                finally:
                    conn.close()
                try:
                    mod.KCP_KeyframeSetItemSaveBatch().run(db_path, set_id, 0, batch, "webp", True)
                    return False, "expected missing idx failure"
                except RuntimeError as e:
                    if "first_missing_idx=2" not in str(e):
                        return False, f"unexpected missing idx error: {e}"

        finally:
            mod.pillow_available = orig_pillow
            mod.save_comfy_image_atomic = orig_save
            mod.make_thumbnail = orig_thumb

        return True, "set-item save batch node ok"
    except Exception as e:
        return False, str(e)


def smoke_set_item_save_batch_index() -> tuple[bool, str]:
    """Smoke: SaveImage selects requested batch index before saving."""
    try:
        import kcp.nodes.keyframe_set_item_save_image as mod
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item

        orig_pillow = mod.pillow_available
        orig_save = mod.save_comfy_image_atomic
        orig_thumb = mod.make_thumbnail
        try:
            mod.pillow_available = lambda: True
            saved_first_vals = []

            def _first_scalar(x):
                cur = x
                while isinstance(cur, (list, tuple)) and cur:
                    cur = cur[0]
                return float(cur)

            def _fake_save(image_obj, path, fmt=None):
                _ = path, fmt
                data = image_obj
                if hasattr(data, "detach"):
                    data = data.detach()
                if hasattr(data, "cpu"):
                    data = data.cpu()
                if hasattr(data, "numpy"):
                    data = data.numpy()
                try:
                    saved_first_vals.append(float(data[0, 0, 0, 0]))
                except Exception:
                    saved_first_vals.append(_first_scalar(data))
                return True

            mod.save_comfy_image_atomic = _fake_save
            mod.make_thumbnail = lambda *_args, **_kwargs: False

            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                    add_keyframe_set_item(conn, {"set_id": set_id, "idx": 0, "seed": 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                finally:
                    conn.close()

                try:
                    import numpy as np  # type: ignore

                    batch = np.zeros((2, 2, 2, 3), dtype=np.float32)
                    batch[0, :, :, :] = 0.1
                    batch[1, :, :, :] = 0.8
                    mod.KCP_KeyframeSetItemSaveImage().run(db_path, set_id, 0, batch, "webp", True, 1)
                    if not saved_first_vals or abs(saved_first_vals[-1] - 0.8) > 1e-6:
                        return False, f"batch index selection mismatch values={saved_first_vals}"
                    try:
                        mod.KCP_KeyframeSetItemSaveImage().run(db_path, set_id, 0, batch, "webp", True, 999)
                        return False, "expected kcp_batch_index_oob"
                    except RuntimeError as e:
                        if "kcp_batch_index_oob" not in str(e):
                            return False, f"unexpected oob error: {e}"
                except Exception:
                    # fallback path when numpy is unavailable in environment
                    mod.KCP_KeyframeSetItemSaveImage().run(db_path, set_id, 0, [[[[0.1, 0.1, 0.1]]]], "webp", True, 0)

        finally:
            mod.pillow_available = orig_pillow
            mod.save_comfy_image_atomic = orig_save
            mod.make_thumbnail = orig_thumb
        return True, "set-item save batch_index ok"
    except Exception as e:
        return False, str(e)


def smoke_promote_prompt_dna() -> tuple[bool, str]:
    """Smoke: Promote stores prompt fragments and json_fields.prompt payload."""
    try:
        import kcp.nodes.keyframe_promote as mod
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item

        orig_pillow = mod.pillow_available
        orig_load = mod.load_image_as_comfy
        orig_save = mod.save_optional_image
        orig_thumb = mod.make_thumbnail
        try:
            mod.pillow_available = lambda: True
            mod.load_image_as_comfy = lambda *_args, **_kwargs: [[[[1.0, 0.0, 0.0]]]]
            def _fake_save(_img, path, fmt=None):
                _ = fmt
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fake")
                return True
            mod.save_optional_image = _fake_save
            mod.make_thumbnail = lambda *_a, **_k: False

            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                    add_keyframe_set_item(conn, {"set_id": set_id, "idx": 0, "seed": 1, "positive_prompt": "PROMPT+", "negative_prompt": "PROMPT-", "gen_params_json": {}})
                    conn.execute("UPDATE keyframe_set_items SET image_path=? WHERE set_id=? AND idx=?", ("sets/demo/0.webp", set_id, 0))
                    conn.commit()
                    src = Path(td) / "kcp" / "sets" / "demo" / "0.webp"
                    src.parent.mkdir(parents=True, exist_ok=True)
                    src.write_bytes(b"fake")
                finally:
                    conn.close()

                _aid, asset_json = mod.KCP_KeyframePromoteToAsset().run(db_path, set_id, 0, "dna_asset", "", "", "new", "")
                payload = json.loads(asset_json)
                jf = payload.get("json_fields", {})
                prompt = jf.get("prompt", {}) if isinstance(jf, dict) else {}
                if prompt.get("positive") != "PROMPT+" or prompt.get("negative") != "PROMPT-":
                    return False, f"missing prompt dna in json_fields: {jf}"

                conn = connect(Path(db_path))
                try:
                    row = conn.execute("SELECT positive_fragment, negative_fragment FROM assets WHERE id=?", (payload["asset_id"],)).fetchone()
                    if not row or row[0] != "PROMPT+" or row[1] != "PROMPT-":
                        return False, f"unexpected fragments row={row}"
                finally:
                    conn.close()

        finally:
            mod.pillow_available = orig_pillow
            mod.load_image_as_comfy = orig_load
            mod.save_optional_image = orig_save
            mod.make_thumbnail = orig_thumb
        return True, "promote prompt dna ok"
    except Exception as e:
        return False, str(e)


def smoke_asset_pick_input_choices_refresh() -> tuple[bool, str]:
    """Smoke: AssetPick INPUT_TYPES choices include newly saved asset name."""
    try:
        import kcp.nodes.asset_nodes as mod
        from kcp.nodes.project_init import KCP_ProjectInit

        orig_pillow = mod.pillow_available
        try:
            mod.pillow_available = lambda: False
            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                mod.KCP_AssetSave().run(db_path, "character", "choice_asset", "", "p", "", "", "", "new", None)
                inp = mod.KCP_AssetPick.INPUT_TYPES(db_path=db_path, asset_type="character", include_archived=False, refresh_token=1, strict=False)
                choices = inp["required"]["asset_name"][0]
                if "choice_asset" not in choices:
                    return False, f"asset_name choices missing saved asset: {choices}"
        finally:
            mod.pillow_available = orig_pillow
        return True, "asset pick input choices refresh ok"
    except Exception as e:
        return False, str(e)


def smoke_keyframe_set_save_policy_source_hygiene() -> tuple[bool, str]:
    """Smoke: KeyframeSetSave source has a single variant_policy_id payload key."""
    try:
        src = Path("kcp/nodes/keyframe_set_save.py").read_text(encoding="utf-8")
        start = src.find("set_id = create_keyframe_set(")
        if start < 0:
            return False, "create_keyframe_set payload block not found"
        end = src.find("\n            for i, v in enumerate(variants):", start)
        block = src[start:end if end > start else len(src)]
        key_count = block.count('"variant_policy_id":')
        if key_count != 1:
            return False, f"expected 1 variant_policy_id key in payload block, found {key_count}"
        return True, "keyframe set save policy source hygiene ok"
    except Exception as e:
        return False, str(e)


def smoke_keyframe_set_save_policy_fallback() -> tuple[bool, str]:
    """Smoke: KeyframeSetSave derives variant_policy_id from variant_list_json when blank."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_save import KCP_KeyframeSetSave
        from kcp.db.repo import connect

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
            finally:
                conn.close()

            variants = json.dumps({"policy_id": "seed_sweep_12_v1", "variants": []})
            set_id, _, _ = KCP_KeyframeSetSave().run(db_path, "stack1", "{}", "", "{}", variants, 0, 64, 64, "", -1, "")
            conn = connect(Path(db_path))
            try:
                row = conn.execute("SELECT variant_policy_id FROM keyframe_sets WHERE id=?", (set_id,)).fetchone()
                if not row or row[0] != "seed_sweep_12_v1":
                    return False, f"unexpected variant_policy_id row={row}"
            finally:
                conn.close()
        return True, "keyframe set save policy fallback ok"
    except Exception as e:
        return False, str(e)




def smoke_set_load_batch_sorted_idx_order() -> tuple[bool, str]:
    """Smoke: KeyframeSetLoadBatch outputs align to ascending idx list order."""
    try:
        import kcp.nodes.keyframe_set_load_batch as mod
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media

        orig_pillow = mod.pillow_available
        orig_load = mod.load_image_as_comfy
        try:
            mod.pillow_available = lambda: True
            mod.load_image_as_comfy = lambda _p: [[[[1.0, 0.0, 0.0]]]]
            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                root = Path(db_path).parent.parent
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                    for idx in [2, 0, 1]:
                        add_keyframe_set_item(conn, {"set_id": set_id, "idx": idx, "seed": idx + 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                        img_rel = f"sets/{set_id}/{idx}.webp"
                        (root / img_rel).parent.mkdir(parents=True, exist_ok=True)
                        (root / img_rel).write_bytes(b"img")
                        update_set_item_media(conn, set_id, idx, img_rel, img_rel)
                finally:
                    conn.close()

                images, thumbs, items_json = mod.KCP_KeyframeSetLoadBatch().run(db_path, set_id, False, True)
                if len(images) != 3 or len(thumbs) != 3 or len(items_json) != 3:
                    return False, f"length mismatch images={len(images)} thumbs={len(thumbs)} items_json={len(items_json)}"
                parsed = [json.loads(x) for x in items_json]
                if [int(p.get("idx", -1)) for p in parsed] != [0, 1, 2]:
                    return False, f"items_json idx order mismatch: {parsed}"
        finally:
            mod.pillow_available = orig_pillow
            mod.load_image_as_comfy = orig_load
        return True, "set load batch sorted idx order ok"
    except Exception as e:
        return False, str(e)

def smoke_set_load_batch_node() -> tuple[bool, str]:
    """Smoke: KeyframeSetLoadBatch returns list outputs for saved set items."""
    try:
        import kcp.nodes.keyframe_set_load_batch as mod
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media

        orig_pillow = mod.pillow_available
        orig_load = mod.load_image_as_comfy
        try:
            mod.pillow_available = lambda: True
            mod.load_image_as_comfy = lambda _p: [[[[1.0, 0.0, 0.0]]]]
            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                root = Path(db_path).parent.parent
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                    for i in range(2):
                        add_keyframe_set_item(conn, {"set_id": set_id, "idx": i, "seed": i + 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                        img_rel = f"sets/{set_id}/{i}.webp"
                        th_rel = f"sets/{set_id}/{i}_thumb.webp"
                        (root / img_rel).parent.mkdir(parents=True, exist_ok=True)
                        (root / img_rel).write_bytes(b"img")
                        (root / th_rel).write_bytes(b"th")
                        update_set_item_media(conn, set_id, i, img_rel, th_rel)
                finally:
                    conn.close()

                images, thumbs, items_json = mod.KCP_KeyframeSetLoadBatch().run(db_path, set_id, False, True)
                if len(images) != 2 or len(thumbs) != 2 or len(items_json) != 2:
                    return False, f"expected list outputs len=2 got images={len(images)} thumbs={len(thumbs)} items={len(items_json)}"
                if [json.loads(x).get("idx") for x in items_json] != [0, 1]:
                    return False, f"unexpected idx order in items_json: {items_json}"
        finally:
            mod.pillow_available = orig_pillow
            mod.load_image_as_comfy = orig_load
        return True, "set load batch node ok"
    except Exception as e:
        return False, str(e)

def smoke_mark_picked_derives_from_item_json() -> tuple[bool, str]:
    """Smoke: mark picked can derive idx/set_id from item_json when picked_index=-1."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_mark_picked import KCP_KeyframeSetMarkPicked
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
                set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                add_keyframe_set_item(conn, {"set_id": set_id, "idx": 7, "seed": 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
            finally:
                conn.close()

            item_json = json.dumps({"set_id": set_id, "idx": 7})
            out_json, = KCP_KeyframeSetMarkPicked().run(db_path, "", -1, "winner", item_json)
            payload = json.loads(out_json)
            if int(payload.get("picked_index", -999)) != 7:
                return False, f"picked_index mismatch payload={payload}"
            if str(payload.get("id")) != set_id:
                return False, f"set_id mismatch payload={payload}"

            try:
                KCP_KeyframeSetMarkPicked().run(db_path, "", -1, "", "")
                return False, "expected kcp_set_id_missing"
            except RuntimeError as e:
                if "kcp_set_id_missing" not in str(e):
                    return False, f"unexpected missing-set error: {e}"
        return True, "mark picked derives item_json ok"
    except Exception as e:
        return False, str(e)

def smoke_promote_derives_from_item_json() -> tuple[bool, str]:
    """Smoke: promote can derive set_id/idx from item_json when set_id blank and idx=-1."""
    try:
        import kcp.nodes.keyframe_promote as mod
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item

        orig_pillow = mod.pillow_available
        orig_load = mod.load_image_as_comfy
        orig_save = mod.save_optional_image
        orig_thumb = mod.make_thumbnail
        try:
            mod.pillow_available = lambda: True
            mod.load_image_as_comfy = lambda _path: [[[[1.0, 0.0, 0.0]]]]
            mod.save_optional_image = lambda _img, path, fmt=None: (path.parent.mkdir(parents=True, exist_ok=True), path.write_bytes(bytes.fromhex("89504E470D0A1A0A")), True)[2]
            mod.make_thumbnail = lambda _src, dst, max_px=384: (dst.parent.mkdir(parents=True, exist_ok=True), dst.write_bytes(b"RIFFxxxxWEBPVP8 "), True)[2]

            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                root = Path(db_path).parent.parent
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                    add_keyframe_set_item(conn, {"set_id": set_id, "idx": 5, "seed": 9, "positive_prompt": "p+", "negative_prompt": "n-", "gen_params_json": {"steps": 4}})
                    rel = f"sets/{set_id}/5.webp"
                    (root / rel).parent.mkdir(parents=True, exist_ok=True)
                    (root / rel).write_bytes(b"img")
                    conn.execute("UPDATE keyframe_set_items SET image_path=? WHERE set_id=? AND idx=?", (rel, set_id, 5))
                    conn.commit()
                finally:
                    conn.close()

                item_json = json.dumps({"set_id": set_id, "idx": 5})
                aid, out_json = mod.KCP_KeyframePromoteToAsset().run(db_path, "", -1, "winner_item_json", "", "", "new", "", item_json)
                out = json.loads(out_json)
                if not aid or out.get("asset_id") != aid:
                    return False, f"asset_id mismatch out={out}"

                try:
                    mod.KCP_KeyframePromoteToAsset().run(db_path, "", -1, "bad_ref", "", "", "new", "", "")
                    return False, "expected kcp_set_item_ref_missing"
                except RuntimeError as e:
                    if "kcp_set_item_ref_missing" not in str(e):
                        return False, f"unexpected missing-ref error: {e}"
        finally:
            mod.pillow_available = orig_pillow
            mod.load_image_as_comfy = orig_load
            mod.save_optional_image = orig_save
            mod.make_thumbnail = orig_thumb
        return True, "promote derives item_json ok"
    except Exception as e:
        return False, str(e)

def smoke_set_summary_node() -> tuple[bool, str]:
    """Smoke: set summary reports total/saved/picked correctly."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_summary import KCP_KeyframeSetSummary
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            root = Path(db_path).parent.parent
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
                set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                for i in range(12):
                    add_keyframe_set_item(conn, {"set_id": set_id, "idx": i, "seed": i, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                for i in [0, 1, 2]:
                    rel = f"sets/{set_id}/{i}.webp"
                    (root / rel).parent.mkdir(parents=True, exist_ok=True)
                    (root / rel).write_bytes(b"img")
                    update_set_item_media(conn, set_id, i, rel, "")
                conn.execute("UPDATE keyframe_sets SET picked_index=? WHERE id=?", (2, set_id))
                conn.commit()
            finally:
                conn.close()

            summary_text, status_json = KCP_KeyframeSetSummary().run(db_path, set_id)
            status = json.loads(status_json)
            if "set_id=" not in summary_text or "stack_id=stack1" not in summary_text or "variant_policy_id=seed_sweep_12_v1" not in summary_text or "item_count=12" not in summary_text or "picked_index=2" not in summary_text:
                return False, f"summary_text mismatch: {summary_text}"
            if status.get("total_items") != 12 or status.get("picked_index") != 2 or status.get("variant_policy_id") != "seed_sweep_12_v1" or status.get("stack_id") != "stack1":
                return False, f"status payload mismatch: {status}"
        return True, "set summary node ok"
    except Exception as e:
        return False, str(e)

def smoke_set_pick_input_choices() -> tuple[bool, str]:
    """Smoke: KeyframeSetPick INPUT_TYPES includes created set choices with id+created_at label."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_pick import KCP_KeyframeSetPick
        from kcp.db.repo import connect, create_keyframe_set

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
                set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64, "name": "myset"})
            finally:
                conn.close()

            inputs = KCP_KeyframeSetPick.INPUT_TYPES(db_path=db_path, refresh_token=1, strict=False)
            choices = inputs["required"]["set_choice"][0]
            if not any(str(c).startswith(f"{set_id} | ") for c in choices):
                return False, f"set choice missing created set: {choices}"

            chosen = next(c for c in choices if str(c).startswith(f"{set_id} | "))
            rid, set_json, _warn = KCP_KeyframeSetPick().run(db_path, chosen, 2, False)
            if rid != set_id:
                return False, f"set_id mismatch rid={rid} expected={set_id}"
            payload = json.loads(set_json)
            if payload.get("id") != set_id:
                return False, f"set_json missing id payload={payload}"
        return True, "set pick input choices ok"
    except Exception as e:
        return False, str(e)

def smoke_set_item_pick_input_choices() -> tuple[bool, str]:
    """Smoke: KeyframeSetItemPick filters choices by only_with_media and parses labels."""
    try:
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.nodes.keyframe_set_item_pick import KCP_KeyframeSetItemPick
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, update_set_item_media

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            root = Path(db_path).parent.parent
            conn = connect(Path(db_path))
            try:
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
                set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                add_keyframe_set_item(conn, {"set_id": set_id, "idx": 0, "seed": 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                add_keyframe_set_item(conn, {"set_id": set_id, "idx": 1, "seed": 2, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
                img_rel = f"sets/{set_id}/0.webp"
                (root / img_rel).parent.mkdir(parents=True, exist_ok=True)
                (root / img_rel).write_bytes(b"img")
                update_set_item_media(conn, set_id, 0, img_rel, img_rel)
            finally:
                conn.close()

            c1 = KCP_KeyframeSetItemPick.INPUT_TYPES(db_path=db_path, set_id=set_id, refresh_token=1, strict=False)["required"]["item_choice"][0]
            c2 = KCP_KeyframeSetItemPick.INPUT_TYPES(db_path=db_path, set_id=set_id, refresh_token=2, strict=False, only_with_media=False)["required"]["item_choice"][0]
            if not any(str(c).startswith("idx=0 [saved]") for c in c1) or any(str(c).startswith("idx=1") for c in c1):
                return False, f"unexpected media-filtered choices: {c1}"
            if not any("[missing]" in str(c) and str(c).startswith("idx=1") for c in c2):
                return False, f"missing unsaved idx in unfiltered choices: {c2}"

            idx, _item_json, _warn = KCP_KeyframeSetItemPick().run(db_path, set_id, "idx = 1 [missing] seed=2", 0, False, False)
            if idx != 1:
                return False, f"label parse mismatch idx={idx}"
        return True, "set item pick input choices ok"
    except Exception as e:
        return False, str(e)

def smoke_refresh_token_convention_across_picks() -> tuple[bool, str]:
    """Smoke: refresh_token path updates choices for Asset/Stack/Set/Item pickers."""
    try:
        import kcp.nodes.asset_nodes as asset
        import kcp.nodes.stack_nodes as stack
        from kcp.nodes.keyframe_set_pick import KCP_KeyframeSetPick
        from kcp.nodes.keyframe_set_item_pick import KCP_KeyframeSetItemPick
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item

        with tempfile.TemporaryDirectory() as td:
            db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
            # before inserts
            a0 = asset.KCP_AssetPick.INPUT_TYPES(db_path=db_path, asset_type="character", include_archived=False, refresh_token=0, strict=False)["required"]["asset_name"][0]
            s0 = stack.KCP_StackPick.INPUT_TYPES(db_path=db_path, include_archived=False, refresh_token=0, strict=False)["required"]["stack_name"][0]

            conn = connect(Path(db_path))
            try:
                aid = asset.create_asset(conn, {
                    "type": "character",
                    "name": "r_asset",
                    "description": "",
                    "tags": [],
                    "positive_fragment": "p",
                    "negative_fragment": "n",
                    "json_fields": {},
                    "version": 1,
                    "parent_id": None,
                })
                _ = aid
                conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                conn.commit()
                set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64, "name": "sset"})
                add_keyframe_set_item(conn, {"set_id": set_id, "idx": 0, "seed": 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {}})
            finally:
                conn.close()

            a1 = asset.KCP_AssetPick.INPUT_TYPES(db_path=db_path, asset_type="character", include_archived=False, refresh_token=1, strict=False)["required"]["asset_name"][0]
            s1 = stack.KCP_StackPick.INPUT_TYPES(db_path=db_path, include_archived=False, refresh_token=1, strict=False)["required"]["stack_name"][0]
            set_choices = KCP_KeyframeSetPick.INPUT_TYPES(db_path=db_path, refresh_token=1, strict=False)["required"]["set_choice"][0]
            item_choices = KCP_KeyframeSetItemPick.INPUT_TYPES(db_path=db_path, set_id=set_id, only_with_media=False, refresh_token=1, strict=False)["required"]["item_choice"][0]

            if any("r_asset" == c for c in a0) or not any("r_asset" == c for c in a1):
                return False, f"asset choices refresh mismatch before={a0} after={a1}"
            if any("stack1" == c for c in s0) or not any("stack1" == c for c in s1):
                return False, f"stack choices refresh mismatch before={s0} after={s1}"
            if not any(str(set_id) in c for c in set_choices):
                return False, f"set choices missing: {set_choices}"
            if not any(str(c).startswith("idx=0 ") for c in item_choices):
                return False, f"item choices missing idx 0: {item_choices}"
        return True, "refresh_token convention across picks ok"
    except Exception as e:
        return False, str(e)


def smoke_promote_dependency_input() -> tuple[bool, str]:
    """Smoke: promote node exposes depends_on_item_json dependency input."""
    try:
        from kcp.nodes.keyframe_promote import KCP_KeyframePromoteToAsset

        inputs = KCP_KeyframePromoteToAsset.INPUT_TYPES()
        required = inputs.get("required", {})
        optional = inputs.get("optional", {})
        if "depends_on_item_json" not in required and "depends_on_item_json" not in optional:
            return False, "depends_on_item_json missing from INPUT_TYPES"
        return True, "promote dependency input ok"
    except Exception as e:
        return False, str(e)


def smoke_set_image_load_promote_e2e() -> tuple[bool, str]:
    """Smoke: end-to-end set -> save image -> load -> promote using synthetic IMAGE."""
    try:
        import kcp.nodes.keyframe_set_item_save_image as save_mod
        import kcp.nodes.keyframe_set_item_load as load_mod
        import kcp.nodes.keyframe_promote as promote_mod
        from kcp.nodes.project_init import KCP_ProjectInit
        from kcp.db.repo import connect, create_keyframe_set, add_keyframe_set_item, get_asset_by_type_name

        orig_save_pillow = save_mod.pillow_available
        orig_save_atomic = save_mod.save_comfy_image_atomic
        orig_make_thumb = save_mod.make_thumbnail
        orig_load_img = load_mod.load_image_as_comfy
        orig_promote_pillow = promote_mod.pillow_available
        orig_promote_load = promote_mod.load_image_as_comfy
        orig_promote_save = promote_mod.save_optional_image
        orig_promote_thumb = promote_mod.make_thumbnail
        try:
            save_mod.pillow_available = lambda: True
            def _save_atomic(_img, path, fmt=None):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"RIFFxxxxWEBPVP8 ")
                return True
            save_mod.save_comfy_image_atomic = _save_atomic
            save_mod.make_thumbnail = lambda _src, dst, max_px=384: (dst.parent.mkdir(parents=True, exist_ok=True), dst.write_bytes(b"RIFFxxxxWEBPVP8 "), True)[2]

            load_mod.load_image_as_comfy = lambda _path: [[[[1.0, 0.0, 0.0]]]]

            promote_mod.pillow_available = lambda: True
            promote_mod.load_image_as_comfy = lambda _path: [[[[1.0, 0.0, 0.0]]]]
            promote_mod.save_optional_image = lambda _img, path, fmt=None: (path.parent.mkdir(parents=True, exist_ok=True), path.write_bytes(bytes.fromhex("89504E470D0A1A0A")), True)[2]
            promote_mod.make_thumbnail = lambda _src, dst, max_px=384: (dst.parent.mkdir(parents=True, exist_ok=True), dst.write_bytes(b"RIFFxxxxWEBPVP8 "), True)[2]

            with tempfile.TemporaryDirectory() as td:
                db_path, _, _ = KCP_ProjectInit().run(str(Path(td) / "kcp"), "kcp.sqlite", True)
                conn = connect(Path(db_path))
                try:
                    conn.execute("INSERT INTO stacks (id,name,created_at,updated_at) VALUES (?,?,?,?)", ("stack1", "stack1", 1, 1))
                    conn.commit()
                    set_id = create_keyframe_set(conn, {"stack_id": "stack1", "variant_policy_id": "seed_sweep_12_v1", "variant_policy_json": {}, "base_seed": 1, "width": 64, "height": 64})
                    add_keyframe_set_item(conn, {"set_id": set_id, "idx": 0, "seed": 1, "positive_prompt": "p", "negative_prompt": "n", "gen_params_json": {"seed": 1}})
                finally:
                    conn.close()

                save_json, = save_mod.KCP_KeyframeSetItemSaveImage().run(db_path, set_id, 0, [[[[1,0,0]]]], "webp", True)
                if "image_path" not in save_json:
                    return False, "save output missing image_path"

                image, thumb, item_json = load_mod.KCP_KeyframeSetItemLoad().run(db_path, set_id, 0, True)
                if image is None or thumb is None:
                    return False, "load output image/thumb empty"

                promote_id, _ = promote_mod.KCP_KeyframePromoteToAsset().run(db_path, set_id, 0, "winner_asset", "", "", "new", item_json)
                conn = connect(Path(db_path))
                try:
                    row = get_asset_by_type_name(conn, "keyframe", "winner_asset", include_archived=True)
                    if not row or row["id"] != promote_id:
                        return False, "promoted asset row missing"
                    img_path = Path(db_path).parent.parent / row["image_path"]
                    if not img_path.exists():
                        return False, "promoted image file missing"
                finally:
                    conn.close()
        finally:
            save_mod.pillow_available = orig_save_pillow
            save_mod.save_comfy_image_atomic = orig_save_atomic
            save_mod.make_thumbnail = orig_make_thumb
            load_mod.load_image_as_comfy = orig_load_img
            promote_mod.pillow_available = orig_promote_pillow
            promote_mod.load_image_as_comfy = orig_promote_load
            promote_mod.save_optional_image = orig_promote_save
            promote_mod.make_thumbnail = orig_promote_thumb

        return True, "set/save/load/promote e2e ok"
    except Exception as e:
        return False, str(e)

def smoke_readme_mentions_winner_loop_wiring() -> tuple[bool, str]:
    """Smoke: README contains winner-loop and on-ramp wiring lines."""
    try:
        src = Path("README.md").read_text(encoding="utf-8")
        required_exact = [
            "KCP_KeyframeSetPick.set_id` -> `KCP_KeyframeSetLoadBatch.set_id",
            "KCP_KeyframeSetItemPick.item_json` -> `KCP_KeyframeSetMarkPicked.item_json",
            "KCP_KeyframeSetItemPick.item_json` -> `KCP_KeyframePromoteToAsset.item_json",
        ]
        for s in required_exact:
            if s not in src:
                return False, f"README missing winner wiring string: {s}"

        if "## Opinionated On-Ramp: Render → Persist → Pick Winner" not in src:
            return False, "README missing on-ramp header"
        onramp_candidates = [
            "VariantPack.variant_list_json -> VariantUnroll.variant_list_json",
            "KSampler IMAGE -> KCP_KeyframeSetItemSaveBatch.images",
            "KeyframeSetSave.set_id -> KCP_KeyframeSetItemSaveBatch.set_id",
        ]
        hits = sum(1 for s in onramp_candidates if s in src)
        if hits < 2:
            return False, f"README missing on-ramp wiring lines hits={hits}"
        return True, "readme winner loop wiring ok"
    except Exception as e:
        return False, str(e)
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--receipt", default="UNSPECIFIED")
    args = parser.parse_args()

    oracles: list[str] = []
    all_ok = True

    compile_target = "kcp" if Path("kcp").exists() else "."
    compile_cmd = [sys.executable, "-m", "compileall", compile_target]
    oracles.append("compileall")
    rc, out, err = run(compile_cmd)
    print(f"$ {' '.join(compile_cmd)}")
    if out:
        print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    if rc != 0:
        all_ok = False

    if Path("kcp").exists() and not args.fast:
        for name, fn in [
            ("smoke_asset_thumb", smoke_asset_thumb),
            ("smoke_pack_root_entrypoint_import", smoke_pack_root_entrypoint_import),
            ("smoke_asset_overwrite_preserves_media_without_image", smoke_asset_overwrite_preserves_media_without_image),
            ("smoke_project_init_respects_create_if_missing", smoke_project_init_respects_create_if_missing),
            ("smoke_variant_pick", smoke_variant_pick),
            ("smoke_variant_unroll_lists", smoke_variant_unroll_lists),
            ("smoke_set_item_pick_defaults_saved_only", smoke_set_item_pick_defaults_saved_only),
            ("smoke_render_pack_status_counts_missing", smoke_render_pack_status_counts_missing),
            ("smoke_keyframe_set_save_policy_json_fallback", smoke_keyframe_set_save_policy_json_fallback),
            ("smoke_keyframe_set_save_derives_dims_seed_when_defaulted", smoke_keyframe_set_save_derives_dims_seed_when_defaulted),
            ("smoke_keyframe_set_save_stack_json_fallback_and_provenance", smoke_keyframe_set_save_stack_json_fallback_and_provenance),
            ("smoke_mark_picked", smoke_mark_picked),
            ("smoke_mark_picked_derives_from_item_json", smoke_mark_picked_derives_from_item_json),
            ("smoke_root_resolution", smoke_root_resolution),
            ("smoke_output_nodes", smoke_output_nodes),
            ("smoke_picker_empty_ok", smoke_picker_empty_ok),
            ("smoke_picker_not_found_codes", smoke_picker_not_found_codes),
            ("smoke_default_db_path_hint", smoke_default_db_path_hint),
            ("smoke_asset_pick_returns_media_tensors", smoke_asset_pick_returns_media_tensors),
            ("smoke_asset_pick_missing_media_strictness", smoke_asset_pick_missing_media_strictness),
            ("smoke_stack_pick_missing_refs_strictness", smoke_stack_pick_missing_refs_strictness),
            ("smoke_set_item_media_update", smoke_set_item_media_update),
            ("smoke_set_item_load", smoke_set_item_load),
            ("smoke_promote_keyframe", smoke_promote_keyframe),
            ("smoke_asset_save_modes", smoke_asset_save_modes),
            ("smoke_image_format_headers", smoke_image_format_headers),
            ("smoke_db_path_guardrails", smoke_db_path_guardrails),
            ("smoke_db_path_trim_quotes", smoke_db_path_trim_quotes),
            ("smoke_connect_migrates", smoke_connect_migrates),
            ("smoke_set_item_save_error_details", smoke_set_item_save_error_details),
            ("smoke_set_item_not_found_diagnostic", smoke_set_item_not_found_diagnostic),
            ("smoke_set_item_save_batch_node", smoke_set_item_save_batch_node),
            ("smoke_set_item_save_batch_index", smoke_set_item_save_batch_index),
            ("smoke_set_load_batch_node", smoke_set_load_batch_node),
            ("smoke_set_load_batch_sorted_idx_order", smoke_set_load_batch_sorted_idx_order),
            ("smoke_set_summary_node", smoke_set_summary_node),
            ("smoke_set_pick_input_choices", smoke_set_pick_input_choices),
            ("smoke_set_item_pick_input_choices", smoke_set_item_pick_input_choices),
            ("smoke_promote_prompt_dna", smoke_promote_prompt_dna),
            ("smoke_asset_pick_input_choices_refresh", smoke_asset_pick_input_choices_refresh),
            ("smoke_keyframe_set_save_policy_source_hygiene", smoke_keyframe_set_save_policy_source_hygiene),
            ("smoke_keyframe_set_save_policy_fallback", smoke_keyframe_set_save_policy_fallback),
            ("smoke_refresh_token_convention_across_picks", smoke_refresh_token_convention_across_picks),
            ("smoke_promote_dependency_input", smoke_promote_dependency_input),
            ("smoke_promote_derives_from_item_json", smoke_promote_derives_from_item_json),
            ("smoke_set_image_load_promote_e2e", smoke_set_image_load_promote_e2e),
            ("smoke_readme_mentions_winner_loop_wiring", smoke_readme_mentions_winner_loop_wiring),
        ]:
            ok, msg = fn()
            oracles.append(name)
            print(f"$ {name} -> {'PASS' if ok else 'FAIL'}: {msg}")
            if not ok:
                all_ok = False

    has_tests = Path("tests").exists() and any(Path("tests").glob("test*.py"))
    if has_tests and not args.fast:
        test_cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
        oracles.append("unittest")
        rc, out, err = run(test_cmd)
        print(f"$ {' '.join(test_cmd)}")
        if out:
            print(out, end="")
        if err:
            print(err, end="", file=sys.stderr)
        if rc != 0:
            all_ok = False

    write_receipt(args.receipt, oracles, all_ok)
    print(f"VERIFY_RESULT={'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
