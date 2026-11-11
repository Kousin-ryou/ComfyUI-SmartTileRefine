# v1.0.1 · 分块高清重绘 / Smart Tile Refine

更新节点内可视化展示与演示材料。一个 ComfyUI 节点完成分块图生图、可选模型放大、颜色校正和高低频融合。

Updated in-node visualization and demonstration materials. One ComfyUI node for tiled img2img refinement, optional model upscaling, color correction and frequency-aware blending.

- 标准 MODEL、VAE、正负 CONDITIONING 接线，一个 IMAGE 输出。
- 自定义横纵块数、百分比延展，独立或 S 形依次重绘。
- 节点内预览、蓝色悬停延展、自由缩放、中英文界面。
- 完整安装、参数、Krea2 示例、排错及原理说明。
- Kuka LoRA 横屏演示：2 倍放大、5×4 分块、8 步重绘，仅保留整图比较；原图 12 步生成。
- 三组全新图像；分块前后两列整图对比。

## 安装 / Installation

下载 ZIP，解压到 `ComfyUI/custom_nodes/ComfyUI-SmartTileRefine`，重启服务并刷新网页；也可在 `custom_nodes` 中克隆仓库。

Extract the ZIP into `ComfyUI/custom_nodes/ComfyUI-SmartTileRefine`, restart ComfyUI and refresh the browser, or clone this repository into `custom_nodes`.

需要 / Requires: ComfyUI 0.41.0+, frontend 1.55.17+, Python 3.10+.

[使用说明 / Usage](https://github.com/Kousin-ryou/ComfyUI-SmartTileRefine/blob/main/docs/usage.md) · [原理图解 / Principles](https://github.com/Kousin-ryou/ComfyUI-SmartTileRefine/blob/main/docs/principles.md) · [效果对比 / Comparisons](https://github.com/Kousin-ryou/ComfyUI-SmartTileRefine/blob/main/docs/gallery.md)

附件 / Assets: installable ZIP and SHA256SUMS.txt. 模型文件不包含在安装包中 / Model weights are not included.
