from __future__ import annotations

import json

from kcp.db.migrate import migrate
from kcp.db.paths import ensure_layout, resolve_root
from kcp.db.repo import connect


class KCP_ProjectInit:
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "kcp_root": ("STRING", {"default": "output/kcp"}),
                "db_filename": ("STRING", {"default": "kcp.sqlite"}),
                "create_if_missing": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("db_path", "kcp_root_resolved", "status_json")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, kcp_root: str, db_filename: str, create_if_missing: bool = True):
        root = resolve_root(kcp_root)
        if create_if_missing:
            layout = ensure_layout(root, db_filename)
            db_path = layout["db_path"]
        else:
            db_path = root / "db" / db_filename
            if not root.exists() or not (root / "db").exists() or not db_path.exists():
                raise RuntimeError(
                    "kcp_project_missing: "
                    f"kcp_root={root} db_path={db_path} create_if_missing=False. "
                    "Set create_if_missing=True to initialize project folders and DB."
                )
        try:
            conn = connect(db_path)
            ver = migrate(conn)
            conn.close()
        except Exception as e:
            raise RuntimeError(f"kcp_db_migration_failed: {e}") from e

        status = {
            "ok": True,
            "db_path": str(db_path),
            "kcp_root_resolved": str(root),
            "schema_version": ver,
            "create_if_missing": bool(create_if_missing),
        }
        return (str(db_path), str(root), json.dumps(status))
