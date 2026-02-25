from __future__ import annotations

import json
import sqlite3
from kcp.db.paths import kcp_root_from_db_path, normalize_db_path, with_projectinit_db_path_tip
from kcp.db.repo import (
    ASSET_TYPES,
    connect,
    create_asset,
    create_asset_version,
    get_asset_by_type_name,
    list_asset_names,
    update_asset_by_id,
)
from kcp.util.hashing import sha256_file
from kcp.util.image_io import load_image_as_comfy, make_thumbnail, pillow_available, save_optional_image
from kcp.util.json_utils import validate_asset_json_fields


def _safe_asset_choices(db_path: str, asset_type: str, include_archived: bool, refresh_token: int) -> list[str]:
    _ = refresh_token
    try:
        dbp = normalize_db_path(db_path)
        if not dbp.exists():
            return [""]
        conn = connect(dbp)
        try:
            names = list_asset_names(conn, asset_type, include_archived=include_archived)
            return names if names else [""]
        finally:
            conn.close()
    except Exception:
        return [""]


class KCP_AssetSave:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "asset_type": (sorted(ASSET_TYPES),),
                "name": ("STRING", {"default": ""}),
                "description": ("STRING", {"default": ""}),
                "positive_fragment": ("STRING", {"multiline": True, "default": ""}),
                "negative_fragment": ("STRING", {"multiline": True, "default": ""}),
                "json_fields": ("STRING", {"multiline": True, "default": ""}),
                "tags_csv": ("STRING", {"default": ""}),
                "save_mode": (["new", "new_version_of_name", "overwrite_by_name"],),
            },
            "optional": {"image": ("IMAGE",)},
        }

    RETURN_TYPES = ("STRING", "IMAGE", "STRING")
    RETURN_NAMES = ("asset_id", "thumb_image", "asset_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path, asset_type, name, description, positive_fragment, negative_fragment, json_fields, tags_csv, save_mode, image=None):
        if asset_type not in ASSET_TYPES:
            raise RuntimeError("kcp_asset_validation_failed: invalid asset_type")

        try:
            parsed_json = validate_asset_json_fields(json_fields) if (json_fields and json_fields.strip()) else {}
        except Exception as e:
            raise RuntimeError(f"kcp_asset_validation_failed: {e}") from e

        tags = [t.strip() for t in tags_csv.split(",") if t.strip()]
        try:
            dbp = normalize_db_path(db_path)
            root = dbp.parent.parent
            conn = connect(dbp)
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        warnings = []
        thumb_image_out = image
        try:
            existing = get_asset_by_type_name(conn, asset_type, name, include_archived=True)
            if existing and save_mode == "new":
                raise RuntimeError("kcp_asset_name_conflict: type+name already exists")

            effective_name = name
            if existing and save_mode == "new_version_of_name":
                effective_name = f"{name}__v{int(existing['version']) + 1}"
                warnings.append(f"name adjusted to {effective_name} to satisfy UNIQUE(type,name)")

            if existing and save_mode == "overwrite_by_name":
                asset_id = existing["id"]
            else:
                if existing and save_mode == "new_version_of_name":
                    asset_id = create_asset_version(
                        conn,
                        existing,
                        effective_name,
                        description=description,
                        tags=tags,
                        positive_fragment=positive_fragment,
                        negative_fragment=negative_fragment,
                        json_fields=parsed_json,
                    )
                else:
                    asset_id = create_asset(
                        conn,
                        {
                            "type": asset_type,
                            "name": effective_name,
                            "description": description,
                            "tags": tags,
                            "positive_fragment": positive_fragment,
                            "negative_fragment": negative_fragment,
                            "json_fields": parsed_json,
                            "version": 1,
                            "parent_id": None,
                        },
                    )

            image_rel = ""
            thumb_rel = ""
            image_hash = ""
            if image is not None:
                if not pillow_available():
                    raise RuntimeError("kcp_io_write_failed: Pillow required to save IMAGE input; install with pip install pillow")

                image_path = root / "images" / asset_type / asset_id / "original.png"
                if not save_optional_image(image, image_path, fmt="PNG"):
                    raise RuntimeError("kcp_io_write_failed: failed to save IMAGE input")

                image_rel = str(image_path.relative_to(root))
                image_hash = sha256_file(image_path)
                thumb_path = root / "thumbs" / asset_type / asset_id / "thumb.webp"
                try:
                    if make_thumbnail(image_path, thumb_path, max_px=384):
                        thumb_rel = str(thumb_path.relative_to(root))
                        thumb_image_out = load_image_as_comfy(thumb_path)
                    else:
                        warnings.append("thumbnail generation failed; saved original image without thumbnail")
                except Exception:
                    warnings.append("thumbnail generation failed; saved original image without thumbnail")
            elif asset_type == "environment":
                warnings.append("environment asset saved without plate image; plate-lock workflows will be blocked")

            if existing and save_mode == "overwrite_by_name":
                update_asset_by_id(
                    conn,
                    asset_id,
                    description=description,
                    tags=tags,
                    positive_fragment=positive_fragment,
                    negative_fragment=negative_fragment,
                    json_fields=parsed_json,
                    image_path=image_rel,
                    thumb_path=thumb_rel,
                    image_hash=image_hash,
                )
            elif image is not None:
                conn.execute(
                    "UPDATE assets SET image_path=?, thumb_path=?, image_hash=? WHERE id=?",
                    (image_rel, thumb_rel, image_hash, asset_id),
                )
                conn.commit()

            out = {
                "asset_id": asset_id,
                "type": asset_type,
                "name": effective_name,
                "warnings": warnings,
                "image_path": image_rel,
                "thumb_path": thumb_rel,
            }
            return (asset_id, thumb_image_out, json.dumps(out))
        except sqlite3.IntegrityError as e:
            raise RuntimeError(f"kcp_asset_name_conflict: {e}") from e
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"kcp_io_write_failed: {e}") from e
        finally:
            conn.close()


class KCP_AssetPick:
    @classmethod
    def INPUT_TYPES(
        cls,
        db_path: str = "output/kcp/db/kcp.sqlite",
        asset_type: str = "character",
        include_archived: bool = False,
        refresh_token: int = 0,
        strict: bool = False,
    ):
        choices = _safe_asset_choices(db_path, asset_type, include_archived, refresh_token)
        return {
            "required": {
                "db_path": ("STRING", {"default": db_path}),
                "asset_type": (sorted(ASSET_TYPES),),
                "asset_name": (choices,),
                "include_archived": ("BOOLEAN", {"default": include_archived}),
                "refresh_token": ("INT", {"default": refresh_token}),
                "strict": ("BOOLEAN", {"default": strict}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("asset_id", "positive_fragment", "negative_fragment", "json_fields", "thumb_image", "image", "warning_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    @classmethod
    def list_names(cls, db_path: str, asset_type: str, include_archived: bool = False, refresh_token: int = 0):
        return _safe_asset_choices(db_path, asset_type, include_archived, refresh_token)

    def run(self, db_path, asset_type, asset_name, include_archived=False, refresh_token=0, strict=False):
        _ = refresh_token
        if (asset_name is None or str(asset_name).strip() == "") and not strict:
            return ("", "", "", "{}", None, None, json.dumps({"code": "kcp_asset_no_selection"}))

        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
        try:
            row = get_asset_by_type_name(conn, asset_type, asset_name, include_archived=include_archived)
            if not row:
                if strict:
                    raise RuntimeError("kcp_asset_not_found")
                return ("", "", "", "{}", None, None, json.dumps({"code": "kcp_asset_not_found"}))
            root = kcp_root_from_db_path(db_path)
            missing_paths = []
            if row["image_path"]:
                image_path = root / row["image_path"]
                if not image_path.exists():
                    missing_paths.append(str(image_path.resolve()))
            if row["thumb_path"]:
                thumb_path = root / row["thumb_path"]
                if not thumb_path.exists():
                    missing_paths.append(str(thumb_path.resolve()))

            if missing_paths:
                if strict:
                    raise RuntimeError("kcp_asset_image_missing")
                warning = {
                    "code": "kcp_asset_media_missing",
                    "asset_id": row["id"],
                    "asset_type": asset_type,
                    "asset_name": asset_name,
                    "missing_paths": missing_paths,
                }
                return (row["id"], row["positive_fragment"], row["negative_fragment"], row["json_fields"], None, None, json.dumps(warning))

            return (row["id"], row["positive_fragment"], row["negative_fragment"], row["json_fields"], None, None, "{}")
        finally:
            conn.close()
