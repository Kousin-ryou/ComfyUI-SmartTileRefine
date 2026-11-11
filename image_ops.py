import math

import torch
import torch.nn.functional as F


def resize(image, width, height, mode="bicubic"):
    if image.shape[1:3] == (height, width):
        return image
    kwargs = {"align_corners": False, "antialias": True} if mode in ("bilinear", "bicubic") else {}
    return F.interpolate(image.movedim(-1, 1), size=(height, width), mode=mode, **kwargs).movedim(1, -1).clamp(0, 1)


def pad_tile(image, alignment):
    h, w = image.shape[1:3]
    pw = math.ceil(max(64, w) / alignment) * alignment
    ph = math.ceil(max(64, h) / alignment) * alignment
    return F.pad(image.movedim(-1, 1), (0, pw - w, 0, ph - h), mode="replicate").movedim(1, -1)


def lowpass(image, radius):
    # Gaussian at a bounded working resolution avoids kernels growing with the canvas.
    h, w = image.shape[1:3]
    scale = max(1, radius / 3)
    sh, sw = max(1, round(h / scale)), max(1, round(w / scale))
    small = F.interpolate(image.movedim(-1, 1), size=(sh, sw), mode="area")
    sigma = max(0.5, radius / scale)
    r = math.ceil(3 * sigma)
    axis = torch.arange(-r, r + 1, device=image.device, dtype=image.dtype)
    kernel = torch.exp(-axis.square() / (2 * sigma * sigma))
    kernel /= kernel.sum()
    channels = image.shape[-1]
    small = F.conv2d(F.pad(small, (r, r, 0, 0), mode="replicate"),
                     kernel.view(1, 1, 1, -1).expand(channels, 1, 1, -1), groups=channels)
    small = F.conv2d(F.pad(small, (0, 0, r, r), mode="replicate"),
                     kernel.view(1, 1, -1, 1).expand(channels, 1, -1, 1), groups=channels)
    return F.interpolate(small, size=(h, w), mode="bilinear", align_corners=False).movedim(1, -1)


def color_correct(generated, original, strength):
    if strength <= 0:
        return generated
    radius = max(8, min(original.shape[1:3]) / 24)
    delta = (lowpass(original, radius) - lowpass(generated, radius)).clamp(-0.15, 0.15)
    return (generated + strength * delta).clamp(0, 1)


def axis_weight(length, core_start, core_end, left, right, sharpness):
    pos = torch.arange(length, dtype=torch.float32) + 0.5
    # At a shared core border each neighbour has 0.5 weight; the support reaches
    # into both cores. A narrow transition is used only for the detail band.
    result = torch.ones(length)
    for border, extent, direction in ((core_start, left, 1), (core_end, right, -1)):
        if extent:
            u = ((pos - border) * direction / (2 * extent / sharpness) + 0.5).clamp(0, 1)
            result *= u.square() * (3 - 2 * u)
    return result


def tile_weight(tile, sharpness=1.0):
    x0, y0, x1, y1 = tile["crop"]
    a, b, c, d = tile["core"]
    wx = axis_weight(x1 - x0, a - x0, c - x0, a - x0, x1 - c, sharpness)
    wy = axis_weight(y1 - y0, b - y0, d - y0, b - y0, y1 - d, sharpness)
    return (wy[:, None] * wx[None, :])[None, :, :, None]


class TileMerger:
    """CPU, execution-scoped accumulation; no generated tile list is retained."""
    def __init__(self, source, plan):
        self.source = source
        self.low = torch.zeros_like(source)
        self.high = torch.zeros_like(source)
        self.low_weight = torch.zeros((*source.shape[:3], 1), dtype=source.dtype)
        self.high_weight = torch.zeros_like(self.low_weight)
        # Split tile residuals against the common source so an identity run
        # reconstructs exactly, including the image and crop borders.
        self.radius = max(4, min(plan["width"] / plan["columns"], plan["height"] / plan["rows"]) / 32)

    def add(self, tile, image):
        x0, y0, x1, y1 = tile["crop"]
        region = (slice(None), slice(y0, y1), slice(x0, x1), slice(None))
        residual = image - self.source[region]
        lo = lowpass(residual, self.radius)
        hi = residual - lo
        wl, wh = tile_weight(tile), tile_weight(tile, 10.0)
        self.low[region].addcmul_(lo, wl)
        self.high[region].addcmul_(hi, wh)
        self.low_weight[region] += wl
        self.high_weight[region] += wh

    def context(self, tile, strength=0.5):
        x0, y0, x1, y1 = tile["crop"]
        region = (slice(None), slice(y0, y1), slice(x0, x1), slice(None))
        lw, hw = self.low_weight[region], self.high_weight[region]
        residual = self.low[region] / lw.clamp_min(1e-8) + self.high[region] / hw.clamp_min(1e-8)
        # Only previous tiles' supported pixels can influence this crop, at a
        # bounded strength, while each new core stays anchored to the source.
        confidence = lw.clamp(0, 1) * strength
        return (self.source[region] + residual * confidence).clamp(0, 1)

    def finish(self):
        if torch.any(self.low_weight <= 0) or torch.any(self.high_weight <= 0):
            raise RuntimeError("融合权重出现未覆盖像素。")
        self.low.div_(self.low_weight)
        self.high.div_(self.high_weight)
        self.low.add_(self.high).add_(self.source).clamp_(0, 1)
        return self.low
