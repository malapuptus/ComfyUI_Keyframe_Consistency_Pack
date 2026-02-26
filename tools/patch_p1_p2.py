from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def patch_asset_nodes():
    p = ROOT / "kcp" / "nodes" / "asset_nodes.py"
    txt = p.read_text(encoding="utf-8")

    # Remove fmt="PNG" kwarg in save_optional_image(...) calls
    # Converts: save_optional_image(image, image_path, fmt="PNG") -> save_optional_image(image, image_path)
    new_txt, n = re.subn(
        r"save_optional_image\(\s*([^,]+)\s*,\s*([^)]+?)\s*,\s*fmt\s*=\s*['\"]PNG['\"]\s*\)",
        r"save_optional_image(\1, \2)",
        txt,
        flags=re.M
    )

    if n == 0 and "fmt=" in txt and "save_optional_image" in txt:
        # fallback: remove any fmt=... for save_optional_image
        new_txt, n = re.subn(
            r"save_optional_image\(\s*([^,]+)\s*,\s*([^)]+?)\s*,\s*fmt\s*=\s*[^)]+\)",
            r"save_optional_image(\1, \2)",
            txt,
            flags=re.M
        )

    if n == 0:
        raise RuntimeError("P1 patch: did not find a save_optional_image(..., fmt=...) call to fix in asset_nodes.py")

    p.write_text(new_txt, encoding="utf-8")
    print(f"P1_OK: asset_nodes.py updated ({n} replacement(s))")

def patch_save_image_swallow():
    p = ROOT / "kcp" / "nodes" / "keyframe_set_item_save_image.py"
    txt = p.read_text(encoding="utf-8")

    # Replace:
    #   except Exception:
    #       pass
    # with:
    #   except RuntimeError:
    #       raise
    #   except Exception:
    #       pass
    #
    # but only for the batch-selection block (anchor on kcp_batch_index_oob)
    if "kcp_batch_index_oob" not in txt:
        raise RuntimeError("P2 patch: kcp_batch_index_oob not found; batch_index block missing?")

    # Find the first occurrence of the broad except directly after the batch block
    pat = re.compile(
        r"(?ms)(#\s*Select one image from a batch.*?)(\n\s*except\s+Exception\s*:\s*\n\s*#.*?\n\s*pass)",
    )
    m = pat.search(txt)
    if not m:
        # fallback: simpler match: except Exception: ... pass (first occurrence after kcp_batch_index_oob)
        idx = txt.find("kcp_batch_index_oob")
        tail = txt[idx:idx+2000]
        m2 = re.search(r"(?ms)\n(\s*)except\s+Exception\s*:\s*\n(\s*)#.*?\n(\s*)pass", tail)
        if not m2:
            raise RuntimeError("P2 patch: could not find the 'except Exception: pass' block to replace")
        indent = m2.group(1)
        repl = f"\n{indent}except RuntimeError:\n{indent}    raise\n{indent}except Exception:\n{indent}    # If shape introspection fails, keep original; downstream save will raise if invalid.\n{indent}    pass"
        tail2 = re.sub(r"(?ms)\n\s*except\s+Exception\s*:\s*\n\s*#.*?\n\s*pass", repl, tail, count=1)
        txt = txt[:idx] + tail2 + txt[idx+2000:]
        p.write_text(txt, encoding="utf-8")
        print("P2_OK: save_image exception handling updated (fallback)")
        return

    block = m.group(2)
    # Detect indent level from "except Exception"
    indent_m = re.search(r"\n(\s*)except\s+Exception", block)
    indent = indent_m.group(1) if indent_m else "        "

    replacement = (
        f"\n{indent}except RuntimeError:\n"
        f"{indent}    raise\n"
        f"{indent}except Exception:\n"
        f"{indent}    # If shape introspection fails, keep original; downstream save will raise if invalid.\n"
        f"{indent}    pass"
    )

    new_txt = txt[:m.start(2)] + replacement + txt[m.end(2):]
    p.write_text(new_txt, encoding="utf-8")
    print("P2_OK: save_image no longer swallows RuntimeError")

if __name__ == "__main__":
    patch_asset_nodes()
    patch_save_image_swallow()
    print("PATCH_P1P2_OK")
