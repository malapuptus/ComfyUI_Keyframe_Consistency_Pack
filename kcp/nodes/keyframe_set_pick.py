from __future__ import annotations

import json

from kcp.db.paths import DEFAULT_DB_PATH_INPUT, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect


def _safe_set_choices(db_path: str, include_empty: bool, refresh_token: int) -> list[str]:
    _ = refresh_token
    choices = [""] if include_empty else []
    try:
        dbp = normalize_db_path(db_path)
        if not dbp.exists():
            return choices or [""]
        conn = connect(dbp)
        try:
            rows = conn.execute("SELECT id,name FROM keyframe_sets ORDER BY created_at DESC, id DESC").fetchall()
            for r in rows:
                label = str(r["id"])
                if (r["name"] or "").strip():
                    label = f"{r['id']} | {r['name']}"
                choices.append(label)
            return choices or [""]
        finally:
            conn.close()
    except Exception:
        return choices or [""]


class KCP_KeyframeSetPick:
    @classmethod
    def INPUT_TYPES(
        cls,
        db_path: str = DEFAULT_DB_PATH_INPUT,
        include_empty: bool = False,
        refresh_token: int = 0,
        strict: bool = False,
    ):
        effective_db_path = str(db_path).strip() or DEFAULT_DB_PATH_INPUT
        choices = _safe_set_choices(effective_db_path, include_empty, refresh_token)
        return {
            "required": {
                "db_path": ("STRING", {"default": effective_db_path}),
                "set_choice": (choices,),
                "include_empty": ("BOOLEAN", {"default": include_empty}),
                "refresh_token": ("INT", {"default": refresh_token}),
                "strict": ("BOOLEAN", {"default": strict}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("set_id", "set_json", "warning_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_choice: str, include_empty: bool = False, refresh_token: int = 0, strict: bool = False):
        _ = include_empty, refresh_token
        if not (set_choice or "").strip():
            if strict:
                raise RuntimeError("kcp_set_not_found")
            return ("", "{}", json.dumps({"code": "kcp_set_no_selection"}))

        set_id = str(set_choice).split("|", 1)[0].strip()
        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            row = conn.execute("SELECT * FROM keyframe_sets WHERE id=?", (set_id,)).fetchone()
            if row is None:
                if strict:
                    raise RuntimeError("kcp_set_not_found")
                return ("", "{}", json.dumps({"code": "kcp_set_not_found", "set_id": set_id}))
            payload = {k: row[k] for k in row.keys()}
            return (set_id, json.dumps(payload), "{}")
        finally:
            conn.close()
