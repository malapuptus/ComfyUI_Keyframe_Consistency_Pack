from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from kcp.db.migrate import migrate
from kcp.util.time_utils import now_ms


ASSET_TYPES = {"character", "environment", "camera", "lighting", "action", "keyframe", "style", "pose", "mask", "control_guide"}


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def create_asset(conn: sqlite3.Connection, payload: dict) -> str:
    asset_id = payload.get("id") or _id("asset")
    ts = now_ms()
    conn.execute(
        """
        INSERT INTO assets (
          id,type,name,description,tags_json,positive_fragment,negative_fragment,json_fields,
          thumb_path,image_path,image_hash,created_at,updated_at,version,parent_id,is_archived
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            asset_id,
            payload["type"],
            payload["name"],
            payload.get("description", ""),
            json.dumps(payload.get("tags", [])),
            payload["positive_fragment"],
            payload.get("negative_fragment", ""),
            json.dumps(payload.get("json_fields", {})),
            payload.get("thumb_path", ""),
            payload.get("image_path", ""),
            payload.get("image_hash", ""),
            ts,
            ts,
            int(payload.get("version", 1)),
            payload.get("parent_id"),
            int(payload.get("is_archived", 0)),
        ),
    )
    conn.commit()
    return asset_id




def update_asset_by_id(
    conn: sqlite3.Connection,
    asset_id: str,
    *,
    description: str,
    tags: list,
    positive_fragment: str,
    negative_fragment: str,
    json_fields: dict,
    image_path: str = "",
    thumb_path: str = "",
    image_hash: str = "",
    bump_version: bool = False,
):
    row = conn.execute("SELECT version FROM assets WHERE id = ?", (asset_id,)).fetchone()
    if not row:
        raise ValueError(f"asset not found: {asset_id}")
    version = int(row[0]) + 1 if bump_version else int(row[0])
    conn.execute(
        """
        UPDATE assets
        SET description = ?,
            tags_json = ?,
            positive_fragment = ?,
            negative_fragment = ?,
            json_fields = ?,
            image_path = ?,
            thumb_path = ?,
            image_hash = ?,
            version = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            description,
            json.dumps(tags),
            positive_fragment,
            negative_fragment,
            json.dumps(json_fields),
            image_path,
            thumb_path,
            image_hash,
            version,
            now_ms(),
            asset_id,
        ),
    )
    conn.commit()
    return conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()


def create_asset_version(
    conn: sqlite3.Connection,
    existing_row,
    new_name: str,
    *,
    description: str,
    tags: list,
    positive_fragment: str,
    negative_fragment: str,
    json_fields: dict,
    image_path: str = "",
    thumb_path: str = "",
    image_hash: str = "",
) -> str:
    new_version = int(existing_row["version"]) + 1
    return create_asset(
        conn,
        {
            "type": existing_row["type"],
            "name": new_name,
            "description": description,
            "tags": tags,
            "positive_fragment": positive_fragment,
            "negative_fragment": negative_fragment,
            "json_fields": json_fields,
            "thumb_path": thumb_path,
            "image_path": image_path,
            "image_hash": image_hash,
            "version": new_version,
            "parent_id": existing_row["id"],
            "is_archived": int(existing_row["is_archived"]),
        },
    )


def get_asset_by_type_name(conn: sqlite3.Connection, asset_type: str, name: str, include_archived: bool = False):
    q = "SELECT * FROM assets WHERE type = ? AND name = ?"
    args = [asset_type, name]
    if not include_archived:
        q += " AND is_archived = 0"
    return conn.execute(q, args).fetchone()


def list_asset_names(conn: sqlite3.Connection, asset_type: str, include_archived: bool = False) -> list[str]:
    q = "SELECT name FROM assets WHERE type = ?"
    args = [asset_type]
    if not include_archived:
        q += " AND is_archived = 0"
    q += " ORDER BY name COLLATE NOCASE"
    return [r[0] for r in conn.execute(q, args).fetchall()]


def save_stack(conn: sqlite3.Connection, payload: dict) -> str:
    stack_id = payload.get("id") or _id("stack")
    ts = now_ms()
    conn.execute(
        """
        INSERT INTO stacks (
          id,name,notes,character_id,environment_id,action_id,camera_id,lighting_id,style_id,
          json_overrides,created_at,updated_at,is_archived
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET
          notes=excluded.notes,
          character_id=excluded.character_id,
          environment_id=excluded.environment_id,
          action_id=excluded.action_id,
          camera_id=excluded.camera_id,
          lighting_id=excluded.lighting_id,
          style_id=excluded.style_id,
          json_overrides=excluded.json_overrides,
          updated_at=excluded.updated_at
        """,
        (
            stack_id,
            payload["name"],
            payload.get("notes", ""),
            payload.get("character_id"),
            payload.get("environment_id"),
            payload.get("action_id"),
            payload.get("camera_id"),
            payload.get("lighting_id"),
            payload.get("style_id"),
            json.dumps(payload.get("json_overrides", {})),
            ts,
            ts,
            int(payload.get("is_archived", 0)),
        ),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM stacks WHERE name = ?", (payload["name"],)).fetchone()
    return str(row[0])


def get_stack_by_name(conn: sqlite3.Connection, name: str, include_archived: bool = False):
    q = "SELECT * FROM stacks WHERE name = ?"
    if not include_archived:
        q += " AND is_archived = 0"
    return conn.execute(q, (name,)).fetchone()


def list_stack_names(conn: sqlite3.Connection, include_archived: bool = False) -> list[str]:
    q = "SELECT name FROM stacks"
    if not include_archived:
        q += " WHERE is_archived = 0"
    q += " ORDER BY name COLLATE NOCASE"
    return [r[0] for r in conn.execute(q).fetchall()]


def create_keyframe_set(conn: sqlite3.Connection, payload: dict) -> str:
    set_id = payload.get("id") or _id("kset")
    ts = now_ms()
    conn.execute(
        """
        INSERT INTO keyframe_sets (
          id,name,stack_id,variant_policy_id,variant_policy_json,base_seed,width,height,model_ref,
          created_at,updated_at,picked_index,notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            set_id,
            payload.get("name", ""),
            payload["stack_id"],
            payload["variant_policy_id"],
            json.dumps(payload.get("variant_policy_json", {})),
            int(payload["base_seed"]),
            int(payload["width"]),
            int(payload["height"]),
            payload.get("model_ref", ""),
            ts,
            ts,
            payload.get("picked_index"),
            payload.get("notes", ""),
        ),
    )
    conn.commit()
    return set_id


def add_keyframe_set_item(conn: sqlite3.Connection, payload: dict) -> str:
    item_id = payload.get("id") or _id("kitem")
    conn.execute(
        """
        INSERT INTO keyframe_set_items (
          id,set_id,idx,seed,positive_prompt,negative_prompt,gen_params_json,image_path,thumb_path,score_json,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            item_id,
            payload["set_id"],
            int(payload["idx"]),
            int(payload["seed"]),
            payload["positive_prompt"],
            payload.get("negative_prompt", ""),
            json.dumps(payload.get("gen_params_json", {})),
            payload.get("image_path", ""),
            payload.get("thumb_path", ""),
            json.dumps(payload.get("score_json", {})),
            now_ms(),
        ),
    )
    conn.commit()
    return item_id


def set_picked_index(conn: sqlite3.Connection, set_id: str, picked_index: int, notes_optional: str | None = None):
    if int(picked_index) < 0:
        raise ValueError("picked_index must be >= 0")

    ts = now_ms()
    if notes_optional is None:
        conn.execute(
            "UPDATE keyframe_sets SET picked_index = ?, updated_at = ? WHERE id = ?",
            (int(picked_index), ts, set_id),
        )
    else:
        conn.execute(
            "UPDATE keyframe_sets SET picked_index = ?, notes = ?, updated_at = ? WHERE id = ?",
            (int(picked_index), notes_optional, ts, set_id),
        )
    conn.commit()
    return conn.execute("SELECT * FROM keyframe_sets WHERE id = ?", (set_id,)).fetchone()



def get_set_item(conn: sqlite3.Connection, set_id: str, idx: int):
    return conn.execute(
        "SELECT * FROM keyframe_set_items WHERE set_id = ? AND idx = ?",
        (set_id, int(idx)),
    ).fetchone()


def get_keyframe_set(conn: sqlite3.Connection, set_id: str):
    return conn.execute("SELECT * FROM keyframe_sets WHERE id = ?", (set_id,)).fetchone()


def update_set_item_media(conn: sqlite3.Connection, set_id: str, idx: int, image_rel: str, thumb_rel: str):
    if int(idx) < 0:
        raise ValueError("idx must be >= 0")
    cur = conn.execute(
        "UPDATE keyframe_set_items SET image_path = ?, thumb_path = ? WHERE set_id = ? AND idx = ?",
        (image_rel, thumb_rel, set_id, int(idx)),
    )
    if cur.rowcount == 0:
        conn.rollback()
        raise ValueError(f"set item not found: set_id={set_id} idx={idx}")
    conn.commit()
    return get_set_item(conn, set_id, int(idx))
