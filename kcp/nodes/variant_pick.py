from __future__ import annotations

import json


class KCP_VariantPick:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "variant_list_json": ("STRING", {"multiline": True, "default": "{}"}),
                "index": ("INT", {"default": 0, "min": 0}),
            }
        }

    RETURN_TYPES = (
        "STRING",
        "STRING",
        "STRING",
        "INT",
        "INT",
        "FLOAT",
        "STRING",
        "STRING",
        "FLOAT",
        "INT",
        "INT",
        "STRING",
    )
    RETURN_NAMES = (
        "label",
        "positive_prompt",
        "negative_prompt",
        "seed",
        "steps",
        "cfg",
        "sampler",
        "scheduler",
        "denoise",
        "width",
        "height",
        "gen_params_json",
    )
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, variant_list_json: str, index: int = 0):
        try:
            payload = json.loads(variant_list_json)
        except Exception as e:
            raise RuntimeError(f"kcp_variant_list_invalid: {e}") from e

        if not isinstance(payload, dict) or "variants" not in payload or not isinstance(payload["variants"], list):
            raise RuntimeError("kcp_variant_list_invalid: expected object with variants array")

        variants = payload["variants"]
        if index < 0 or index >= len(variants):
            raise RuntimeError(f"kcp_variant_index_oob: index={index} variants={len(variants)}")

        variant = variants[index]
        if not isinstance(variant, dict):
            raise RuntimeError("kcp_variant_missing_fields: variant entry must be object")

        required_variant = ["positive", "negative", "gen_params"]
        missing_variant = [k for k in required_variant if k not in variant]
        if missing_variant:
            raise RuntimeError(f"kcp_variant_missing_fields: missing variant fields {', '.join(missing_variant)}")

        gen_params = variant["gen_params"]
        if not isinstance(gen_params, dict):
            raise RuntimeError("kcp_variant_missing_fields: gen_params must be object")

        required_gp = ["seed", "steps", "cfg", "sampler", "scheduler", "denoise", "width", "height"]
        missing_gp = [k for k in required_gp if k not in gen_params]
        if missing_gp:
            raise RuntimeError(f"kcp_variant_missing_fields: missing gen_params fields {', '.join(missing_gp)}")

        label = str(variant.get("label", f"Variant {index}"))
        positive = str(variant["positive"])
        negative = str(variant["negative"])
        seed = int(gen_params["seed"])
        steps = int(gen_params["steps"])
        cfg = float(gen_params["cfg"])
        sampler = str(gen_params["sampler"])
        scheduler = str(gen_params["scheduler"])
        denoise = float(gen_params["denoise"])
        width = int(gen_params["width"])
        height = int(gen_params["height"])

        return (
            label,
            positive,
            negative,
            seed,
            steps,
            cfg,
            sampler,
            scheduler,
            denoise,
            width,
            height,
            json.dumps(gen_params),
        )
