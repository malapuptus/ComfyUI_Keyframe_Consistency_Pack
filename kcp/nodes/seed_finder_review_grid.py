from __future__ import annotations

import math

from kcp.util.image_io import comfy_image_to_pil, pil_to_comfy_image, pillow_available


def _image_to_pil_any(image_obj):
    try:
        return comfy_image_to_pil(image_obj).convert("RGB")
    except Exception:
        from PIL import Image

        if isinstance(image_obj, list) and image_obj and isinstance(image_obj[0], list):
            h = len(image_obj)
            w = len(image_obj[0]) if h > 0 else 0
            if h <= 0 or w <= 0:
                raise
            pixels = []
            for row in image_obj:
                for px in row:
                    r, g, b = px[:3]
                    def _u8(v):
                        fv = float(v)
                        if fv <= 1.0:
                            fv *= 255.0
                        return int(max(0, min(255, round(fv))))
                    pixels.append((_u8(r), _u8(g), _u8(b)))
            img = Image.new("RGB", (w, h))
            img.putdata(pixels)
            return img
        raise


class KCP_SeedFinderReviewGrid:
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "seeds": ("INT",),
                "columns": ("INT", {"default": 4, "min": 1, "max": 64}),
                "tile_padding": ("INT", {"default": 8, "min": 0, "max": 128}),
                "show_labels": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT")
    RETURN_NAMES = ("grid_image", "seed_text", "count")
    FUNCTION = "run"
    CATEGORY = "KCP"

    def run(self, images, seeds, columns=4, tile_padding=8, show_labels=True):
        if isinstance(columns, list):
            columns = columns[0] if columns else 4
        if isinstance(tile_padding, list):
            tile_padding = tile_padding[0] if tile_padding else 8
        if isinstance(show_labels, list):
            show_labels = show_labels[0] if show_labels else True

        if not pillow_available():
            raise RuntimeError("kcp_io_write_failed: Pillow required for SeedFinderReviewGrid")

        from PIL import Image, ImageDraw

        img_list = list(images or [])
        seed_values = seeds if isinstance(seeds, list) else [seeds]
        if len(seed_values) == 1 and isinstance(seed_values[0], list):
            seed_values = seed_values[0]
        seed_list = [int(s) for s in (seed_values or [])]
        count = min(len(img_list), len(seed_list))
        warning = ""
        if len(img_list) != len(seed_list):
            warning = f"warning: image/seed length mismatch images={len(img_list)} seeds={len(seed_list)} using={count}"

        if count <= 0:
            blank = Image.new("RGB", (64, 64), (0, 0, 0))
            text = warning or "warning: no tiles"
            return (pil_to_comfy_image(blank), text, 0)

        pil_tiles = [_image_to_pil_any(img_list[i]) for i in range(count)]
        tile_w, tile_h = pil_tiles[0].size
        cols = max(1, int(columns))
        rows = int(math.ceil(count / float(cols)))
        pad = max(0, int(tile_padding))
        label_h = 18 if bool(show_labels) else 0

        grid_w = (cols * tile_w) + ((cols + 1) * pad)
        grid_h = (rows * (tile_h + label_h)) + ((rows + 1) * pad)
        canvas = Image.new("RGB", (grid_w, grid_h), (24, 24, 24))
        draw = ImageDraw.Draw(canvas)

        lines = []
        if warning:
            lines.append(warning)
        for i in range(count):
            r = i // cols
            c = i % cols
            x = pad + c * (tile_w + pad)
            y = pad + r * (tile_h + label_h + pad)
            canvas.paste(pil_tiles[i], (x, y))
            seed = seed_list[i]
            label = f"[{i}] seed={seed}"
            lines.append(label)
            if bool(show_labels):
                draw.text((x + 2, y + tile_h + 2), label, fill=(230, 230, 230))

        return (pil_to_comfy_image(canvas), "\n".join(lines), count)
