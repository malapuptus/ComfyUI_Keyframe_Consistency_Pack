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
            picked = set_row["picked_index"]
            stack_id = set_row["stack_id"]
            variant_policy_id = set_row["variant_policy_id"]
            summary_text = (
                f"set_id={set_id} stack_id={stack_id} variant_policy_id={variant_policy_id} "
                f"item_count={int(total)} picked_index={picked}"
            )
            payload = {
                "set_id": set_id,
                "total_items": int(total),
                "picked_index": picked,
                "variant_policy_id": variant_policy_id,
                "stack_id": stack_id,
            }
            return (summary_text, json.dumps(payload))
        finally:
            conn.close()
