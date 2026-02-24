from __future__ import annotations

from pathlib import Path



def _comfy_output_dir() -> Path | None:
    try:
        import folder_paths  # type: ignore

        out = folder_paths.get_output_directory()
        if out:
            return Path(out).resolve()
    except Exception:
        return None
    return None


def resolve_root(kcp_root: str) -> Path:
    root = Path(kcp_root)
    if root.is_absolute():
        return root.resolve()

    comfy_out = _comfy_output_dir()
    if comfy_out is not None:
        parts = root.parts
        if len(parts) >= 2 and parts[0].lower() == "output":
            root = Path(*parts[1:])
        return (comfy_out / root).resolve()

    return (Path.cwd() / root).resolve()
def resolve_root(kcp_root: str) -> Path:
    root = Path(kcp_root)
    if not root.is_absolute():
        root = Path.cwd() / root
    return root.resolve()


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
