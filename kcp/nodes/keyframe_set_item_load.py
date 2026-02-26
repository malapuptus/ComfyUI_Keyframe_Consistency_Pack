from __future__ import annotations

import json

from kcp.db.paths import kcp_root_from_db_path, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect, get_set_item
from kcp.util.image_io import load_image_as_comfy


class KCP_KeyframeSetItemLoad:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
                "idx": ("INT", {"default": 0, "min": 0}),
                "strict": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("image", "thumb_image", "item_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_id: str, idx: int, strict: bool = True):
        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            row = get_set_item(conn, set_id, idx)
            if row is None:
                raise RuntimeError("kcp_set_item_not_found")

            payload = {
                "set_id": row["set_id"],
                "idx": row["idx"],
                "positive_prompt": row["positive_prompt"],
                "negative_prompt": row["negative_prompt"],
                "gen_params_json": row["gen_params_json"],
                "image_path": row["image_path"],
                "thumb_path": row["thumb_path"],
            }

            root = kcp_root_from_db_path(db_path)
            image = None
            thumb = None

            if row["image_path"]:
                ip = root / row["image_path"]
                if ip.exists():
                    image = load_image_as_comfy(ip)
                elif strict:
                    raise RuntimeError("kcp_set_item_image_missing")
                else:
                    payload["warning_json"] = {"warning": "image missing on disk"}

            if row["thumb_path"]:
                tp = root / row["thumb_path"]
                if tp.exists():
                    thumb = load_image_as_comfy(tp)
                elif strict:
                    raise RuntimeError("kcp_set_item_image_missing")
                else:
                    payload.setdefault("warning_json", {"warning": "thumb missing on disk"})

            return (image, thumb, json.dumps(payload))
        finally:
            conn.close()
