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


class KCP_CharacterForge:
    ARCHETYPE = ["heroic guardian", "street courier", "arcane scholar", "space pilot", "mystery detective"]
    AGE_BAND = ["(random)", "teen", "young adult", "adult", "middle-aged"]
    SKIN_TONE = ["(random)", "fair", "light tan", "medium", "deep", "ebony"]
    HAIR_COLOR = ["(random)", "black", "brown", "blonde", "red", "silver"]
    HAIR_STYLE = ["(random)", "short tidy", "wavy shoulder-length", "curly bob", "braided", "undercut"]
    EYE_COLOR = ["(random)", "brown", "hazel", "green", "blue", "gray"]
    WARDROBE = ["(random)", "casual jacket", "tailored suit", "utility jumpsuit", "fantasy traveler gear"]
    ACCESSORY = ["(random)", "simple pendant", "leather satchel", "wrist device", "fingerless gloves"]
    BODY_TYPE = ["(random)", "slim", "athletic", "average", "broad"]
    STYLE_PRESET = ["cinematic realism", "stylized illustration", "anime clean lines", "painterly fantasy"]
    QUALITY_LEVEL = ["minimal", "normal", "high"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "archetype": (cls.ARCHETYPE,),
                "age_band": (cls.AGE_BAND,),
                "skin_tone": (cls.SKIN_TONE,),
                "hair_color": (cls.HAIR_COLOR,),
                "hair_style": (cls.HAIR_STYLE,),
                "eye_color": (cls.EYE_COLOR,),
                "wardrobe": (cls.WARDROBE,),
                "accessory": (cls.ACCESSORY,),
                "body_type": (cls.BODY_TYPE,),
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

    def run(self, archetype, age_band, skin_tone, hair_color, hair_style, eye_color, wardrobe, accessory, body_type, style_preset, quality_level, seed=0, reroll=0, freeform_addon=""):
        tokens = {
            "archetype": archetype,
            "age_band": _pick(age_band, self.AGE_BAND, seed, reroll, "age_band"),
            "skin_tone": _pick(skin_tone, self.SKIN_TONE, seed, reroll, "skin_tone"),
            "hair_color": _pick(hair_color, self.HAIR_COLOR, seed, reroll, "hair_color"),
            "hair_style": _pick(hair_style, self.HAIR_STYLE, seed, reroll, "hair_style"),
            "eye_color": _pick(eye_color, self.EYE_COLOR, seed, reroll, "eye_color"),
            "wardrobe": _pick(wardrobe, self.WARDROBE, seed, reroll, "wardrobe"),
            "accessory": _pick(accessory, self.ACCESSORY, seed, reroll, "accessory"),
            "body_type": _pick(body_type, self.BODY_TYPE, seed, reroll, "body_type"),
            "style_preset": style_preset,
            "quality_level": quality_level,
            "seed": int(seed),
            "reroll": int(reroll),
        }

        identity_line = (
            f"{tokens['archetype']}, {tokens['age_band']}, {tokens['body_type']} build, "
            f"{tokens['skin_tone']} skin, {tokens['hair_color']} {tokens['hair_style']} hair, {tokens['eye_color']} eyes"
        )
        wardrobe_line = f"wearing {tokens['wardrobe']}, with {tokens['accessory']}"
        expression_line = "calm confident expression, natural relaxed pose"
        style_line = tokens["style_preset"]
        quality_line = {
            "minimal": "clean composition",
            "normal": "clean composition, coherent details",
            "high": "clean composition, coherent details, high fidelity textures",
        }[quality_level]

        positive_lines = [identity_line, wardrobe_line, expression_line, style_line, quality_line]
        addon = (freeform_addon or "").strip()
        if addon:
            positive_lines.append(addon)
        positive_fragment = "\n".join(positive_lines)
        negative_fragment = "blurry, low quality, extra limbs, deformed anatomy"

        suggested_name = f"{tokens['archetype'].replace(' ', '_')}_{tokens['style_preset'].split()[0]}"
        description = f"{tokens['archetype']} character in {tokens['style_preset']} style"
        tags_csv = ",".join(
            [
                "character",
                tokens["archetype"].replace(" ", "-"),
                tokens["style_preset"].replace(" ", "-"),
                tokens["wardrobe"].replace(" ", "-"),
            ]
        )

        json_fields = {
            "format_version": "1.0",
            "asset_type": "character",
            "display": {"name": suggested_name, "description": description},
            "invariants": {
                "provenance": {"node": "KCP_CharacterForge", "version": "1", "seed": int(seed), "reroll": int(reroll)},
            },
            "variables": {"forge_inputs": tokens},
            "prompt": {
                "positive_fragment": positive_fragment,
                "negative_fragment": negative_fragment,
                "tokens": tokens,
            },
        }
        return ("character", suggested_name, description, positive_fragment, negative_fragment, json.dumps(json_fields), tags_csv)
