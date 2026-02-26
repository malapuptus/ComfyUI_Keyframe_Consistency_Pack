from __future__ import annotations

import json

from kcp.util.json_utils import parse_json_object


class KCP_VariantUnroll:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "variant_list_json": ("STRING", {"default": "{}", "multiline": True}),
            }
        }

    RETURN_TYPES = ("INT", "STRING", "STRING", "INT", "INT", "FLOAT", "SAMPLER_NAME", "SCHEDULER", "FLOAT", "INT", "INT", "STRING")
    RETURN_NAMES = (
        "idx_list",
        "positive_list",
        "negative_list",
        "seed_list",
        "steps_list",
        "cfg_list",
        "sampler_list",
        "scheduler_list",
        "denoise_list",
        "width_list",
        "height_list",
        "gen_params_json_list",
    )
    OUTPUT_IS_LIST = (True, True, True, True, True, True, True, True, True, True, True, True)
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, variant_list_json: str):
        payload = parse_json_object(variant_list_json, default={})
        variants = payload.get("variants", []) if isinstance(payload, dict) else []

        idx_list = []
        positive_list = []
        negative_list = []
        seed_list = []
        steps_list = []
        cfg_list = []
        sampler_list = []
        scheduler_list = []
        denoise_list = []
        width_list = []
        height_list = []
        gen_params_json_list = []

        for i, variant in enumerate(variants):
            v = variant if isinstance(variant, dict) else {}
            gp = v.get("gen_params", {})
            gp = gp if isinstance(gp, dict) else {}
            idx_list.append(int(v.get("index", i)))
            positive_list.append(str(v.get("positive", "")))
            negative_list.append(str(v.get("negative", "")))
            seed_list.append(int(gp.get("seed", 0)))
            steps_list.append(int(gp.get("steps", 20)))
            cfg_list.append(float(gp.get("cfg", 7.0)))
            sampler_list.append(str(gp.get("sampler", "euler")))
            scheduler_list.append(str(gp.get("scheduler", "normal")))
            denoise_list.append(float(gp.get("denoise", 1.0)))
            width_list.append(int(gp.get("width", 1024)))
            height_list.append(int(gp.get("height", 1024)))
            gen_params_json_list.append(json.dumps(gp))

        return (
            idx_list,
            positive_list,
            negative_list,
            seed_list,
            steps_list,
            cfg_list,
            sampler_list,
            scheduler_list,
            denoise_list,
            width_list,
            height_list,
            gen_params_json_list,
        )
