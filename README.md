# ComfyUI Smart Tile Refine · 分块高清重绘

[English](README.en.md) · [使用说明](docs/usage.md) · [原理图解](docs/principles.md) · [效果展示](docs/gallery.md) · [兼容与测试](docs/compatibility.md)

**一个节点完成分块图生图、可选模型放大、颜色校正与高低频融合，适合高分辨率插画精修。**

**An all-in-one ComfyUI node for tiled img2img refinement, optional model upscaling, color correction and frequency-aware blending.**

## 特点

- 普通 `MODEL / VAE / CONDITIONING` 接线，仅输出融合后的 `IMAGE`。
- 自定义横纵块数、百分比延展，整数坐标准确覆盖画布。
- 分块独立重绘或 S 形依次重绘，复用 ComfyUI 原生采样。
- 连接放大模型自动启用；未连接则保持输入尺寸。
- 节点内高清预览：连续白色网格、蓝色悬停延展，无图折叠。
- 简洁参数排布，自由调整节点大小，中英文跟随界面设置。

## 安装

在 `ComfyUI/custom_nodes` 中执行：

```sh
git clone https://github.com/Kousin-ryou/ComfyUI-SmartTileRefine.git
```

也可下载 [Release 安装包](https://github.com/Kousin-ryou/ComfyUI-SmartTileRefine/releases/latest)，解压成 `custom_nodes/ComfyUI-SmartTileRefine`。需要 **ComfyUI 0.41.0+、前端 1.55.17+、Python 3.10+**，使用 ComfyUI 自带的 torch、numpy、Pillow 和 aiohttp。详细步骤见[安装与更新](docs/usage.md#安装与更新)。

重启 ComfyUI、刷新网页后，搜索 **分块高清重绘**；英文界面搜索 **Tile Refine**。

## 快速上手

1. 接入图像、模型、正面条件、负面条件和匹配的 VAE。
2. 从 **2×2 分块、延展 15、重绘强度 0.20～0.30、单次数量 1** 开始。
3. 需要放大时接入 `UpscaleModelLoader`，设置放大倍率。
4. 输出接到普通预览或保存图像节点。步数、CFG、采样器按基础模型要求设置。

![处理流程](docs/assets/pipeline.png)

下载[通用接线示例](examples/basic_img2img.json)或[Krea2 示例](examples/krea2_refine.json)。导入后选择自己的模型、VAE 和输入图片；示例不包含模型文件。Krea2 4 步 LoRA 的设置见[专用说明](docs/usage.md#krea2-示例)。

## 展示与原理

三组演示均使用新编写的提示词生成原图，再由本节点实际重绘。每组提供完整图片、局部对比、提示词、种子与参数：**[查看效果展示](docs/gallery.md)**。

想了解延展如何计算、S 形如何传递上下文、颜色如何校正，以及高低频为何使用不同权重，请看 **[原理图解](docs/principles.md)**。

## 常见问题

- **人物变样或结构重复**：先降低重绘强度，避免每个局部提示词都要求生成整张场景。
- **显存不足**：单次数量设为 1，再增加横纵块数或减小延展。S 形模式始终逐块执行。
- **未接放大模型，倍率无效**：这是预期行为，输入会按原尺寸精修。
- **预览暂未出现**：加载图像可直接预览；复杂上游首次运行后同步实际图片。

完整说明见[参数与排错](docs/usage.md)。整批画布上限为 64 Mi 像素；每轴 1～8 块，无额外总块数限制。

## 开源

[MIT License](LICENSE) · [第三方说明](THIRD_PARTY_NOTICES.md) · [更新记录](CHANGELOG.md) · [问题反馈](https://github.com/Kousin-ryou/ComfyUI-SmartTileRefine/issues)

设计参考：[Ultimate SD Upscale](https://github.com/ssitu/ComfyUI_UltimateSDUpscale) 与 [Tiled Upscale & Refine](https://github.com/GianlucaMancuso/ComfyUI-TiledUpscale)。
