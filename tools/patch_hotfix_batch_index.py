import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "kcp" / "nodes" / "keyframe_set_item_save_image.py"
txt = p.read_text(encoding="utf-8")

# 1) Ensure run() signature accepts batch_index as last arg
# Match def run(self, ... overwrite=True): and add batch_index=0 if missing.
def_sig_pat = re.compile(r"(?ms)^(?P<indent>\s*)def run\((?P<args>[^)]*)\)\s*:", re.M)
m = def_sig_pat.search(txt)
if not m:
    raise RuntimeError("Could not find def run(...) in keyframe_set_item_save_image.py")

args = m.group("args")
if "batch_index" not in args:
    # insert after overwrite=True if present, else append
    if re.search(r"\boverwrite\s*=\s*True\b", args):
        args2 = re.sub(r"(\boverwrite\s*=\s*True\b)", r"\1, batch_index=0", args)
    else:
        args2 = args.rstrip() + ", batch_index=0"
    txt = txt[:m.start("args")] + args2 + txt[m.end("args"):]

# 2) Ensure batch selection block exists after idx validation
if "kcp_batch_index_oob" not in txt:
    # Find idx check block and insert after it
    # Handle either: if idx < 0: raise ...  OR  if int(idx) < 0: raise ...
    idx_block_pat = re.compile(
        r"(?ms)^(?P<indent>\s*)if\s+(?:int\(\s*)?idx(?:\s*\))?\s*<\s*0\s*:\s*\n(?P=indent)\s+raise\s+RuntimeError\([^\)]*\)\s*\n",
        re.M
    )
    m2 = idx_block_pat.search(txt)
    if not m2:
        raise RuntimeError("Could not find idx < 0 validation block to insert batch selection after")

    indent = m2.group("indent")
    insert = f"""{indent}# Select one image from a batch if needed
{indent}try:
{indent}    shape = getattr(image, "shape", None)
{indent}    if shape is not None and len(shape) == 4:
{indent}        b = int(shape[0])
{indent}        bi = int(batch_index or 0)
{indent}        if bi < 0 or bi >= b:
{indent}            raise RuntimeError(f"kcp_batch_index_oob: batch_index={{bi}} batch_size={{b}}")
{indent}        image = image[bi]
{indent}except Exception:
{indent}    # If shape introspection fails, keep original; downstream save will raise if invalid.
{indent}    pass

"""
    txt = txt[:m2.end()] + insert + txt[m2.end():]

p.write_text(txt, encoding="utf-8")
print("PATCH_BATCH_OK")
