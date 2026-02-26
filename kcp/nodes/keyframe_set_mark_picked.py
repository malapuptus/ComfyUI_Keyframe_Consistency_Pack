from __future__ import annotations

import json
from kcp.db.paths import normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect, set_picked_index


class KCP_KeyframeSetMarkPicked:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
                "picked_index": ("INT", {"default": 0, "min": 0}),
                "notes": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("set_json",)
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_id: str, picked_index: int, notes: str = ""):
        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            row = set_picked_index(conn, set_id, picked_index, notes)
            if row is None:
                raise RuntimeError(f"kcp_keyframe_set_not_found: {set_id}")
            payload = {k: row[k] for k in row.keys()}
            return (json.dumps(payload),)
        finally:
            conn.close()
