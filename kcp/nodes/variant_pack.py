from __future__ import annotations

import json

from kcp.policies.engine import available_policy_ids, build_variants
from kcp.util.json_utils import parse_json_object


class KCP_VariantPack:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive_prompt": ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "variant_policy_id": (available_policy_ids(),),
                "count": ("INT", {"default": 12, "min": 1, "max": 256}),
                "base_seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "seed_mode": (["increment", "fixed", "hash_label", "policy_default"],),
                "width": ("INT", {"default": 1024, "min": 64}),
                "height": ("INT", {"default": 1024, "min": 64}),
                "steps": ("INT", {"default": 26, "min": 1}),
                "cfg": ("FLOAT", {"default": 6.0, "min": 0.0}),
                "sampler": ("STRING", {"default": "euler"}),
                "scheduler": ("STRING", {"default": "normal"}),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0}),
                "policy_overrides_json": ("STRING", {"default": "{}", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("variant_list_json", "set_preview_text")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, positive_prompt, negative_prompt, variant_policy_id, count, base_seed, seed_mode, width, height, steps, cfg, sampler, scheduler, denoise, policy_overrides_json):
        payload = build_variants(
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            policy_id=variant_policy_id,
            count=count,
            base_seed=base_seed,
            seed_mode=seed_mode,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            denoise=denoise,
            policy_overrides=parse_json_object(policy_overrides_json, default={}),
        )
        preview = "\n".join([f"[{v['index']}] {v.get('label', '')}" for v in payload["variants"]])
        return (json.dumps(payload), preview)
