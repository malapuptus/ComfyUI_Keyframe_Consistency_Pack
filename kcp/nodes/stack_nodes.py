from __future__ import annotations

import json
from kcp.db.paths import normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import connect, get_stack_by_name, list_stack_names, save_stack
from kcp.util.json_utils import parse_json_object


def _safe_stack_choices(db_path: str, include_archived: bool, refresh_token: int) -> list[str]:
    _ = refresh_token
    try:
        dbp = normalize_db_path(db_path)
        if not dbp.exists():
            return [""]
        conn = connect(dbp)
        try:
            names = list_stack_names(conn, include_archived=include_archived)
            return names if names else [""]
        finally:
            conn.close()
    except Exception:
        return [""]


class KCP_StackSave:
    OUTPUT_NODE = True

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
        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
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
    def INPUT_TYPES(
        cls,
        db_path: str = "output/kcp/db/kcp.sqlite",
        include_archived: bool = False,
        refresh_token: int = 0,
        strict: bool = False,
    ):
        choices = _safe_stack_choices(db_path, include_archived, refresh_token)
        return {
            "required": {
                "db_path": ("STRING", {"default": db_path}),
                "stack_name": (choices,),
                "include_archived": ("BOOLEAN", {"default": include_archived}),
                "refresh_token": ("INT", {"default": refresh_token}),
                "strict": ("BOOLEAN", {"default": strict}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "IMAGE", "IMAGE", "STRING")
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
        "warning_json",
    )
    FUNCTION = "run"
    CATEGORY = "KCP"

    @classmethod
    def list_names(cls, db_path: str, include_archived: bool = False, refresh_token: int = 0):
        return _safe_stack_choices(db_path, include_archived, refresh_token)

    def run(self, db_path, stack_name, include_archived=False, refresh_token=0, strict=False):
        _ = refresh_token
        if (stack_name is None or str(stack_name).strip() == "") and not strict:
            return ("", "{}", "", "", "", "", "", "", None, None, json.dumps({"code": "kcp_stack_no_selection"}))

        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            srow = get_stack_by_name(conn, stack_name, include_archived=include_archived)
            if not srow:
                if strict:
                    raise RuntimeError("kcp_stack_not_found")
                return ("", "{}", "", "", "", "", "", "", None, None, json.dumps({"code": "kcp_stack_not_found"}))

            missing_refs = []

            def frag(asset_id: str | None) -> str:
                if not asset_id:
                    return ""
                row = conn.execute("SELECT positive_fragment FROM assets WHERE id = ?", (asset_id,)).fetchone()
                if row is None:
                    missing_refs.append(asset_id)
                return row[0] if row else ""

            slot_ids = {
                "character_id": srow["character_id"],
                "environment_id": srow["environment_id"],
                "action_id": srow["action_id"],
                "camera_id": srow["camera_id"],
                "lighting_id": srow["lighting_id"],
                "style_id": srow["style_id"],
            }
            missing_slot_refs = []
            for slot, asset_id in slot_ids.items():
                if asset_id and conn.execute("SELECT id FROM assets WHERE id = ?", (asset_id,)).fetchone() is None:
                    missing_slot_refs.append({"slot": slot, "asset_id": asset_id})

            if missing_slot_refs and strict:
                first = missing_slot_refs[0]
                raise RuntimeError(f"kcp_stack_ref_missing: slot={first['slot']} asset_id={first['asset_id']}")

            stack_json = {k: srow[k] for k in srow.keys()}
            warning_json = "{}"
            if missing_slot_refs:
                warning_json = json.dumps({"code": "kcp_stack_ref_missing", "missing_refs": missing_slot_refs})
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
                warning_json,
            )
        finally:
            conn.close()
