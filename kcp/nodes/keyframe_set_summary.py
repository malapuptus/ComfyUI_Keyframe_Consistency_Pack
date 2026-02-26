from __future__ import annotations

import json

from kcp.db.paths import normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect


class KCP_KeyframeSetSummary:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("summary_text", "status_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_id: str):
        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            set_row = conn.execute("SELECT * FROM keyframe_sets WHERE id=?", (set_id,)).fetchone()
            if set_row is None:
                raise RuntimeError("kcp_set_not_found")
            total = conn.execute("SELECT COUNT(*) FROM keyframe_set_items WHERE set_id=?", (set_id,)).fetchone()[0]
            saved = conn.execute(
                "SELECT COUNT(*) FROM keyframe_set_items WHERE set_id=? AND COALESCE(TRIM(image_path),'')<>''",
                (set_id,),
            ).fetchone()[0]
            picked = set_row["picked_index"]
            summary_text = f"{int(total)} items, {int(saved)} saved media, picked={picked}"
            payload = {
                "set_id": set_id,
                "total_items": int(total),
                "saved_media_items": int(saved),
                "picked_index": picked,
            }
            return (summary_text, json.dumps(payload))
        finally:
            conn.close()
