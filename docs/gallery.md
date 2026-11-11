# 效果对比

[返回首页](../README.md) · [使用说明](usage.md) · [完整参数 JSON](assets/gallery/parameters.json)

三组原图均使用本项目新编写的提示词重新生成。每组只比较分块前和分块后的完整图像，使用相同视野展示。分块后为本节点实际输出，图片未额外锐化、调色或修饰。

共同模型设置：Krea2 INT8、匹配的 Qwen 文本编码器与 VAE，CFG 1、Euler / Simple、AuraFlow shift 1.15。每组的 LoRA、放大倍率和步数分别列于下表。测试设备为 RTX 4060 Laptop 8 GB、32 GB RAM。

## 1. 雨后湖畔电车站 / Lakeside tram stop

![分块前后整图对比](assets/gallery/lakeside-comparison.webp)

**图 1.** 左：分块前原图；右：分块后完整输出。

[分块前 PNG](assets/gallery/lakeside-source.png) · [分块后 PNG](assets/gallery/lakeside-refined.png)

| 参数 | 数值 |
| --- | --- |
| 尺寸 | 1280×720 → 2560×1440 |
| 放大模型 / 倍率 | 4x-AnimeSharp / 2× |
| LoRA / 权重 | `kuka\krea2-kuka-style-v1_c1-st8000.safetensors` / 1.0 |
| 原图步数 / 重绘步数 | 12 / 8 |
| CFG / 采样 | 1 / Euler + Simple |
| 分块 / 延展 | 5×4 / 每侧 15% |
| 重绘方式 / 强度 | 分块独立重绘 / 0.25 |
| 种子 | 原图 2026111121；精修 2026111221 |
| 颜色校正 / 单次数量 | 开启 0.50 / 1 |
| 总任务耗时 | 原图 130.63 s；分块重绘 631.81 s |

<details>
<summary>提示词 / Prompts</summary>

**原图提示词**

```text
Wide landscape anime illustration, hand-painted textured brushwork, delicate clean linework. A quiet lakeside tram stop after rain in early summer. On the left foreground, a young adult woman with long dark brown hair, a cream raincoat over a muted blue dress and brown ankle boots sits sideways on a wooden bench, holding a closed red umbrella, her relaxed face in three-quarter profile looking toward the lake. On the right, one vintage mint-green tram is stopped beside the platform, warm amber light in its windows, clear perspective and simple coherent construction. Wet stone pavement reflects the tram and the pale sky. A small cluster of white hydrangeas grows beside the bench. Beyond the platform, a broad blue lake, a distant small white sailboat and layered lavender mountains under soft broken clouds. A few leafy branches frame the upper left corner. Open space over the lake in the center, distinct foreground and background, balanced cinematic composition, soft afternoon sunlight after rain, restrained teal, cream and warm gold palette, detailed environmental illustration, no writing, no lettering, no watermark.
```

**分块重绘提示词**

```text
Hand-painted anime environmental illustration, delicate clean linework, natural facial features, textured fabric, coherent tram windows and metal edges, subtle wet stone reflections, soft foliage, restrained teal cream and warm gold colors, preserve the existing composition and painted texture.
```

负面提示词为空。

</details>

[原图生成工作流（API JSON）](../examples/lakeside_source_api.json) · [分块重绘工作流](../examples/krea2_refine.json)

原图使用 Kuka 风格 LoRA、12 步生成；分块精修使用同一 LoRA、8 步。

## 2. 玻璃温室 / Botanical glasshouse

![分块前后整图对比](assets/gallery/glasshouse-comparison.webp)

**图 2.** 左：分块前原图；右：分块后完整输出。

[分块前 PNG](assets/gallery/glasshouse-source.png) · [分块后 PNG](assets/gallery/glasshouse-refined.png)

| 参数 | 数值 |
| --- | --- |
| 尺寸 | 896×640 → 1344×960 |
| 放大模型 / 倍率 | 4x-AnimeSharp / 1.5× |
| LoRA / 权重 | `krea2\krea2_turbo_4step_rank_64_lora_comfyui.safetensors` / 1.0 |
| 原图步数 / 重绘步数 | 4 / 4 |
| CFG / 采样 | 1 / Euler + Simple |
| 分块 / 延展 | 2×2 / 每侧 15% |
| 重绘方式 / 强度 | S形依次重绘 / 0.24 |
| 种子 | 原图 2026111102；精修 2026111202 |
| 颜色校正 / 单次数量 | 开启 0.50 / 1 |
| 总任务耗时 | 原图 39.92 s；分块重绘 86.61 s |

<details>
<summary>提示词 / Prompts</summary>

**原图提示词**

```text
An original gouache and ink illustration of a quiet Victorian botanical glasshouse interior, a narrow red brick path curves between large fern beds, terracotta pots with varied leafy plants, slim green painted iron columns support tall glass panes, warm morning sunlight, soft leaf shadows on the ground, one shallow stone fountain in the distance, natural asymmetrical arrangement, no people, sage green, terracotta and creamy yellow palette, carefully drawn architectural perspective, richly varied foliage with clear shapes, matte paper texture, no lettering, no watermark.
```

**分块重绘提示词**

```text
Keep the existing architectural perspective, plant placement, palette and gouache style. Refine leaf veins, iron joints, terracotta surfaces, brick edges and subtle painted textures. Preserve broad soft lighting and avoid excessive grain.
```

负面提示词为空。

</details>

## 3. 山间茶屋 / Mountain teahouse

![分块前后整图对比](assets/gallery/teahouse-comparison.webp)

**图 3.** 左：分块前原图；右：分块后完整输出。

[分块前 PNG](assets/gallery/teahouse-source.png) · [分块后 PNG](assets/gallery/teahouse-refined.png)

| 参数 | 数值 |
| --- | --- |
| 尺寸 | 768×768 → 1152×1152 |
| 放大模型 / 倍率 | 4x-AnimeSharp / 1.5× |
| LoRA / 权重 | `krea2\krea2_turbo_4step_rank_64_lora_comfyui.safetensors` / 1.0 |
| 原图步数 / 重绘步数 | 4 / 4 |
| CFG / 采样 | 1 / Euler + Simple |
| 分块 / 延展 | 3×3 / 每侧 15% |
| 重绘方式 / 强度 | 分块独立重绘 / 0.3 |
| 种子 | 原图 2026111103；精修 2026111203 |
| 颜色校正 / 单次数量 | 开启 0.50 / 1 |
| 总任务耗时 | 原图 29.04 s；分块重绘 148.79 s |

<details>
<summary>提示词 / Prompts</summary>

**原图提示词**

```text
An original isometric fantasy illustration of a small cedar teahouse on a mossy mountain ledge, a curved green ceramic tile roof, warm amber light inside paper windows, a stone footbridge crosses a narrow stream beside the house, a wind-shaped pine tree on one side, ferns and small rounded stones, layered misty mountains far behind, dusk blue atmosphere with warm accents, a balanced square composition, clear miniature architecture, hand-painted game environment art, varied organic textures, no people, no lettering, no watermark.
```

**分块重绘提示词**

```text
Preserve the existing isometric geometry and all object positions. Refine cedar wood grain, individual ceramic roof tiles, moss, stone edges, pine needles and small water ripples. Keep the same hand-painted fantasy illustration, atmospheric blue and amber colors, clean controlled texture.
```

负面提示词为空。

</details>

## 复现步骤

1. 下载分块前原图，通过 ComfyUI 加载图像节点上传。
2. 导入 [Krea2 接线示例](../examples/krea2_refine.json)，选择该组对应的 LoRA、步数以及匹配的文本编码器和 VAE。
3. 外部正面文本编码节点填入本页的分块重绘提示词，负面留空。
4. 使用表中的分块、延展、强度、种子和放大倍率，连接 4x-AnimeSharp 后运行。

总任务时间包含模型加载与缓存影响。模型、LoRA、软件版本或设备变化会影响固定种子的生成细节。

English: each figure compares the full input image (left) with the full node output (right), using the same field of view. Prompts, seeds and settings are included.
