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

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "thumbs", "items_json", "labels_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    @staticmethod
    def _to_batch(image_obj):
        data = image_obj
        if hasattr(data, "detach"):
            data = data.detach()
        if hasattr(data, "shape"):
            shape = tuple(int(x) for x in data.shape)
            if len(shape) == 4:
                return image_obj
            if len(shape) == 3:
                return image_obj[None, ...]
        return image_obj

    @staticmethod
    def _concat_batches(parts):
        if not parts:
            return None
        first = parts[0]
        if len(parts) == 1:
            return first
        try:
            import torch  # type: ignore

            if isinstance(first, torch.Tensor):
                return torch.cat(parts, dim=0)
        except Exception:
            pass
        try:
            import numpy as np  # type: ignore

            return np.concatenate(parts, axis=0)
        except Exception:
            out = []
            for p in parts:
                if isinstance(p, list):
                    out.extend(p)
                else:
                    out.append(p)
            return out

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
            rows = conn.execute(
                "SELECT * FROM keyframe_set_items WHERE set_id=? ORDER BY idx",
                (set_id,),
            ).fetchall()
            rows = sorted(rows, key=lambda r: int(r["idx"]))
        finally:
            conn.close()

        images = []
        thumbs = []
        items = []
        labels = []
        missing = []
        for row in rows:
            image_rel = (row["image_path"] or "").strip()
            thumb_rel = (row["thumb_path"] or "").strip()
            if only_with_media and not image_rel:
                continue

            image_abs = (root / image_rel).resolve() if image_rel else None
            thumb_abs = (root / thumb_rel).resolve() if thumb_rel else None

            if image_abs is None or (not image_abs.exists()):
                missing.append({"idx": int(row["idx"]), "image_path": str(image_abs) if image_abs else ""})
                if strict:
                    raise RuntimeError(f"kcp_set_media_missing: set_id={set_id} idx={int(row['idx'])} image_path={image_abs}")
                continue

            try:
                images.append(self._to_batch(load_image_as_comfy(image_abs)))
                if thumb_abs is not None and thumb_abs.exists():
                    thumbs.append(self._to_batch(load_image_as_comfy(thumb_abs)))
                else:
                    thumbs.append(self._to_batch(load_image_as_comfy(image_abs)))
                item_payload = {"idx": int(row["idx"]), "image_path": image_rel, "thumb_path": thumb_rel, "seed": row["seed"]}
                items.append(item_payload)
                row_dict = {k: row[k] for k in row.keys()}
                labels.append({"idx": int(row["idx"]), "status": "saved", "seed": row["seed"], "label": row_dict.get("label", "")})
            except Exception as e:
                if strict:
                    raise RuntimeError(f"kcp_set_media_missing: set_id={set_id} idx={int(row['idx'])} image_path={image_abs} err={e!r}") from e
                missing.append({"idx": int(row["idx"]), "image_path": str(image_abs), "err": repr(e)})

        payload = {"set_id": set_id, "count": len(items), "items": items}
        if missing:
            payload["warning"] = {"code": "kcp_set_media_missing", "missing": missing}

        return (self._concat_batches(images), self._concat_batches(thumbs), json.dumps(payload), json.dumps(labels))
