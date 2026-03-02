from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from kcp.db.repo import connect


def _parse_picked_indexes(value: str) -> list[int]:
    out: set[int] = set()
    for part in (value or "").split(","):
        p = part.strip()
        if not p:
            continue
        if "-" in p:
            a_str, b_str = p.split("-", 1)
            a = int(a_str.strip())
            b = int(b_str.strip())
            lo, hi = (a, b) if a <= b else (b, a)
            for i in range(lo, hi + 1):
                out.add(i)
        else:
            out.add(int(p))
    return sorted(out)


class KCP_SeedBankSave:
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "seeds": ("INT",),
                "picked_indexes": ("STRING", {"default": "0", "multiline": False}),
                "dedupe_mode": (["seed_plus_context", "seed_only"],),
                "positive_prompt": ("STRING", {"default": "", "multiline": True}),
                "negative_prompt": ("STRING", {"default": "", "multiline": True}),
                "checkpoint": ("STRING", {"default": ""}),
                "sampler": ("STRING", {"default": "euler"}),
                "scheduler": ("STRING", {"default": "normal"}),
                "steps": ("INT", {"default": 20, "min": 1}),
                "cfg": ("FLOAT", {"default": 7.0, "min": 0.0}),
                "width": ("INT", {"default": 1024, "min": 64}),
                "height": ("INT", {"default": 1024, "min": 64}),
                "tags_csv": ("STRING", {"default": "", "multiline": False}),
                "note": ("STRING", {"default": "", "multiline": True}),
                "context_json": ("STRING", {"default": "{}", "multiline": True}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "STRING")
    RETURN_NAMES = ("picked_seeds", "saved_count", "skipped_count", "summary")
    OUTPUT_IS_LIST = (True, False, False, False)
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path, seeds, picked_indexes, dedupe_mode, positive_prompt, negative_prompt, checkpoint, sampler, scheduler, steps, cfg, width, height, tags_csv, note, context_json):
        def _scalar(v):
            if isinstance(v, list):
                return v[0] if v else ""
            return v

        db_path = _scalar(db_path)
        picked_indexes = _scalar(picked_indexes)
        dedupe_mode = _scalar(dedupe_mode)
        positive_prompt = _scalar(positive_prompt)
        negative_prompt = _scalar(negative_prompt)
        checkpoint = _scalar(checkpoint)
        sampler = _scalar(sampler)
        scheduler = _scalar(scheduler)
        steps = _scalar(steps)
        cfg = _scalar(cfg)
        width = _scalar(width)
        height = _scalar(height)
        tags_csv = _scalar(tags_csv)
        note = _scalar(note)
        context_json = _scalar(context_json)

        seed_values = seeds if isinstance(seeds, list) else [seeds]
        if len(seed_values) == 1 and isinstance(seed_values[0], list):
            seed_values = seed_values[0]
        seed_list = [int(s) for s in (seed_values or [])]
        indexes = _parse_picked_indexes(str(picked_indexes))

        oob = [i for i in indexes if i < 0 or i >= len(seed_list)]
        if oob:
            return ([], 0, len(oob), json.dumps({"code": "kcp_seedbank_index_oob", "oob_indexes": oob, "seed_count": len(seed_list)}))

        try:
            context_obj = json.loads(context_json or "{}")
            if not isinstance(context_obj, dict):
                context_obj = {"value": context_obj}
        except Exception:
            context_obj = {}

        prompt_hash = sha256(f"{positive_prompt}\n---\n{negative_prompt}".encode("utf-8")).hexdigest()
        context_hash_raw = sha256(json.dumps(context_obj, sort_keys=True).encode("utf-8")).hexdigest()
        context_hash = "" if dedupe_mode == "seed_only" else context_hash_raw

        picked_seeds = [seed_list[i] for i in indexes]
        saved_count = 0
        skipped_count = 0

        conn = connect(Path(str(db_path).strip()))
        try:
            for seed in picked_seeds:
                cur = conn.execute(
                    """
                    INSERT OR IGNORE INTO seed_bank_entry (
                        seed, created_at, prompt_hash, context_hash,
                        checkpoint, sampler, scheduler, steps, cfg, width, height,
                        positive_prompt, negative_prompt, tags_csv, note, context_json
                    ) VALUES (?, strftime('%s','now')*1000, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(seed),
                        prompt_hash,
                        context_hash,
                        str(checkpoint or ""),
                        str(sampler or ""),
                        str(scheduler or ""),
                        int(steps),
                        float(cfg),
                        int(width),
                        int(height),
                        str(positive_prompt or ""),
                        str(negative_prompt or ""),
                        str(tags_csv or ""),
                        str(note or ""),
                        json.dumps(context_obj, sort_keys=True),
                    ),
                )
                if cur.rowcount == 1:
                    saved_count += 1
                else:
                    skipped_count += 1
            conn.commit()
        finally:
            conn.close()

        summary = {
            "picked": len(picked_seeds),
            "saved_count": saved_count,
            "skipped_count": skipped_count,
            "dedupe_mode": dedupe_mode,
        }
        return (picked_seeds, saved_count, skipped_count, json.dumps(summary))
