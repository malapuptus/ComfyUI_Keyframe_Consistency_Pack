
from __future__ import annotations

import json

from kcp.db.paths import kcp_root_from_db_path, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect
from kcp.util.image_io import load_image_as_comfy, pillow_available


class KCP_KeyframeSetLoadBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
                "strict": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "only_with_media": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("images", "thumbs", "items_json")
    OUTPUT_IS_LIST = (True, True, True)
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_id: str, strict: bool = False, only_with_media: bool = True):
        if not pillow_available():
            raise RuntimeError("kcp_io_read_failed: Pillow required to load IMAGE output; install with pip install pillow")
        try:
            dbp = normalize_db_path(db_path)
            root = kcp_root_from_db_path(db_path)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e

        try:
            conn = connect(dbp)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            rows = conn.execute("SELECT * FROM keyframe_set_items WHERE set_id=? ORDER BY idx", (set_id,)).fetchall()
        finally:
            conn.close()

        rows = sorted(rows, key=lambda r: int(r["idx"]))
        images = []
        thumbs = []
        items_json = []
        for row in rows:
            idx = int(row["idx"])
            image_rel = (row["image_path"] or "").strip()
            thumb_rel = (row["thumb_path"] or "").strip()
            if only_with_media and not image_rel:
                continue

            image_abs = (root / image_rel).resolve() if image_rel else None
            thumb_abs = (root / thumb_rel).resolve() if thumb_rel else None
            exists = image_abs is not None and image_abs.exists()
            if not exists:
                if strict:
                    raise RuntimeError(f"kcp_set_media_missing: set_id={set_id} idx={idx} image_path={image_abs}")
                images.append(None)
                thumbs.append(None)
                items_json.append(json.dumps({
                    "set_id": set_id,
                    "idx": idx,
                    "image_path": image_rel,
                    "thumb_path": thumb_rel,
                    "warning": {"code": "kcp_set_media_missing", "idx": idx, "image_path": str(image_abs) if image_abs else ""},
                }))
                continue

            try:
                image_obj = load_image_as_comfy(image_abs)
                thumb_obj = load_image_as_comfy(thumb_abs) if (thumb_abs is not None and thumb_abs.exists()) else image_obj
            except Exception as e:
                if strict:
                    raise RuntimeError(f"kcp_set_media_missing: set_id={set_id} idx={idx} image_path={image_abs} err={e!r}") from e
                images.append(None)
                thumbs.append(None)
                items_json.append(json.dumps({
                    "set_id": set_id,
                    "idx": idx,
                    "image_path": image_rel,
                    "thumb_path": thumb_rel,
                    "warning": {"code": "kcp_set_media_missing", "idx": idx, "image_path": str(image_abs), "err": repr(e)},
                }))
                continue

            images.append(image_obj)
            thumbs.append(thumb_obj)
            items_json.append(json.dumps({"set_id": set_id, "idx": idx, "image_path": image_rel, "thumb_path": thumb_rel}))

        return (images, thumbs, items_json)
