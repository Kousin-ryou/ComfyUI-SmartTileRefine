"""The execution node and preview endpoint share these integer coordinates."""
import math

MAX_IMAGE_PIXELS = 64 * 1024 * 1024


def target_size(width, height, upscale_by=1.5, upscale_connected=False):
    factor = float(upscale_by) if upscale_connected else 1.0
    if not math.isfinite(factor) or not 1 <= factor <= 8:
        raise ValueError("放大倍率需为 1～8。")
    return max(1, int(width * factor + 0.5)), max(1, int(height * factor + 0.5))


def make_plan(width, height, columns=2, rows=2, expand_percent=15.0):
    width, height, columns, rows = int(width), int(height), int(columns), int(rows)
    if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS or max(width, height) > 65536:
        raise ValueError("画布最多 64 MP、单边最多 65536 像素，请缩小输入图片。")
    if not (1 <= columns <= 8 and 1 <= rows <= 8):
        raise ValueError("横向和纵向块数各为 1～8。")
    if columns > width or rows > height:
        raise ValueError("块数超过图片像素尺寸，请减少横向或纵向块数。")
    if not math.isfinite(expand_percent) or not 0 <= expand_percent <= 50:
        raise ValueError("分块延展需为 0～50%。")
    xs = [i * width // columns for i in range(columns + 1)]
    ys = [i * height // rows for i in range(rows + 1)]
    tiles = []
    for row in range(rows):
        for col in range(columns):
            x0, x1, y0, y1 = xs[col], xs[col + 1], ys[row], ys[row + 1]
            dx = int((x1 - x0) * expand_percent / 100 + 0.5)
            dy = int((y1 - y0) * expand_percent / 100 + 0.5)
            crop = [max(0, x0 - dx), max(0, y0 - dy), min(width, x1 + dx), min(height, y1 + dy)]
            tiles.append({"id": row * columns + col, "row": row, "col": col,
                          "core": [x0, y0, x1, y1], "crop": crop})
    return {"width": width, "height": height, "columns": columns, "rows": rows,
            "count": len(tiles), "tiles": tiles}
