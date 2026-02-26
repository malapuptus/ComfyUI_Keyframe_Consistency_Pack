from __future__ import annotations

import json

from kcp.db.paths import DEFAULT_DB_PATH_INPUT, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect


def _safe_item_choices(db_path: str, set_id: str, only_with_media: bool, refresh_token: int) -> list[str]:
    _ = refresh_token
    if not (set_id or "").strip():
        return [""]
    try:
        dbp = normalize_db_path(db_path)
        if not dbp.exists():
            return [""]
        conn = connect(dbp)
        try:
            rows = conn.execute("SELECT idx,seed,image_path FROM keyframe_set_items WHERE set_id=? ORDER BY idx", (set_id,)).fetchall()
            choices = []
            for r in rows:
                has_media = bool((r["image_path"] or "").strip())
                if only_with_media and not has_media:
                    continue
                seed = int(r["seed"]) if r["seed"] is not None else 0
                label = f"idx={int(r['idx'])} [{'saved' if has_media else 'missing'}] seed={seed}"
                choices.append(label)
            return choices or [""]
        finally:
            conn.close()
    except Exception:
        return [""]


class KCP_KeyframeSetItemPick:
    @classmethod
    def INPUT_TYPES(
        cls,
        db_path: str = DEFAULT_DB_PATH_INPUT,
        set_id: str = "",
        only_with_media: bool = True,
        refresh_token: int = 0,
        strict: bool = False,
    ):
        effective_db_path = str(db_path).strip() or DEFAULT_DB_PATH_INPUT
        choices = _safe_item_choices(effective_db_path, set_id, only_with_media, refresh_token)
        return {
            "required": {
                "db_path": ("STRING", {"default": effective_db_path}),
                "set_id": ("STRING", {"default": set_id}),
                "item_choice": (choices,),
                "only_with_media": ("BOOLEAN", {"default": only_with_media}),
                "refresh_token": ("INT", {"default": refresh_token}),
                "strict": ("BOOLEAN", {"default": strict}),
            }
        }

    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("idx", "item_json", "warning_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_id: str, item_choice: str, only_with_media: bool = True, refresh_token: int = 0, strict: bool = False):
        _ = only_with_media, refresh_token
        if not (item_choice or "").strip():
            if strict:
                raise RuntimeError("kcp_set_item_not_found")
            return (-1, "{}", json.dumps({"code": "kcp_set_item_no_selection", "set_id": set_id}))

        try:
            raw = str(item_choice).strip()
            if raw.startswith("idx="):
                idx = int(raw.split(" ", 1)[0].split("=", 1)[1])
            else:
                idx = int(raw.split(" ", 1)[0].strip())
        except Exception:
            if strict:
                raise RuntimeError("kcp_set_item_not_found")
            return (-1, "{}", json.dumps({"code": "kcp_set_item_not_found", "set_id": set_id}))

        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            row = conn.execute("SELECT * FROM keyframe_set_items WHERE set_id=? AND idx=?", (set_id, idx)).fetchone()
            if row is None:
                if strict:
                    raise RuntimeError("kcp_set_item_not_found")
                return (-1, "{}", json.dumps({"code": "kcp_set_item_not_found", "set_id": set_id, "idx": idx}))
            payload = {k: row[k] for k in row.keys()}
            return (idx, json.dumps(payload), "{}")
        finally:
            conn.close()
