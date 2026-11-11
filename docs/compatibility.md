# 兼容与验证

[返回首页](../README.md)

## 运行要求

| 项目 | 要求 |
| --- | --- |
| ComfyUI | 0.41.0+ |
| ComfyUI 前端 | 1.55.17+ |
| Python | 3.10+ |
| Python 依赖 | ComfyUI 自带的 torch、numpy、Pillow、aiohttp |
| 接口 | MODEL、VAE、正负 CONDITIONING；可选 UPSCALE_MODEL |
| 输出 | 一个 IMAGE 接口，支持输入批次，输出 RGB |

节点没有模型下载器、云端生成接口或额外网络请求。图片预览和规划通过本机 ComfyUI 完成。CI 的依赖下载仅用于开发检查。

## 实机验证

Windows 11、Python 3.12.10、ComfyUI 0.41.0、前端 1.55.17、RTX 4060 Laptop 8 GB、系统内存 32 GB。生成使用 Krea2 INT8、匹配的 Qwen 编码器和 VAE；已实际执行 Kuka 风格 LoRA 的 12 步原图与 5×4、8 步重绘，以及 4 步 Turbo LoRA 的两组演示。

已实测独立分块、S 形分块、4x-AnimeSharp 模型放大、单次双块处理、不能整除的尺寸恢复、累计进度及浏览器接图、缩放和中英切换。公开演示的参数和耗时见[展示页](gallery.md)。

MODEL/VAE 接口可接入其他普通图生图模型；当前 GPU 展示采用 Krea2。其他模型的 CFG、步数、VAE 和 latent 要求应按各自配置。

## 自动检查

- 450 组随机分块覆盖，横纵各 1～8，包括 1×1 与 8×8。
- 边界、延展、整数余数分配与尺寸限制。
- 恒等重建、四块交汇、颜色校正和顺序上下文强度。
- 条件传递、普通 VAE、分组噪声 ID、累计进度。
- 前端先显示图像、失败重试、悬停隐藏、无图折叠、语言回退与自由尺寸。
- 发布包文件清单和本机路径检查。

CI 在 Windows/Linux、Python 3.10/3.12 上运行 CPU 和前端模拟回归；结果见 [Actions](https://github.com/Kousin-ryou/ComfyUI-SmartTileRefine/actions)。

## 使用边界

- 整批输出画布最多 64 Mi 像素，单边最多 65536；模型放大中间画布最多 256 Mi 像素。
- 每轴 1～8 块，无额外单块 2048/3 MP 门槛；可处理尺寸取决于模型和显存。
- 极大画布的 CPU 融合也需要足够系统内存。
- 复杂上游首次运行后取得真实预览；运行前主要反映可追溯图片和尺寸。
- 不提供内部局部视觉提示词、Edit 专用适配器和透明通道恢复。
- 模型、LoRA、ComfyUI 或设备变化会影响固定种子的生成细节。

## 安装渠道

GitHub 与 Release ZIP 可直接手动安装；支持 Git URL 的 Manager 版本可使用仓库地址。Registry 是独立渠道，需要有效 Publisher ID 和专用发布密钥；GitHub Release 的使用不依赖 Registry 收录。
