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

    def _fake_save_optional_image(_image, path: Path) -> bool:
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
        return True, "picker empty non-strict ok"
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
            ("smoke_set_item_media_update", smoke_set_item_media_update),
            ("smoke_set_item_load", smoke_set_item_load),
            ("smoke_promote_keyframe", smoke_promote_keyframe),
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
