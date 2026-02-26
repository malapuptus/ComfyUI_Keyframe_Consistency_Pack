
from __future__ import annotations

import json
from datetime import datetime, timezone

from kcp.db.paths import DEFAULT_DB_PATH_INPUT, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect


def _fmt_created_at(ms: int | None) -> str:
    if ms is None:
        return ""
    try:
        return datetime.fromtimestamp(int(ms) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return str(ms)


def _safe_set_choices(db_path: str, refresh_token: int) -> list[str]:
    _ = refresh_token
    try:
        dbp = normalize_db_path(db_path)
        if not dbp.exists():
            return [""]
        conn = connect(dbp)
        try:
            rows = conn.execute("SELECT id,name,created_at FROM keyframe_sets ORDER BY created_at DESC, id DESC").fetchall()
            choices: list[str] = [""]
            for r in rows:
                created = _fmt_created_at(r["created_at"])
                name = (r["name"] or "").strip()
                label = f"{r['id']} | {created}"
                if name:
                    label = f"{label} | {name}"
                choices.append(label)
            return choices
        finally:
            conn.close()
    except Exception:
        return [""]


class KCP_KeyframeSetPick:
    @classmethod
    def INPUT_TYPES(
        cls,
        db_path: str = DEFAULT_DB_PATH_INPUT,
        refresh_token: int = 0,
        strict: bool = False,
    ):
        effective_db_path = str(db_path).strip() or DEFAULT_DB_PATH_INPUT
        choices = _safe_set_choices(effective_db_path, refresh_token)
        return {
            "required": {
                "db_path": ("STRING", {"default": effective_db_path}),
                "set_choice": (choices,),
                "refresh_token": ("INT", {"default": refresh_token}),
                "strict": ("BOOLEAN", {"default": strict}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("set_id", "set_json", "warning_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path: str, set_choice: str, refresh_token: int = 0, strict: bool = False):
        _ = refresh_token
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
