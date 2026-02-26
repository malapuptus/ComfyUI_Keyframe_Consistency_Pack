
from __future__ import annotations

import json
from kcp.db.paths import normalize_db_path, with_projectinit_db_path_tip
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
                "stack_json": ("STRING", {"default": "{}", "multiline": True}),
                "variant_policy_id": ("STRING", {"default": ""}),
                "variant_policy_json": ("STRING", {"default": "{}", "multiline": True}),
                "variant_list_json": ("STRING", {"default": "{}", "multiline": True}),
                "base_seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "width": ("INT", {"default": 1024, "min": 64}),
                "height": ("INT", {"default": 1024, "min": 64}),
                "set_name": ("STRING", {"default": ""}),
                "picked_index": ("INT", {"default": -1, "min": -1, "max": 255}),
                "notes": ("STRING", {"default": ""}),
                "model_ref": ("STRING", {"default": ""}),
                "breakdown_json": ("STRING", {"default": "{}", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("set_id", "item_count", "set_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path, stack_id, stack_json, variant_policy_id, variant_policy_json, variant_list_json, base_seed, width, height, set_name="", picked_index=-1, notes="", model_ref="", breakdown_json="{}"):
        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            policy_payload = parse_json_object(variant_policy_json, default={})
            variants_payload = parse_json_object(variant_list_json, default={})
            stack_payload = parse_json_object(stack_json, default={})
            breakdown_payload = parse_json_object(breakdown_json, default={})
            variants = variants_payload.get("variants", [])

            effective_stack_id = str(stack_id).strip() or str(stack_payload.get("stack_id", "") or stack_payload.get("id", "") or "")

            effective_policy_id = variant_policy_id if str(variant_policy_id).strip() else str(variants_payload.get("policy_id", "") or "")

            # KCP-071: safe derivation from variant payload only when user left defaults.
            first_variant = variants[0] if variants else {}
            first_gp = first_variant.get("gen_params", {}) if isinstance(first_variant, dict) else {}
            derived_base_seed = variants_payload.get("base_seed")
            derived_width = first_gp.get("width") if isinstance(first_gp, dict) else None
            derived_height = first_gp.get("height") if isinstance(first_gp, dict) else None
            if derived_width is None and isinstance(first_variant, dict):
                derived_width = first_variant.get("width")
            if derived_height is None and isinstance(first_variant, dict):
                derived_height = first_variant.get("height")

            effective_base_seed = int(base_seed)
            effective_width = int(width)
            effective_height = int(height)
            if effective_base_seed == 0 and derived_base_seed is not None:
                try:
                    dbs = int(derived_base_seed)
                    if dbs != 0:
                        effective_base_seed = dbs
                except Exception:
                    pass
            if effective_width == 1024 and derived_width is not None:
                try:
                    dw = int(derived_width)
                    if dw != 1024:
                        effective_width = dw
                except Exception:
                    pass
            if effective_height == 1024 and derived_height is not None:
                try:
                    dh = int(derived_height)
                    if dh != 1024:
                        effective_height = dh
                except Exception:
                    pass

            # KCP-072: minimal policy provenance fallback when user left JSON empty.
            if not policy_payload and str(effective_policy_id).strip():
                policy_payload = {"policy_id": str(effective_policy_id).strip()}

            policy_payload = {
                **policy_payload,
                "compose_breakdown": breakdown_payload,
            }

            set_id = create_keyframe_set(
                conn,
                {
                    "name": set_name,
                    "stack_id": effective_stack_id,
                    "variant_policy_id": effective_policy_id,
                    "variant_policy_json": policy_payload,
                    "base_seed": effective_base_seed,
                    "width": effective_width,
                    "height": effective_height,
                    "picked_index": picked_index if picked_index >= 0 else None,
                    "notes": notes,
                    "model_ref": model_ref,
                },
            )
            for i, v in enumerate(variants):
                gp = v.get("gen_params", {})
                add_keyframe_set_item(
                    conn,
                    {
                        "set_id": set_id,
                        "idx": int(v.get("index", i)),
                        "seed": int(gp.get("seed", effective_base_seed + i)),
                        "positive_prompt": v.get("positive", ""),
                        "negative_prompt": v.get("negative", ""),
                        "gen_params_json": gp,
                    },
                )
            return (set_id, len(variants), json.dumps({"set_id": set_id, "item_count": len(variants)}))
        finally:
            conn.close()
