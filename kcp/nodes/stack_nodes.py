from __future__ import annotations

import json
from pathlib import Path

from kcp.db.repo import connect, get_stack_by_name, list_stack_names, save_stack
from kcp.util.json_utils import parse_json_object


class KCP_StackSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "stack_name": ("STRING", {"default": ""}),
                "character_id": ("STRING", {"default": ""}),
                "environment_id": ("STRING", {"default": ""}),
                "action_id": ("STRING", {"default": ""}),
                "camera_id": ("STRING", {"default": ""}),
                "lighting_id": ("STRING", {"default": ""}),
                "style_id": ("STRING", {"default": ""}),
                "json_overrides": ("STRING", {"default": "{}", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("stack_id", "stack_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path, stack_name, character_id, environment_id, action_id, camera_id, lighting_id, style_id, json_overrides):
        conn = connect(Path(db_path))
        try:
            stack_id = save_stack(
                conn,
                {
                    "name": stack_name,
                    "character_id": character_id or None,
                    "environment_id": environment_id or None,
                    "action_id": action_id or None,
                    "camera_id": camera_id or None,
                    "lighting_id": lighting_id or None,
                    "style_id": style_id or None,
                    "json_overrides": parse_json_object(json_overrides, default={}),
                },
            )
            return (
                stack_id,
                json.dumps({"id": stack_id, "name": stack_name}),
            )
        except Exception as e:
            raise RuntimeError(f"kcp_stack_ref_invalid: {e}") from e
        finally:
            conn.close()


class KCP_StackPick:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "stack_name": ("STRING", {"default": ""}),
                "include_archived": ("BOOLEAN", {"default": False}),
                "refresh_token": ("INT", {"default": 0}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = (
        "stack_id",
        "stack_json",
        "character_fragment",
        "environment_fragment",
        "action_fragment",
        "camera_fragment",
        "lighting_fragment",
        "style_fragment",
        "environment_thumb",
        "character_thumb",
    )
    FUNCTION = "run"
    CATEGORY = "KCP"

    @classmethod
    def list_names(cls, db_path: str, include_archived: bool = False, refresh_token: int = 0):
        _ = refresh_token
        conn = connect(Path(db_path))
        try:
            return list_stack_names(conn, include_archived=include_archived)
        finally:
            conn.close()

    def run(self, db_path, stack_name, include_archived=False, refresh_token=0):
        _ = refresh_token
        conn = connect(Path(db_path))
        try:
            srow = get_stack_by_name(conn, stack_name, include_archived=include_archived)
            if not srow:
                raise RuntimeError("kcp_stack_not_found")

            def frag(asset_id: str | None) -> str:
                if not asset_id:
                    return ""
                row = conn.execute("SELECT positive_fragment FROM assets WHERE id = ?", (asset_id,)).fetchone()
                return row[0] if row else ""

            stack_json = {k: srow[k] for k in srow.keys()}
            return (
                srow["id"],
                json.dumps(stack_json),
                frag(srow["character_id"]),
                frag(srow["environment_id"]),
                frag(srow["action_id"]),
                frag(srow["camera_id"]),
                frag(srow["lighting_id"]),
                frag(srow["style_id"]),
                None,
                None,
            )
        finally:
            conn.close()
