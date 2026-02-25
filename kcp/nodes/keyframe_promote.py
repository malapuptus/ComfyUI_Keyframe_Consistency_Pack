from __future__ import annotations

import json
import sqlite3

from kcp.db.paths import kcp_root_from_db_path, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect, create_asset, get_asset_by_type_name, get_keyframe_set, get_set_item
from kcp.util.hashing import sha256_file
from kcp.util.image_io import load_image_as_comfy, make_thumbnail, pillow_available, save_optional_image
from kcp.util.time_utils import now_ms


class KCP_KeyframePromoteToAsset:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
                "idx": ("INT", {"default": 0, "min": 0}),
                "name": ("STRING", {"default": ""}),
                "description": ("STRING", {"default": ""}),
                "tags_csv": ("STRING", {"default": ""}),
                "save_mode": (["new", "overwrite_by_name"],),
            },
            "optional": {
                "depends_on_item_json": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("asset_id", "asset_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(
        self,
        db_path: str,
        set_id: str,
        idx: int,
        name: str,
        description: str = "",
        tags_csv: str = "",
        save_mode: str = "new",
        depends_on_item_json: str = "",
    ):
        _ = depends_on_item_json
        if not pillow_available():
            raise RuntimeError("kcp_io_write_failed: Pillow required to save IMAGE input; install with pip install pillow")

        try:
            dbp = normalize_db_path(db_path)
            root = kcp_root_from_db_path(db_path)
            conn = connect(dbp)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            item = get_set_item(conn, set_id, idx)
            if item is None:
                raise RuntimeError("kcp_set_item_not_found")
            if not (item["image_path"] or "").strip():
                raise RuntimeError("kcp_set_item_image_missing")

            src_path = root / item["image_path"]
            if not src_path.exists():
                raise RuntimeError("kcp_set_item_image_missing")

            existing = get_asset_by_type_name(conn, "keyframe", name, include_archived=True)
            if existing and save_mode == "new":
                raise RuntimeError("kcp_asset_name_conflict")

            set_row = get_keyframe_set(conn, set_id)
            gen_params = json.loads(item["gen_params_json"]) if item["gen_params_json"] else {}
            provenance = {
                "source": {"set_id": set_id, "idx": int(idx)},
                "gen_params": gen_params,
                "policy_id": set_row["variant_policy_id"] if set_row else "",
                "stack_id": set_row["stack_id"] if set_row else "",
            }
            tags = [t.strip() for t in tags_csv.split(",") if t.strip()]

            if existing and save_mode == "overwrite_by_name":
                asset_id = existing["id"]
                conn.execute(
                    """
                    UPDATE assets SET
                      description=?, tags_json=?, positive_fragment=?, negative_fragment=?,
                      json_fields=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        description,
                        json.dumps(tags),
                        item["positive_prompt"],
                        item["negative_prompt"],
                        json.dumps(provenance),
                        now_ms(),
                        asset_id,
                    ),
                )
                conn.commit()
            else:
                asset_id = create_asset(
                    conn,
                    {
                        "type": "keyframe",
                        "name": name,
                        "description": description,
                        "tags": tags,
                        "positive_fragment": item["positive_prompt"],
                        "negative_fragment": item["negative_prompt"],
                        "json_fields": provenance,
                    },
                )

            image_path = root / "images" / "keyframe" / asset_id / "original.png"
            thumb_path = root / "thumbs" / "keyframe" / asset_id / "thumb.webp"
            image_obj = load_image_as_comfy(src_path)
            if not save_optional_image(image_obj, image_path):
                raise RuntimeError("kcp_io_write_failed: failed to save promoted keyframe image")
            make_thumbnail(image_path, thumb_path, max_px=384)
            image_rel = str(image_path.relative_to(root))
            thumb_rel = str(thumb_path.relative_to(root)) if thumb_path.exists() else ""
            image_hash = sha256_file(image_path)

            conn.execute(
                "UPDATE assets SET image_path=?, thumb_path=?, image_hash=? WHERE id=?",
                (image_rel, thumb_rel, image_hash, asset_id),
            )
            conn.commit()

            out = {
                "asset_id": asset_id,
                "type": "keyframe",
                "name": name,
                "json_fields": provenance,
                "image_path": image_rel,
                "thumb_path": thumb_rel,
            }
            return (asset_id, json.dumps(out))
        except sqlite3.IntegrityError as e:
            raise RuntimeError(f"kcp_asset_name_conflict: {e}") from e
        finally:
            conn.close()
