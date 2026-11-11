import base64
import io
import logging
import math
import time
import uuid

import torch
from aiohttp import web
from PIL import Image

import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
from server import PromptServer

from .geometry import MAX_IMAGE_PIXELS, make_plan, target_size
from .image_ops import TileMerger, color_correct, pad_tile, resize


def thumbnail(image):
    pil = Image.fromarray((image[0].detach().cpu().numpy().clip(0, 1) * 255).round().astype("uint8"))
    pil.thumbnail((2560, 2560), Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    pil.save(stream, format="PNG", compress_level=3)
    return base64.b64encode(stream.getvalue()).decode("ascii")


def pixel_alignment(model, vae):
    downscale = int(model.get_model_object("latent_format").spacial_downscale_ratio)
    diffusion = model.get_model_object("diffusion_model")
    patch = getattr(diffusion, "patch_size", getattr(diffusion, "patch", 1))
    if isinstance(patch, (tuple, list)):
        patch = max(patch)
    return math.lcm(8, downscale * int(patch), int(vae.spacial_compression_encode()))


def plan_from_settings(width, height, settings):
    width, height = target_size(width, height, settings.get("upscale_by", 1.5), settings.get("upscale_connected", False))
    return make_plan(width, height, **{key: settings[key] for key in ("columns", "rows", "expand_percent") if key in settings})


@PromptServer.instance.routes.post("/smart-tile-refine/plan")
async def preview_plan(request):
    try:
        body = await request.json()
        return web.json_response(plan_from_settings(int(body["width"]), int(body["height"]), body))
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        return web.json_response({"error": str(error)}, status=400)


class UpscaleProgress:
    def __init__(self, steps, update):
        self.steps, self.current, self.update_fraction = steps, 0, update

    def update(self, count):
        self.current += count
        self.update_fraction(min(1.0, self.current / self.steps))


def upscale_with_model(model, source, width, height, update):
    scale = float(model.scale)
    if scale <= 1 and (width > source.shape[2] or height > source.shape[1]):
        raise ValueError("所接模型没有放大能力，请使用倍率大于 1 的放大模型。")
    passes = max(1, math.ceil(math.log(max(width / source.shape[2], height / source.shape[1]), scale))) if scale > 1 else 1
    for index in range(passes):
        comfy.model_management.throw_exception_if_processing_interrupted()
        if source.shape[1] * source.shape[2] * scale ** 2 > 256 * 1024 * 1024:
            raise ValueError("放大模型中间画布超过 256 MP，请减小输入或放大倍率。")
        memory = (512 * 512 * 3) * source.element_size() * max(scale, 1) * 384 + source.nelement() * source.element_size()
        comfy.model_management.load_models_gpu([model.patcher], memory_required=memory, force_full_load=True)
        pixels = source.movedim(-1, 1).to(model.patcher.load_device)
        tile = 512
        while True:
            steps = comfy.utils.get_tiled_scale_steps(pixels.shape[3], pixels.shape[2], tile_x=tile, tile_y=tile, overlap=32)
            progress = UpscaleProgress(steps, lambda fraction: update((index + fraction) / passes))
            try:
                result = comfy.utils.tiled_scale(pixels, lambda crop: model(crop.float()), tile_x=tile, tile_y=tile,
                                                overlap=32, upscale_amount=scale, pbar=progress, output_device="cpu")
                break
            except Exception as error:
                comfy.model_management.raise_non_oom(error)
                tile //= 2
                if tile < 128:
                    raise
        source = result.movedim(1, -1).clamp_(0, 1)
        del pixels, result
    # Enlargement comes from the connected model. Resampling only reduces
    # its native output to the requested final canvas.
    return resize(source, width, height)


class SmartTileRefine:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",), "model": ("MODEL",),
            "positive": ("CONDITIONING",), "negative": ("CONDITIONING",), "vae": ("VAE",),
            "upscale_by": ("FLOAT", {"default": 1.5, "min": 1, "max": 8, "step": 0.05}),
            "columns": ("INT", {"default": 2, "min": 1, "max": 8}),
            "rows": ("INT", {"default": 2, "min": 1, "max": 8}),
            "expand_percent": ("FLOAT", {"default": 15, "min": 0, "max": 50, "step": 1}),
            "redraw_mode": (["Independent tiles", "S-shaped sequence"],),
            "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
            "cfg": ("FLOAT", {"default": 1.0, "min": 0, "max": 100, "step": 0.1}),
            "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
            "scheduler": (comfy.samplers.KSampler.SCHEDULERS,),
            "denoise": ("FLOAT", {"default": 0.3, "min": 0, "max": 1, "step": 0.01}),
            "color_correction": ("BOOLEAN", {"default": True}),
            "color_strength": ("FLOAT", {"default": 0.5, "min": 0, "max": 1, "step": 0.05}),
            "batch_size": ("INT", {"default": 1, "min": 1, "max": 4}),
        }, "optional": {"upscale_model": ("UPSCALE_MODEL",)}, "hidden": {"unique_id": "UNIQUE_ID"}}

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "refine"
    CATEGORY = "image/Smart Tile Refine"

    def refine(self, image, model, positive, negative, vae, upscale_by, columns, rows, expand_percent,
               redraw_mode, seed, steps, cfg, sampler_name, scheduler, denoise,
               color_correction=True, color_strength=0.5, batch_size=1, upscale_model=None, unique_id=None):
        started = time.perf_counter()
        if image.ndim != 4 or image.shape[-1] not in (3, 4) or image.shape[0] < 1:
            raise ValueError("请输入 RGB/RGBA 图片。")
        if redraw_mode not in ("Independent tiles", "S-shaped sequence"):
            raise ValueError("Unknown redraw method.")
        settings = dict(upscale_by=upscale_by, upscale_connected=upscale_model is not None,
                        columns=columns, rows=rows, expand_percent=expand_percent)
        plan = plan_from_settings(image.shape[2], image.shape[1], settings)
        if image.shape[0] * plan["width"] * plan["height"] > MAX_IMAGE_PIXELS:
            raise ValueError("图片批次的总画布超过 64 MP，请拆成多个批次。")
        alignment = pixel_alignment(model, vae) if denoise > 0 else 16
        outputs = []
        progress = comfy.utils.ProgressBar(1000, node_id=unique_id)
        run_id = uuid.uuid4().hex
        payload = {"run_id": run_id, "plan": plan, "settings": settings,
                   "source_size": [image.shape[2], image.shape[1]], "running": True}
        last_progress = 0.0

        def publish(data):
            server = PromptServer.instance
            if unique_id is not None and server.client_id is not None:
                server.send_sync("smart-tile-refine.preview", {"node": str(unique_id), "run_id": run_id,
                                 "settings": settings, "source_size": payload["source_size"], **data}, server.client_id)

        def overall(value, tile_progress=None):
            nonlocal last_progress
            last_progress = max(last_progress, min(1.0, value))
            progress.update_absolute(round(last_progress * 1000))
            publish({"progress": last_progress, "tile_progress": tile_progress, "running": True})

        for batch_index in range(image.shape[0]):
            comfy.model_management.throw_exception_if_processing_interrupted()
            source = image[batch_index:batch_index + 1, :, :, :3].detach().to(device="cpu", dtype=torch.float32)
            tile_progress = {tile["id"]: 0.0 for tile in plan["tiles"]}
            payload.update(thumbnail=thumbnail(source), tile_progress=tile_progress.copy(), progress=batch_index/image.shape[0])
            publish(payload)
            up_weight = (0.12 if denoise > 0 else 1.0) if upscale_model is not None else 0.0
            if upscale_model is not None:
                source = upscale_with_model(upscale_model, source, plan["width"], plan["height"],
                    lambda fraction: overall((batch_index + up_weight * fraction) / image.shape[0]))
                payload["thumbnail"] = thumbnail(source)
                publish({"thumbnail": payload["thumbnail"]})
            if denoise == 0:
                outputs.append(source)
                tile_progress = {tile["id"]: 1.0 for tile in plan["tiles"]}
                overall((batch_index + 1) / image.shape[0], tile_progress)
                continue
            order = sorted(plan["tiles"], key=lambda t: (t["row"], t["col"] if t["row"] % 2 == 0 else -t["col"])) if redraw_mode == "S-shaped sequence" else plan["tiles"]
            merger = TileMerger(source, plan)
            cursor = 0
            while cursor < len(order):
                comfy.model_management.throw_exception_if_processing_interrupted()
                group, padded = [], []
                limit = 1 if redraw_mode == "S-shaped sequence" else batch_size
                while cursor + len(group) < len(order) and len(group) < limit:
                    tile = order[cursor + len(group)]
                    x0, y0, x1, y1 = tile["crop"]
                    crop = merger.context(tile) if redraw_mode == "S-shaped sequence" else source[:, y0:y1, x0:x1]
                    pixels = pad_tile(crop, alignment)
                    if group and pixels.shape != padded[0].shape:
                        break
                    group.append(tile)
                    padded.append(pixels)

                def group_progress(fraction):
                    for tile in group:
                        tile_progress[tile["id"]] = fraction
                    fraction_done = (cursor + len(group) * fraction) / len(order)
                    overall((batch_index + up_weight + (1-up_weight)*fraction_done) / image.shape[0], tile_progress.copy())

                group_progress(0.01)
                pixels = torch.cat(padded, dim=0)
                latent = vae.encode(pixels)
                latent = comfy.sample.fix_empty_latent_channels(model, latent)
                noise = comfy.sample.prepare_noise(latent, seed, [t["id"] + batch_index * len(order) for t in group])
                group_progress(0.06)
                def callback(step, x0, x, total_steps):
                    group_progress(0.06 + 0.84 * (step + 1) / max(1, total_steps))
                samples = comfy.sample.sample(model, noise, steps, cfg, sampler_name, scheduler, positive, negative,
                                              latent, denoise=denoise, callback=callback, disable_pbar=True, seed=seed)
                decoded = vae.decode(samples)
                if decoded.ndim == 5:
                    decoded = decoded.reshape(-1, *decoded.shape[-3:])
                decoded = resize(decoded.to(device="cpu", dtype=torch.float32), pixels.shape[2], pixels.shape[1])
                group_progress(0.95)
                for index, tile in enumerate(group):
                    x0, y0, x1, y1 = tile["crop"]
                    result = decoded[index:index + 1, :y1 - y0, :x1 - x0, :3]
                    if color_correction:
                        result = color_correct(result, source[:, y0:y1, x0:x1], color_strength)
                    merger.add(tile, result)
                group_progress(1.0)
                cursor += len(group)
                del latent, noise, samples, decoded, pixels, padded
            outputs.append(merger.finish())
            del merger
        payload.update(tile_progress=tile_progress, progress=1.0, running=False, seconds=round(time.perf_counter()-started,2))
        publish(payload)
        logging.info("[SmartTileRefine] %s×%s, %s×%s tiles, %.2fs", plan["width"], plan["height"], columns, rows, payload["seconds"])
        return {"ui": {"smart_tile": [payload]}, "result": (torch.cat(outputs, dim=0),)}
