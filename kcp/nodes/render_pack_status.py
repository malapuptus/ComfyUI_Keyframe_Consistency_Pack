
from __future__ import annotations

import json

from kcp.db.paths import kcp_root_from_db_path, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect


class KCP_RenderPackStatus:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "set_id": ("STRING", {"default": ""}),
                "strict": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("summary_text", "status_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_id: str, strict: bool = False):
        try:
            dbp = normalize_db_path(db_path)
            root = kcp_root_from_db_path(db_path)
            conn = connect(dbp)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e

        try:
            rows = conn.execute("SELECT idx,image_path FROM keyframe_set_items WHERE set_id=? ORDER BY idx", (set_id,)).fetchall()
        finally:
            conn.close()

        total_items = len(rows)
        expected_count = total_items
        items_with_media = 0
        missing_idxs = []
        for row in rows:
            idx = int(row["idx"])
            rel = (row["image_path"] or "").strip()
            exists = bool(rel) and (root / rel).resolve().exists()
            if exists:
                items_with_media += 1
            else:
                missing_idxs.append(idx)

        missing_idxs = sorted(missing_idxs)
        if strict and missing_idxs:
            raise RuntimeError(f"kcp_set_media_missing: set_id={set_id} missing_idxs={missing_idxs}")

        payload = {
            "set_id": set_id,
            "expected_count": expected_count,
            "total_items": total_items,
            "items_with_media": items_with_media,
            "missing_idxs": missing_idxs,
        }
        summary = f"set_id={set_id} total={total_items} saved={items_with_media} missing={len(missing_idxs)}"
        return (summary, json.dumps(payload))
