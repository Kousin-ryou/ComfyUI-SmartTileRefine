# Contributing

欢迎提交问题和改进。Please keep changes focused and include a reproducible case.

## 检查 / Checks

在已有 ComfyUI Python 环境中运行，或另建环境安装 CPU 版 torch、numpy、Pillow、aiohttp。

```sh
python -m unittest discover -s tests -v
node tests/test_preview.mjs
node --check web/smart_tile_final.js
python scripts/package_release.py
```

Python tests exercise geometry, fusion and the node coordinator through lightweight ComfyUI doubles. Frontend tests exercise preview state and rendering with a simulated browser. Real GPU sampling and browser layout are verified separately; see [compatibility](docs/compatibility.md).

## 代码范围 / Scope

- 保留 `SmartTileRefine` 类名和现有输入键，界面翻译与序列化值分开维护。
- 使用 ComfyUI 原生采样、模型加载和中断机制，不在节点内下载模型。
- 坐标改动同时检查前端规划和实际执行；融合改动保留原图恒等重建检查。
- 不提交模型、密钥、本机绝对路径、私人工作流或带个人信息的日志。
- Release tags use `vMAJOR.MINOR.PATCH` and must match `pyproject.toml`.
