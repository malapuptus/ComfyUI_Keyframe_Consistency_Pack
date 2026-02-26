from __future__ import annotations

import json

from kcp.db.paths import normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect, set_picked_index
from kcp.util.json_utils import parse_json_object


class KCP_KeyframeSetMarkPicked:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
                "picked_index": ("INT", {"default": -1, "min": -1}),
                "notes": ("STRING", {"default": ""}),
            },
            "optional": {
                "item_json": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("set_json",)
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_id: str, picked_index: int, notes: str = "", item_json: str = ""):
        resolved_set_id = (set_id or "").strip()
        resolved_idx = int(picked_index)
        if resolved_idx < 0 and (item_json or "").strip():
            item = parse_json_object(item_json)
            if not resolved_set_id:
                resolved_set_id = str(item.get("set_id") or "").strip()
            if "idx" not in item:
                raise RuntimeError("kcp_set_item_not_found")
            resolved_idx = int(item.get("idx"))

        if not resolved_set_id:
            raise RuntimeError("kcp_set_id_missing")
        if resolved_idx < 0:
            raise RuntimeError("kcp_set_item_not_found")

        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            row = set_picked_index(conn, resolved_set_id, resolved_idx, notes)
            if row is None:
                raise RuntimeError(f"kcp_keyframe_set_not_found: {resolved_set_id}")
            payload = {k: row[k] for k in row.keys()}
            return (json.dumps(payload),)
        finally:
            conn.close()
