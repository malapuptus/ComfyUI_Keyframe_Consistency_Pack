import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "kcp" / "nodes" / "keyframe_set_save.py"
s = p.read_text(encoding="utf-8")

# 1) Remove any previously-inserted effective_policy_id lines (wrong indent, duplicates, etc.)
s2 = re.sub(r"(?m)^\s*effective_policy_id\s*=.*\n", "", s)

# 2) Ensure the create_keyframe_set payload uses effective_policy_id (safe if already done)
s2 = s2.replace('"variant_policy_id": variant_policy_id,', '"variant_policy_id": effective_policy_id,')

# 3) Insert effective_policy_id at the correct place with correct indentation
# We insert after: variants = variants_payload.get("variants", [])
m = re.search(r'(?m)^(?P<indent>\s*)variants\s*=\s*variants_payload\.get\(\s*["\']variants["\']\s*,\s*\[\]\s*\)\s*$', s2)
if not m:
    raise SystemExit("PATCH_FAIL: could not find variants = variants_payload.get('variants', []) line")

indent = m.group("indent")
insert = indent + 'effective_policy_id = variant_policy_id if str(variant_policy_id).strip() else str(variants_payload.get("policy_id", "") or "")\n'
pos = m.end()
s2 = s2[:pos] + "\n" + insert + s2[pos:]

p.write_text(s2, encoding="utf-8")
print("PATCH_FIX_KCP046_OK")
