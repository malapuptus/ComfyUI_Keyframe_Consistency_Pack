import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def replace_top_level_func(path: Path, func: str, new_src: str) -> None:
    txt = path.read_text(encoding="utf-8")
    pat = rf"(?ms)^def {re.escape(func)}\b.*?(?=^def |\Z)"
    matches = list(re.finditer(pat, txt))
    if not matches:
        raise RuntimeError(f"Function not found: {func} in {path}")
    # Replace first occurrence and delete duplicates
    first = matches[0]
    out = txt[:first.start()] + new_src.strip() + "\n\n" + txt[first.end():]
    # Remove any later duplicates
    matches2 = list(re.finditer(pat, out))
    if len(matches2) > 1:
        # Keep the first one, remove the rest
        for m in reversed(matches2[1:]):
            out = out[:m.start()] + out[m.end():]
    path.write_text(out, encoding="utf-8")

image_py = ROOT / "kcp" / "util" / "image_io.py"

new_save_atomic = r'''
def save_comfy_image_atomic(image_obj: Any, out_path: Path, fmt: str | None = None) -> bool:
    """
    Save an IMAGE-like object to out_path atomically.
    - Creates parent dirs.
    - Writes to a temp file in the same directory, then os.replace().
    - fmt can be "PNG" or "WEBP". If None, inferred from suffix.
    Returns True if written.
    """
    if image_obj is None:
        return False
    if not pillow_available():
        raise RuntimeError("kcp_io_write_failed: Pillow required to save IMAGE input; install with pip install pillow")

    from pathlib import Path
    import os
    import tempfile

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    encode_fmt = (fmt or ("WEBP" if out_path.suffix.lower() == ".webp" else "PNG")).upper()

    # Use a temp file in the same directory so os.replace is atomic on Windows
    tmp_fd, tmp_name = tempfile.mkstemp(prefix="kcp_", suffix=out_path.suffix + ".tmp", dir=str(out_path.parent))
    os.close(tmp_fd)
    try:
        img = comfy_image_to_pil(image_obj)
        img.save(tmp_name, format=encode_fmt)
        os.replace(tmp_name, str(out_path))
        return True
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass
'''

replace_top_level_func(image_py, "save_comfy_image_atomic", new_save_atomic)

print("PATCH3_OK")
