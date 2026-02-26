from __future__ import annotations

import copy
import json

from kcp.policies.builtin import BUILTIN_POLICIES


def available_policy_ids() -> list[str]:
    return sorted(BUILTIN_POLICIES.keys())


def get_policy(policy_id: str) -> dict:
    if policy_id not in BUILTIN_POLICIES:
        raise ValueError(f"unknown policy_id: {policy_id}")
    return copy.deepcopy(BUILTIN_POLICIES[policy_id])


def build_variants(
    *,
    positive_prompt: str,
    negative_prompt: str,
    policy_id: str,
    count: int,
    base_seed: int,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler: str,
    scheduler: str,
    denoise: float,
    policy_overrides: dict | None = None,
) -> dict:
    policy = get_policy(policy_id)
    overrides = policy_overrides or {}
    injections = policy["injections"]
    default_count = min(len(injections), policy.get("default_count", len(injections)))
    final_count = max(1, min(count or default_count, len(injections)))

    variants = []
    for i in range(final_count):
        inj = injections[i]
        text = inj.get("text", "").strip()
        variant_positive = positive_prompt.strip()
        if text:
            variant_positive = f"{variant_positive}, {text}" if variant_positive else text

        seed = int(base_seed) + i
        variants.append(
            {
                "index": i,
                "label": inj.get("label", f"Variant {i}"),
                "positive": variant_positive,
                "negative": negative_prompt,
                "gen_params": {
                    "seed": seed,
                    "steps": int(overrides.get("steps", steps)),
                    "cfg": float(overrides.get("cfg", cfg)),
                    "sampler": overrides.get("sampler", sampler),
                    "scheduler": overrides.get("scheduler", scheduler),
                    "denoise": float(overrides.get("denoise", denoise)),
                    "width": int(overrides.get("width", width)),
                    "height": int(overrides.get("height", height)),
                },
            }
        )

    return {
        "format_version": "1.0",
        "policy_id": policy_id,
        "base_seed": int(base_seed),
        "variants": variants,
    }


def build_variant_json(**kwargs) -> str:
    return json.dumps(build_variants(**kwargs), ensure_ascii=False)
