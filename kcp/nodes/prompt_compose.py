from __future__ import annotations

import json


class KCP_PromptCompose:
    ORDER = ["global_rules", "style", "camera", "lighting", "environment", "action", "character"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_fragment": ("STRING", {"default": ""}),
                "environment_fragment": ("STRING", {"default": ""}),
                "action_fragment": ("STRING", {"default": ""}),
                "camera_fragment": ("STRING", {"default": ""}),
                "lighting_fragment": ("STRING", {"default": ""}),
                "style_fragment": ("STRING", {"default": ""}),
                "global_rules": ("STRING", {"default": ""}),
                "negative_base": ("STRING", {"default": ""}),
                "compose_mode": (["concat_strict", "dedupe_light"],),
                "debug": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "breakdown_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, character_fragment, environment_fragment, action_fragment, camera_fragment, lighting_fragment, style_fragment, global_rules, negative_base, compose_mode, debug):
        parts = {
            "global_rules": global_rules.strip(),
            "style": style_fragment.strip(),
            "camera": camera_fragment.strip(),
            "lighting": lighting_fragment.strip(),
            "environment": environment_fragment.strip(),
            "action": action_fragment.strip(),
            "character": character_fragment.strip(),
        }
        ordered = [parts[k] for k in self.ORDER if parts[k]]
        if compose_mode == "dedupe_light":
            seen = set()
            deduped = []
            for p in ordered:
                low = p.lower()
                if low not in seen:
                    seen.add(low)
                    deduped.append(p)
            ordered = deduped

        positive = ", ".join(ordered)
        negative = negative_base.strip()
        breakdown = {
            "compose_mode": compose_mode,
            "ordering": self.ORDER,
            "fragments": parts,
            "debug": bool(debug),
        }
        return (positive, negative, json.dumps(breakdown))
