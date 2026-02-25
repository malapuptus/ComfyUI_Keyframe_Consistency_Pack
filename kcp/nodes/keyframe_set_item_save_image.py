from __future__ import annotations

import json
import os

from kcp.db.paths import kcp_root_from_db_path, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect, get_set_item, update_set_item_media
from kcp.util.image_io import make_thumbnail, pillow_available, save_comfy_image_atomic


DEBUG = False
if os.getenv("KCP_DEBUG_SET_ITEM_SAVE_IMAGE", "").strip().lower() in {"1", "true", "yes", "on"}:
    DEBUG = True


class KCP_KeyframeSetItemSaveImage:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
                "idx": ("INT", {"default": 0, "min": 0}),
                "image": ("IMAGE",),
                "format": ("STRING", {"default": "webp"}),
                "overwrite": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("item_json",)
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_id: str, idx: int, image, format: str = "webp", overwrite: bool = True, batch_index=0):
        if not pillow_available():
            raise RuntimeError("kcp_io_write_failed: Pillow required to save IMAGE input; install with pip install pillow")
        if idx < 0:
            raise RuntimeError("kcp_set_item_invalid_idx")

        # Select one image from a batch if needed
        try:
            shape = getattr(image, "shape", None)
            if shape is not None and len(shape) == 4:
                b = int(shape[0])
                bi = int(batch_index or 0)
                if bi < 0 or bi >= b:
                    raise RuntimeError(f"kcp_batch_index_oob: batch_index={bi} batch_size={b}")
                image = image[bi]
        except Exception:
            # If shape introspection fails, keep original; downstream save will raise if invalid.
            pass

        ext = (format or "webp").lower().strip(".")
        if ext not in {"webp", "png"}:
            ext = "webp"
        encode_fmt = "WEBP" if ext == "webp" else "PNG"

        try:
            dbp = normalize_db_path(db_path)
            root = kcp_root_from_db_path(db_path)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        if DEBUG:
            print(
                f"[KCP_KeyframeSetItemSaveImage] raw_db_path={db_path!r} "
                f"normalized_db_path={dbp} resolved_root={root}"
            )
        image_rel = f"sets/{set_id}/{idx}.{ext}"
        thumb_rel = f"sets/{set_id}/{idx}_thumb.webp"
        image_abs = (root / image_rel).resolve()
        thumb_abs = (root / thumb_rel).resolve()

        try:
            conn = connect(dbp)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            row = get_set_item(conn, set_id, idx)
            if row is None:
                raise RuntimeError(f"kcp_set_item_not_found: set_id={set_id} idx={idx} db_path={dbp} root={root}")

            if (image_abs.exists() or thumb_abs.exists()) and not overwrite:
                raise RuntimeError("kcp_set_item_media_exists")

            try:
                image_abs.parent.mkdir(parents=True, exist_ok=True)
                ok = save_comfy_image_atomic(image, image_abs, fmt=encode_fmt)
                if not ok:
                    raise RuntimeError("failed to save set item image")
                if not make_thumbnail(image_abs, thumb_abs, max_px=384):
                    thumb_rel = image_rel
            except Exception as e:
                raise RuntimeError(
                    f"kcp_io_write_failed: set_id={set_id} idx={idx} root={root} "
                    f"image_path={image_abs} thumb_path={thumb_abs} err={e!r}"
                ) from e

            updated = update_set_item_media(conn, set_id, idx, image_rel, thumb_rel)
            payload = {k: updated[k] for k in updated.keys()}
            return (json.dumps(payload),)
        finally:
            conn.close()
