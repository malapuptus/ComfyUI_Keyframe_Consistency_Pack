from __future__ import annotations

import json
import random
from hashlib import sha256


def _rng_for(seed: int, reroll: int, field_name: str) -> random.Random:
    key = f"{int(seed)}::{int(reroll)}::{field_name}".encode("utf-8")
    digest = sha256(key).hexdigest()
    return random.Random(int(digest[:16], 16))


def _pick(value: str, choices: list[str], seed: int, reroll: int, field_name: str) -> str:
    if value != "(random)":
        return value
    pool = [x for x in choices if x != "(random)"]
    if not pool:
        return ""
    return pool[_rng_for(seed, reroll, field_name).randrange(len(pool))]


class KCP_EnvironmentForge:
    SCENE_TYPE = ["interior", "exterior"]
    LOCATION = ["(random)", "abandoned library", "neon alley", "mountain lookout", "small apartment kitchen"]
    ERA = ["(random)", "modern day", "near future", "retro 80s", "medieval fantasy"]
    TIME_OF_DAY = ["(random)", "dawn", "midday", "golden hour", "night"]
    WEATHER = ["(random)", "clear", "light rain", "foggy", "overcast"]
    MOOD = ["(random)", "calm", "mysterious", "hopeful", "tense"]
    STYLE_PRESET = ["cinematic realism", "stylized illustration", "anime clean lines", "painterly fantasy"]
    QUALITY_LEVEL = ["minimal", "normal", "high"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scene_type": (cls.SCENE_TYPE,),
                "location": (cls.LOCATION,),
                "era": (cls.ERA,),
                "time_of_day": (cls.TIME_OF_DAY,),
                "weather": (cls.WEATHER,),
                "mood": (cls.MOOD,),
                "no_people": ("BOOLEAN", {"default": True}),
                "no_text_signage": ("BOOLEAN", {"default": True}),
                "style_preset": (cls.STYLE_PRESET,),
                "quality_level": (cls.QUALITY_LEVEL,),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "reroll": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "freeform_addon": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "asset_type",
        "suggested_name",
        "description",
        "positive_fragment",
        "negative_fragment",
        "json_fields",
        "tags_csv",
    )
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, scene_type, location, era, time_of_day, weather, mood, no_people=True, no_text_signage=True, style_preset="cinematic realism", quality_level="normal", seed=0, reroll=0, freeform_addon=""):
        tokens = {
            "scene_type": scene_type,
            "location": _pick(location, self.LOCATION, seed, reroll, "location"),
            "era": _pick(era, self.ERA, seed, reroll, "era"),
            "time_of_day": _pick(time_of_day, self.TIME_OF_DAY, seed, reroll, "time_of_day"),
            "weather": _pick(weather, self.WEATHER, seed, reroll, "weather"),
            "mood": _pick(mood, self.MOOD, seed, reroll, "mood"),
            "style_preset": style_preset,
            "quality_level": quality_level,
            "no_people": bool(no_people),
            "no_text_signage": bool(no_text_signage),
            "seed": int(seed),
            "reroll": int(reroll),
        }

        identity_line = f"{tokens['scene_type']} {tokens['location']}, {tokens['era']}"
        wardrobe_line = f"{tokens['time_of_day']}, {tokens['weather']} weather"
        expression_line = f"{tokens['mood']} atmosphere"
        style_line = tokens["style_preset"]
        quality_line = {
            "minimal": "clean plate composition",
            "normal": "clean plate composition, coherent detail",
            "high": "clean plate composition, coherent detail, high fidelity textures",
        }[quality_level]

        positive_lines = [identity_line, wardrobe_line, expression_line, style_line, quality_line]
        if bool(no_people):
            positive_lines.append("empty scene, no people")
        addon = (freeform_addon or "").strip()
        if addon:
            positive_lines.append(addon)
        positive_fragment = "\n".join(positive_lines)

        negatives = ["blurry", "low quality"]
        if bool(no_people):
            negatives.extend(["people", "person", "crowd", "face"])
        if bool(no_text_signage):
            negatives.extend(["text", "watermark", "logo", "signage"])
        negative_fragment = ", ".join(negatives)

        suggested_name = f"{tokens['scene_type']}_{tokens['location'].replace(' ', '_')}"
        description = f"{tokens['scene_type']} plate: {tokens['location']} ({tokens['mood']})"
        tags_csv = ",".join(["environment", tokens["scene_type"], tokens["mood"], tokens["style_preset"].replace(" ", "-")])

        json_fields = {
            "format_version": "1.0",
            "asset_type": "environment",
            "display": {"name": suggested_name, "description": description},
            "invariants": {
                "provenance": {"node": "KCP_EnvironmentForge", "version": "1", "seed": int(seed), "reroll": int(reroll)},
                "plate_flags": {"no_people": bool(no_people), "no_text_signage": bool(no_text_signage)},
            },
            "variables": {"forge_inputs": tokens},
            "prompt": {
                "positive_fragment": positive_fragment,
                "negative_fragment": negative_fragment,
                "tokens": tokens,
            },
        }

        return ("environment", suggested_name, description, positive_fragment, negative_fragment, json.dumps(json_fields), tags_csv)
