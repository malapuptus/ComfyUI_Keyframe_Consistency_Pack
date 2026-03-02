from __future__ import annotations

import json
import random
from hashlib import sha256
from pathlib import Path

from kcp.db.repo import connect


class KCP_SeedBankQuery:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "query_mode": (["latest", "by_tags_any", "by_tags_all", "by_prompt_hash", "by_checkpoint"],),
                "query_text": ("STRING", {"default": "", "multiline": False}),
                "limit": ("INT", {"default": 12, "min": 1, "max": 512}),
                "randomize": ("BOOLEAN", {"default": False}),
                "rng_salt": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("seeds", "seed_labels", "seed_text")
    OUTPUT_IS_LIST = (True, True, False)
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path, query_mode, query_text="", limit=12, randomize=False, rng_salt=""):
        conn = connect(Path(str(db_path).strip()))
        try:
            rows = conn.execute(
                "SELECT seed, checkpoint, tags_csv, prompt_hash, created_at FROM seed_bank_entry ORDER BY created_at DESC, id DESC"
            ).fetchall()
        finally:
            conn.close()

        text = str(query_text or "").strip()
        if query_mode == "by_prompt_hash":
            rows = [r for r in rows if str(r["prompt_hash"]) == text]
        elif query_mode == "by_checkpoint":
            rows = [r for r in rows if str(r["checkpoint"]) == text]
        elif query_mode in ("by_tags_any", "by_tags_all"):
            needles = [t.strip().lower() for t in text.split(",") if t.strip()]
            filtered = []
            for r in rows:
                tags = [t.strip().lower() for t in str(r["tags_csv"] or "").split(",") if t.strip()]
                tag_set = set(tags)
                if query_mode == "by_tags_any" and any(n in tag_set for n in needles):
                    filtered.append(r)
                if query_mode == "by_tags_all" and all(n in tag_set for n in needles):
                    filtered.append(r)
            rows = filtered

        rows = rows[: int(limit)]
        if bool(randomize) and len(rows) > 1:
            token = sha256(f"{query_mode}::{text}::{rng_salt}".encode("utf-8")).hexdigest()
            rng = random.Random(int(token[:16], 16))
            rng.shuffle(rows)

        seeds = [int(r["seed"]) for r in rows]
        labels = [f"seed={int(r['seed'])} ckpt={str(r['checkpoint'])}" for r in rows]
        seed_text = "\n".join([f"[{i}] {labels[i]}" for i in range(len(labels))])
        return (seeds, labels, seed_text)
