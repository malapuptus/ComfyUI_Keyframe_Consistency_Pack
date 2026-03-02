from __future__ import annotations

import random
from hashlib import sha256


class KCP_SeedFinderGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["random_unique", "increment_from_base"],),
                "count": ("INT", {"default": 12, "min": 1, "max": 512}),
                "base_seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "min_seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "max_seed": ("INT", {"default": 2147483647, "min": 0, "max": 2147483647}),
                "reroll": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "rng_salt": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("seeds", "seed_labels", "seed_text")
    OUTPUT_IS_LIST = (True, True, False)
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, mode, count, base_seed, min_seed, max_seed, reroll=0, rng_salt=""):
        n = int(count)
        lo = int(min_seed)
        hi = int(max_seed)
        if hi < lo:
            lo, hi = hi, lo

        seeds: list[int] = []
        if mode == "increment_from_base":
            seeds = [int(base_seed) + i for i in range(n)]
        else:
            span = (hi - lo) + 1
            if n > span:
                raise RuntimeError(f"kcp_seedfinder_range_too_small: count={n} range_size={span}")
            token = f"{int(base_seed)}::{int(reroll)}::{str(rng_salt)}::{mode}".encode("utf-8")
            rng = random.Random(int(sha256(token).hexdigest()[:16], 16))
            seeds = rng.sample(range(lo, hi + 1), n)

        labels = [f"[{i}] seed={s}" for i, s in enumerate(seeds)]
        seed_text = "\n".join(labels)
        return (seeds, labels, seed_text)
