import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
paths_py = ROOT / "kcp" / "db" / "paths.py"
txt = paths_py.read_text(encoding="utf-8")

def replace_func(txt: str, name: str, new_src: str) -> str:
    pat = rf"(?ms)^def {re.escape(name)}\b.*?(?=^def |\Z)"
    ms = list(re.finditer(pat, txt))
    if not ms:
        raise RuntimeError(f"Function not found: {name}")
    m = ms[0]
    out = txt[:m.start()] + new_src.strip() + "\n\n" + txt[m.end():]
    # remove any duplicates
    ms2 = list(re.finditer(pat, out))
    if len(ms2) > 1:
        for d in reversed(ms2[1:]):
            out = out[:d.start()] + out[d.end():]
    return out

new_comfy = r'''
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
'''
new_resolve = r'''
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
'''

txt = replace_func(txt, "_comfy_output_dir", new_comfy)
txt = replace_func(txt, "resolve_root", new_resolve)
paths_py.write_text(txt, encoding="utf-8")
print("PATCH_ROOT_OK")
