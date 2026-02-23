from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_json_object(raw: str | None, default: dict | None = None) -> dict:
    if raw is None or raw.strip() == "":
        return default or {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def parse_json_array(raw: str | None, default: list | None = None) -> list:
    if raw is None or raw.strip() == "":
        return default or []
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("expected JSON array")
    return value


def _expect_type(name: str, value: Any, expected: tuple[type, ...]) -> None:
    if not isinstance(value, expected):
        wanted = "/".join(t.__name__ for t in expected)
        raise ValueError(f"{name} must be {wanted}")


def validate_asset_json_fields(raw: str | None) -> dict:
    """Strict v1 validation for `assets.json_fields` against asset schema contract.

    This is an explicit validator using stdlib only.
    """
    if raw is None or raw.strip() == "":
        return {}

    payload = parse_json_object(raw, default={})

    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "asset.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    required = set(schema.get("required", []))
    allowed = set(schema.get("properties", {}).keys())

    missing = sorted(required - set(payload.keys()))
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    extra = sorted(set(payload.keys()) - allowed)
    if extra:
        raise ValueError(f"unknown fields: {', '.join(extra)}")

    _expect_type("format_version", payload.get("format_version"), (str,))
    if payload["format_version"] != "1.0":
        raise ValueError("format_version must be '1.0'")

    _expect_type("asset_type", payload.get("asset_type"), (str,))
    asset_types = schema["properties"]["asset_type"]["enum"]
    if payload["asset_type"] not in asset_types:
        raise ValueError(f"asset_type must be one of: {', '.join(asset_types)}")

    _expect_type("invariants", payload.get("invariants"), (dict,))
    _expect_type("variables", payload.get("variables"), (dict,))

    prompt = payload.get("prompt")
    _expect_type("prompt", prompt, (dict,))
    prompt_required = {"positive_fragment", "negative_fragment", "tokens"}
    pmissing = sorted(prompt_required - set(prompt.keys()))
    if pmissing:
        raise ValueError(f"prompt missing required fields: {', '.join(pmissing)}")
    pextra = sorted(set(prompt.keys()) - prompt_required)
    if pextra:
        raise ValueError(f"prompt has unknown fields: {', '.join(pextra)}")

    _expect_type("prompt.positive_fragment", prompt.get("positive_fragment"), (str,))
    _expect_type("prompt.negative_fragment", prompt.get("negative_fragment"), (str,))
    _expect_type("prompt.tokens", prompt.get("tokens"), (dict,))

    if "display" in payload:
        display = payload["display"]
        _expect_type("display", display, (dict,))
        allowed_display = {"name", "description"}
        dextra = sorted(set(display.keys()) - allowed_display)
        if dextra:
            raise ValueError(f"display has unknown fields: {', '.join(dextra)}")
        if "name" in display:
            _expect_type("display.name", display["name"], (str,))
        if "description" in display:
            _expect_type("display.description", display["description"], (str,))

    if "references" in payload:
        refs = payload["references"]
        _expect_type("references", refs, (dict,))
        allowed_refs = {"image_paths", "pose_id", "mask_id", "control_guide_id"}
        rextra = sorted(set(refs.keys()) - allowed_refs)
        if rextra:
            raise ValueError(f"references has unknown fields: {', '.join(rextra)}")
        if "image_paths" in refs:
            _expect_type("references.image_paths", refs["image_paths"], (list,))
            for i, p in enumerate(refs["image_paths"]):
                _expect_type(f"references.image_paths[{i}]", p, (str,))
        for key in ("pose_id", "mask_id", "control_guide_id"):
            if key in refs:
                _expect_type(f"references.{key}", refs[key], (str,))

    return payload
