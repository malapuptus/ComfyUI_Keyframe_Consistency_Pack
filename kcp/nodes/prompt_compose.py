from __future__ import annotations

import json


class KCP_PromptCompose:
    ORDER = ["global_rules", "style", "camera", "lighting", "environment", "action", "character"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_fragment": ("STRING", {"default": "", "multiline": True}),
                "environment_fragment": ("STRING", {"default": "", "multiline": True}),
                "action_fragment": ("STRING", {"default": "", "multiline": True}),
                "camera_fragment": ("STRING", {"default": "", "multiline": True}),
                "lighting_fragment": ("STRING", {"default": "", "multiline": True}),
                "style_fragment": ("STRING", {"default": "", "multiline": True}),
                "global_rules": ("STRING", {"default": "", "multiline": True}),
                "negative_base": ("STRING", {"default": "", "multiline": True}),
                "compose_mode": (["concat_strict", "dedupe_light", "newline_blocks", "dedupe_tokens"],),
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

        if compose_mode == "dedupe_tokens":
            seen = set()
            deduped_tokens = []
            for p in ordered:
                for token in p.replace("\n", ",").split(","):
                    t = token.strip()
                    if not t:
                        continue
                    low = t.lower()
                    if low in seen:
                        continue
                    seen.add(low)
                    deduped_tokens.append(t)
            positive = ", ".join(deduped_tokens)
        elif compose_mode == "newline_blocks":
            positive = "\n".join(ordered)
        else:
            positive = ", ".join(ordered)

        negative = negative_base.strip()
        breakdown = {
            "compose_mode": compose_mode,
            "ordering": self.ORDER,
            "fragments": parts,
            "debug": bool(debug),
        }
        return (positive, negative, json.dumps(breakdown))
