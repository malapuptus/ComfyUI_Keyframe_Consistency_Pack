from __future__ import annotations

from pathlib import Path
from typing import Any


def pillow_available() -> bool:
    try:
        import PIL  # noqa: F401

        return True
    except Exception:
        return False


def comfy_image_to_pil(image_obj: Any):
    """Convert common ComfyUI IMAGE values to a PIL RGB image.

    Supported inputs:
    - torch Tensor with shape [B,H,W,C] or [H,W,C]
    - numpy ndarray with shape [B,H,W,C] or [H,W,C]
    - PIL.Image.Image

    Behavior is conservative/deterministic:
    - Uses the first batch item when batched.
    - Expects channel-last tensors/arrays and at least 3 channels.
    - Values <= 1.0 are treated as normalized and scaled to [0,255];
      otherwise values are clamped directly to [0,255].
    """
    if not pillow_available():
        raise RuntimeError("Pillow not available")

    from PIL import Image

    if isinstance(image_obj, Image.Image):
        return image_obj.convert("RGB")

    data = image_obj
    if hasattr(data, "detach"):
        data = data.detach()
    if hasattr(data, "cpu"):
        data = data.cpu()
    if hasattr(data, "numpy"):
        data = data.numpy()

    if not hasattr(data, "shape"):
        raise ValueError("unsupported IMAGE type")

    shape = tuple(int(x) for x in data.shape)
    if len(shape) == 4:
        data = data[0]
        shape = tuple(int(x) for x in data.shape)
    if len(shape) != 3:
        raise ValueError("IMAGE must have shape [H,W,C] or [B,H,W,C]")

    h, w, c = shape
    if c < 3:
        raise ValueError("IMAGE must have at least 3 channels")

    if hasattr(data, "astype") and hasattr(data, "max"):
        arr = data[..., :3]
        max_val = float(arr.max()) if arr.size else 0.0
        if max_val <= 1.0:
            arr = arr * 255.0
        arr = arr.clip(0.0, 255.0).astype("uint8")
        return Image.fromarray(arr, mode="RGB")

    if hasattr(data, "tolist"):
        data = data.tolist()

    if not isinstance(data, list) or h == 0 or w == 0:
        raise ValueError("invalid IMAGE data")

    pixels = bytearray()
    for row in data:
        if not isinstance(row, list) or len(row) != w:
            raise ValueError("ragged IMAGE rows")
        for px in row:
            if not isinstance(px, list) or len(px) < 3:
                raise ValueError("invalid pixel format")
            for ch in px[:3]:
                cv = float(ch)
                if cv <= 1.0:
                    cv *= 255.0
                pixels.append(int(max(0, min(255, round(cv)))))

    return Image.frombytes("RGB", (w, h), bytes(pixels))


def pil_to_comfy_image(pil_image: Any):
    """Convert PIL image to ComfyUI IMAGE tensor/array with batch dim [1,H,W,C] in 0..1."""
    if not pillow_available():
        raise RuntimeError("Pillow not available")

    rgb = pil_image.convert("RGB")

    try:
        import numpy as np  # type: ignore

        arr = np.asarray(rgb, dtype=np.float32) / 255.0
        arr = arr[None, ...]
        try:
            import torch  # type: ignore

            return torch.from_numpy(arr)
        except Exception:
            return arr
    except Exception:
        data = list(rgb.getdata())
        w, h = rgb.size
        rows = []
        idx = 0
        for _ in range(h):
            row = []
            for _ in range(w):
                r, g, b = data[idx]
                idx += 1
                row.append([r / 255.0, g / 255.0, b / 255.0])
            rows.append(row)
        return [rows]


def load_image_as_comfy(path: Path):
    if not pillow_available():
        raise RuntimeError("Pillow not available")
    from PIL import Image

    with Image.open(path) as img:
        return pil_to_comfy_image(img)


def save_optional_image(image_obj: Any, path: Path) -> bool:
    if image_obj is None:
        return False
    if not pillow_available():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    img = comfy_image_to_pil(image_obj)
    img.save(tmp, format="PNG")
    tmp.replace(path)
    return True


def make_thumbnail(source: Path, target: Path, max_px: int = 384) -> bool:
    if not pillow_available() or not source.exists():
        return False
    from PIL import Image

    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as img:
        img = img.convert("RGB")
        img.thumbnail((max_px, max_px))
        tmp = target.with_suffix(target.suffix + ".tmp")
        img.save(tmp, format="WEBP")
        tmp.replace(target)
    return True
