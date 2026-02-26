from __future__ import annotations

from pathlib import Path
import warnings


DEFAULT_DB_PATH_INPUT = "output/kcp/db/kcp.sqlite"




def _comfy_output_dir() -> "Path | None":
    """
    Return ComfyUI output directory if folder_paths is available.

    IMPORTANT: Do NOT cache. Tests inject sys.modules["folder_paths"].
    """
    try:
        import sys
        from pathlib import Path
        fp = sys.modules.get("folder_paths")
        if fp is not None and hasattr(fp, "get_output_directory"):
            return Path(fp.get_output_directory())
        import folder_paths  # type: ignore
        return Path(folder_paths.get_output_directory())
    except Exception:
        return None

def resolve_root(kcp_root: str) -> "Path":
    from pathlib import Path
    root = Path(str(kcp_root))
    if root.is_absolute():
        return root.resolve()

    comfy_out = _comfy_output_dir()
    if comfy_out is not None:
        parts = root.parts
        if len(parts) >= 1 and parts[0].lower() == "output":
            root = Path(*parts[1:]) if len(parts) > 1 else Path()
        return (Path(comfy_out) / root).resolve()

    return (Path.cwd() / root).resolve()

def ensure_layout(root: Path, db_filename: str) -> dict[str, Path]:
    db_dir = root / "db"
    images_dir = root / "images"
    thumbs_dir = root / "thumbs"
    sets_dir = root / "sets"
    receipts_dir = root / "receipts"
    for p in [db_dir, images_dir, thumbs_dir, sets_dir, receipts_dir]:
        p.mkdir(parents=True, exist_ok=True)
    return {
        "root": root,
        "db_dir": db_dir,
        "db_path": db_dir / db_filename,
        "images_dir": images_dir,
        "thumbs_dir": thumbs_dir,
        "sets_dir": sets_dir,
        "receipts_dir": receipts_dir,
    }


def normalize_db_path(db_path: str) -> Path:
    cleaned = str(db_path).strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()
    p = Path(cleaned)
    if not p.is_absolute():
        p = resolve_root(str(p))
    if p.is_dir():
        raise RuntimeError("kcp_db_path_is_directory: expected .../db/kcp.sqlite")
    if not p.parent.exists():
        raise RuntimeError(f"kcp_db_path_parent_missing: {p.parent}")
    if p.suffix.lower() not in {".sqlite", ".db"}:
        warnings.warn(f"kcp_db_path_suffix_unusual: {p.name}", RuntimeWarning)
    return p


def is_default_db_path_input(db_path: str) -> bool:
    cleaned = str(db_path).strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()
    return cleaned == DEFAULT_DB_PATH_INPUT


def with_projectinit_db_path_tip(db_path: str, err: Exception) -> RuntimeError:
    msg = str(err)
    if is_default_db_path_input(db_path):
        msg = f"{msg} Tip: wire KCP_ProjectInit.db_path into this node"
    return RuntimeError(msg)


def kcp_root_from_db_path(db_path: str) -> Path:
    p = normalize_db_path(db_path)
    return p.parent.parent.resolve()
