from __future__ import annotations

import json

from kcp.db.paths import kcp_root_from_db_path, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect, get_set_item, update_set_item_media
from kcp.util.image_io import make_thumbnail, pillow_available, save_comfy_image_atomic


class KCP_KeyframeSetItemSaveBatch:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
                "idx_start": ("INT", {"default": 0, "min": 0}),
                "images": ("IMAGE",),
                "format": ("STRING", {"default": "webp"}),
                "overwrite": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("set_id", "saved_count", "batch_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    @staticmethod
    def _batch_size(images) -> int:
        data = images
        if hasattr(data, "detach"):
            data = data.detach()
        if hasattr(data, "shape"):
            shape = tuple(int(x) for x in data.shape)
            if len(shape) == 4:
                return int(shape[0])
            if len(shape) == 3:
                return 1
            raise RuntimeError(f"kcp_batch_shape_unsupported: shape={shape}")
        return 1

    @staticmethod
    def _batch_slice(images, bi: int, batch_size: int):
        if batch_size <= 1:
            return images
        return images[bi : bi + 1]

    def run(self, db_path: str, set_id: str, idx_start: int, images, format: str = "webp", overwrite: bool = True):
        if not pillow_available():
            raise RuntimeError("kcp_io_write_failed: Pillow required to save IMAGE input; install with pip install pillow")
        if idx_start < 0:
            raise RuntimeError("kcp_set_item_invalid_idx")

        ext = (format or "webp").lower().strip(".")
        if ext not in {"webp", "png"}:
            ext = "webp"
        encode_fmt = "WEBP" if ext == "webp" else "PNG"

        try:
            dbp = normalize_db_path(db_path)
            root = kcp_root_from_db_path(db_path)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e

        batch_size = self._batch_size(images)

        try:
            conn = connect(dbp)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            for bi in range(batch_size):
                idx = int(idx_start + bi)
                row = get_set_item(conn, set_id, idx)
                if row is None:
                    raise RuntimeError(f"kcp_set_item_not_found: set_id={set_id} first_missing_idx={idx} db_path={dbp} root={root}")

            saved = []
            for bi in range(batch_size):
                idx = int(idx_start + bi)
                image_rel = f"sets/{set_id}/{idx}.{ext}"
                thumb_rel = f"sets/{set_id}/{idx}_thumb.webp"
                image_abs = (root / image_rel).resolve()
                thumb_abs = (root / thumb_rel).resolve()

                if (image_abs.exists() or thumb_abs.exists()) and not overwrite:
                    raise RuntimeError(f"kcp_set_item_media_exists: set_id={set_id} idx={idx}")

                try:
                    image_abs.parent.mkdir(parents=True, exist_ok=True)
                    image_one = self._batch_slice(images, bi, batch_size)
                    ok = save_comfy_image_atomic(image_one, image_abs, fmt=encode_fmt)
                    if not ok:
                        raise RuntimeError("failed to save set item image")
                    if not make_thumbnail(image_abs, thumb_abs, max_px=384):
                        thumb_rel = image_rel
                except Exception as e:
                    raise RuntimeError(
                        f"kcp_io_write_failed: set_id={set_id} idx={idx} root={root} "
                        f"image_path={image_abs} thumb_path={thumb_abs} err={e!r}"
                    ) from e

                update_set_item_media(conn, set_id, idx, image_rel, thumb_rel)
                saved.append({"idx": idx, "image_path": image_rel, "thumb_path": thumb_rel})

            return (set_id, len(saved), json.dumps({"set_id": set_id, "saved_count": len(saved), "items": saved}))
        finally:
            conn.close()
