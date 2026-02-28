import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def write(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

# ---------- P2: resolve_root("output") should map to comfy_output root ----------
paths_py = ROOT / "kcp" / "db" / "paths.py"
s = read(paths_py)

# Replace:
#   if len(parts) >= 2 and parts[0].lower() == "output":
#       root = Path(*parts[1:])
# with:
#   if len(parts) >= 1 and parts[0].lower() == "output":
#       root = Path(*parts[1:]) if len(parts) > 1 else Path()
pat = r'(?ms)^(\s*)if\s+len\(parts\)\s*>=\s*2\s+and\s+parts\[0\]\.lower\(\)\s*==\s*"output"\s*:\s*\n\1\s*root\s*=\s*Path\(\*parts\[1:\]\)\s*$'
m = re.search(pat, s)
if not m:
    # If formatting differs, try a looser patch
    s = re.sub(
        r'(?m)^\s*if\s+len\(parts\)\s*>=\s*2\s+and\s+parts\[0\]\.lower\(\)\s*==\s*"output"\s*:\s*$',
        '        if len(parts) >= 1 and parts[0].lower() == "output":',
        s,
        count=1,
    )
    s = re.sub(
        r'(?m)^\s*root\s*=\s*Path\(\*parts\[1:\]\)\s*$',
        '            root = Path(*parts[1:]) if len(parts) > 1 else Path()',
        s,
        count=1,
    )
else:
    indent = m.group(1)
    s = re.sub(
        pat,
        f'{indent}if len(parts) >= 1 and parts[0].lower() == "output":\n'
        f'{indent}    root = Path(*parts[1:]) if len(parts) > 1 else Path()',
        s,
        count=1,
        flags=re.M | re.S,
    )

write(paths_py, s)
print("P2_OK: patched kcp/db/paths.py (resolve_root output handling)")

# ---------- P1: preflight batch overwrite collisions before any writes ----------
batch_py = ROOT / "kcp" / "nodes" / "keyframe_set_item_save_batch.py"
t = read(batch_py)

# Only insert if we haven't already
if "Preflight: avoid partial batch writes when overwrite=False" not in t:
    m = re.search(r'(?m)^(?P<indent>\s*)root\s*=\s*kcp_root_from_db_path\(db_path\)\s*$', t)
    if not m:
        raise SystemExit("PATCH_FAIL: could not find 'root = kcp_root_from_db_path(db_path)' in keyframe_set_item_save_batch.py")

    indent = m.group("indent")
    insert = (
        f"{indent}# Preflight: avoid partial batch writes when overwrite=False.\n"
        f"{indent}# If ANY target index already has media, fail before writing anything.\n"
        f"{indent}if not overwrite:\n"
        f"{indent}    _shape = getattr(images, 'shape', None)\n"
        f"{indent}    _batch_size = int(_shape[0]) if _shape is not None and len(_shape) == 4 else 1\n"
        f"{indent}    _ext = (format or 'webp').lower().strip('.')\n"
        f"{indent}    if _ext not in {{'webp', 'png'}}:\n"
        f"{indent}        _ext = 'webp'\n"
        f"{indent}    for _j in range(_batch_size):\n"
        f"{indent}        _idx = int(idx_start) + _j\n"
        f"{indent}        _image_abs = (root / f\"sets/{{set_id}}/{{_idx}}.{{_ext}}\").resolve()\n"
        f"{indent}        _thumb_abs = (root / f\"sets/{{set_id}}/{{_idx}}_thumb.webp\").resolve()\n"
        f"{indent}        if _image_abs.exists() or _thumb_abs.exists():\n"
        f"{indent}            raise RuntimeError(f\"kcp_set_item_media_exists: set_id={{set_id}} idx={{_idx}}\")\n"
    )

    # Insert right after the root assignment line
    lines = t.splitlines(True)
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and re.match(r'^\s*root\s*=\s*kcp_root_from_db_path\(db_path\)\s*$', line):
            out.append(insert + "\n")
            inserted = True
    if not inserted:
        raise SystemExit("PATCH_FAIL: insertion point not found while rewriting file")

    t = "".join(out)
    write(batch_py, t)
    print("P1_OK: inserted preflight into keyframe_set_item_save_batch.py")
else:
    print("P1_OK: preflight already present; no change")

print("PATCH_P1P2_DONE")
