from __future__ import annotations

import json
from pathlib import Path

from kcp.db.repo import add_keyframe_set_item, connect, create_keyframe_set
from kcp.util.json_utils import parse_json_object


class KCP_KeyframeSetSave:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "stack_id": ("STRING", {"default": ""}),
                "variant_policy_id": ("STRING", {"default": ""}),
                "variant_policy_json": ("STRING", {"default": "{}", "multiline": True}),
                "variant_list_json": ("STRING", {"default": "{}", "multiline": True}),
                "base_seed": ("INT", {"default": 0}),
                "width": ("INT", {"default": 1024}),
                "height": ("INT", {"default": 1024}),
                "set_name": ("STRING", {"default": ""}),
                "picked_index": ("INT", {"default": -1}),
                "notes": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("set_id", "item_count", "set_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path, stack_id, variant_policy_id, variant_policy_json, variant_list_json, base_seed, width, height, set_name="", picked_index=-1, notes=""):
        conn = connect(Path(db_path))
        try:
            policy_payload = parse_json_object(variant_policy_json, default={})
            variants_payload = parse_json_object(variant_list_json, default={})
            variants = variants_payload.get("variants", [])

            set_id = create_keyframe_set(
                conn,
                {
                    "name": set_name,
                    "stack_id": stack_id,
                    "variant_policy_id": variant_policy_id,
                    "variant_policy_json": policy_payload,
                    "base_seed": base_seed,
                    "width": width,
                    "height": height,
                    "picked_index": picked_index if picked_index >= 0 else None,
                    "notes": notes,
                },
            )
            for i, v in enumerate(variants):
                gp = v.get("gen_params", {})
                add_keyframe_set_item(
                    conn,
                    {
                        "set_id": set_id,
                        "idx": int(v.get("index", i)),
                        "seed": int(gp.get("seed", base_seed + i)),
                        "positive_prompt": v.get("positive", ""),
                        "negative_prompt": v.get("negative", ""),
                        "gen_params_json": gp,
                    },
                )
            return (set_id, len(variants), json.dumps({"set_id": set_id, "item_count": len(variants)}))
        finally:
            conn.close()
