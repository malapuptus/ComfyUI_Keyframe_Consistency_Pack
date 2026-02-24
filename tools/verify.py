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

import subprocess
import sys
from pathlib import Path


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
            ("smoke_variant_pick", smoke_variant_pick),
            ("smoke_mark_picked", smoke_mark_picked),
            ("smoke_root_resolution", smoke_root_resolution),
            ("smoke_output_nodes", smoke_output_nodes),
            ("smoke_picker_empty_ok", smoke_picker_empty_ok),
            ("smoke_picker_not_found_codes", smoke_picker_not_found_codes),
            ("smoke_default_db_path_hint", smoke_default_db_path_hint),
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
            ("smoke_promote_dependency_input", smoke_promote_dependency_input),
            ("smoke_set_image_load_promote_e2e", smoke_set_image_load_promote_e2e),
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
