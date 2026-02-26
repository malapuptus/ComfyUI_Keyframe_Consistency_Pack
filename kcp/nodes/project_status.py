from __future__ import annotations

import json
from kcp.db.paths import normalize_db_path, with_projectinit_db_path_tip
<<<<<<< codex/bootstrap-kcp-project-structure-gy3tp6
=======
from pathlib import Path

>>>>>>> main
from kcp.db.repo import connect


class KCP_ProjectStatus:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "db_path": ("STRING", {"default": "output/kcp/db/kcp.sqlite"}),
                "required_environment_names_csv": ("STRING", {"default": ""}),
                "strict_plate_check": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("status_text", "status_json", "is_ready_for_keyframes")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, db_path, required_environment_names_csv="", strict_plate_check=True):
        try:
            conn = connect(normalize_db_path(db_path))
        except Exception as e:
            raise with_projectinit_db_path_tip(db_path, e) from e
<<<<<<< codex/bootstrap-kcp-project-structure-gy3tp6
=======
        conn = connect(Path(db_path))
>>>>>>> main
        try:
            env_rows = conn.execute("SELECT name, image_path FROM assets WHERE type='environment' AND is_archived=0").fetchall()
            warnings = []
            if not env_rows:
                warnings.append("Build plates first: no environment assets found.")
            elif strict_plate_check:
                missing = [r["name"] for r in env_rows if not (r["image_path"] or "").strip()]
                if missing:
                    warnings.append(f"missing plate: {', '.join(missing)}")

            required = [s.strip() for s in required_environment_names_csv.split(",") if s.strip()]
            if required:
                available = {r["name"] for r in env_rows}
                missing_required = [r for r in required if r not in available]
                if missing_required:
                    warnings.append(f"required environments missing: {', '.join(missing_required)}")

            ready = len(warnings) == 0
            status = {"ready": ready, "warnings": warnings, "environment_count": len(env_rows)}
            text = "Ready for keyframes" if ready else " ; ".join(warnings)
            return (text, json.dumps(status), ready)
        finally:
            conn.close()
