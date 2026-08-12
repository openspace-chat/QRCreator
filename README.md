# QRCreator

**在线工具**：访问 [QR Studio - 二维码设计台](https://www.openspace.chat/QRCode/index.html)，快速生成带参数、Logo 和自定义颜色的二维码。

一个使用 Python 编写的二维码生成核心。项目使用 Segno 将文本编码为标准 QR 矩阵，
并负责尺寸布局、颜色绘制、Logo 安全区域检查、画布合成以及 PNG、JPG、SVG 导出。

本仓库只包含二维码后端核心和 JSON 测试入口，不包含网页前端、HTTP API、数据库、
用户系统或网站部署配置。

## 功能

- 支持标准二维码 V1–V40。
- 支持 L、M、Q、H 四种纠错等级。
- 支持固定二维码尺寸和固定模块像素两种布局模式。
- 支持 PNG、JPG/JPEG 和 SVG 输出。
- 支持 PNG、JPG/JPEG、SVG Logo。
- 支持圆形、正方形和圆角正方形 Logo 画布。
- Logo 强制居中，并保护二维码定位、时序、校正、格式和版本信息等关键模块。
- 支持透明画布和 RGBA 颜色。
- 支持 UTF-8、中文及其他多语言文本。

## 目录结构

```text
qr_backend/                    二维码编码、布局、绘制和导出核心
tests/                         自动化测试
examples/request_template.json
                               JSON 请求模板
generate_from_json.py          JSON 文件生成入口
requirements.txt               运行依赖
requirements-dev.txt           测试依赖
LICENSE                        MIT 许可证
```

## 安装

需要 Python 3.11 或更高版本。建议使用虚拟环境：

```bash
python -m venv .venv
```

Linux/macOS：

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 使用 JSON 模板

编辑 `examples/request_template.json`，然后运行：

```bash
python generate_from_json.py
```

默认输出位置为：

```text
output/generated_qr.png
```

也可以指定其他 JSON 文件：

```bash
python generate_from_json.py path/to/request.json
```

Logo 路径和输出路径如果使用相对路径，均以当前 JSON 文件所在目录为基准。

## JSON 主要参数

### 编码参数

| 参数 | 类型或范围 | 说明 |
|---|---|---|
| `core.text` | 字符串 | 写入二维码的实际内容 |
| `core.error_level` | `L` / `M` / `Q` / `H` | 纠错等级 |
| `core.encoding` | 字符串 | 推荐使用 `utf-8` |
| `core.use_eci` | `true` / `false` | 是否写入 ECI 编码标记 |
| `core.quiet_zone_modules` | 大于等于 `0` 的整数 | 四周静区模块数，标准场景通常使用 `4` |
| `core.version` | `1–40` 或 `null` | 指定版本；`null` 自动选择最低可用版本 |

### 尺寸参数

`size_mode` 有两种选择：

- `fixed_size`：`qr_width` 和 `qr_height` 决定二维码最终像素尺寸。
- `fixed_module`：`pixels_per_module` 决定每个模块的整数像素边长，二维码尺寸由版本决定。

`canvas_width` 和 `canvas_height` 决定最终画布尺寸。`qr_position_x` 与
`qr_position_y` 设置为 `null` 时，二维码自动居中。

### 颜色参数

颜色使用 RGB 或 RGBA 数组：

```json
[0, 0, 0]
```

```json
[0, 0, 0, 255]
```

每个通道范围为 `0–255`。RGB 会自动补为完全不透明；RGBA 第四个值为 Alpha。

| 参数 | 说明 |
|---|---|
| `foreground_color` | 二维码深色模块颜色 |
| `background_color` | 二维码图层背景颜色 |
| `canvas_color` | 最终画布颜色 |

### Logo 参数

| 参数 | 类型或范围 | 说明 |
|---|---|---|
| `logo.enabled` | `true` / `false` | 是否添加 Logo |
| `logo.file_path` | PNG、JPG、JPEG、SVG | Logo 文件路径 |
| `logo.width` / `logo.height` | 正整数 | Logo 本身尺寸，单位 px |
| `logo.canvas_width` / `logo.canvas_height` | 正整数 | Logo 扣除画布尺寸，单位 px |
| `logo.shape` | `circle` / `square` / `rounded_square` | Logo 画布形状 |
| `logo.corner_radius` | 大于等于 `0` 的整数 | 圆角半径，单位 px |
| `logo.transparent_background` | `true` / `false` | Logo 画布是否透明 |
| `logo.background_color` | RGBA 数组 | Logo 画布非透明时的背景色 |

Logo 默认居中。如果 Logo 画布覆盖二维码关键功能模块，生成会被拒绝，而不会擅自
移动或缩小 Logo。

### 输出参数

| 参数 | 类型或范围 | 说明 |
|---|---|---|
| `output_format` | `png` / `jpg` / `jpeg` / `svg` | 输出格式 |
| `dpi` | 正整数或 `null` | PNG/JPG 元数据，不改变像素尺寸；SVG 忽略 |
| `output_path` | 字符串 | 输出文件路径，扩展名须与格式一致 |

JPG 不支持透明度。如果需要透明背景，请使用 PNG 或 SVG。

## 直接在 Python 中使用

```python
from pathlib import Path

from qr_backend import QRCoreRequest, QRRequest, generate_qr

request = QRRequest(
    core=QRCoreRequest(
        text="https://www.openspace.chat/QRCode/index.html",
        error_level="H",
        encoding="utf-8",
        use_eci=True,
        version=None,
    ),
    size_mode="fixed_size",
    qr_width=300,
    qr_height=300,
    canvas_width=360,
    canvas_height=360,
    foreground_color=(0, 0, 0, 255),
    background_color=(255, 255, 255, 255),
    canvas_color=(255, 255, 255, 255),
    output_format="png",
    dpi=300,
)

result = generate_qr(request)
Path("generated_qr.png").write_bytes(result.image_bytes)
```

## 测试

安装测试依赖并运行：

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## 许可证

本项目使用 [MIT License](LICENSE)。你可以在保留版权与许可声明的前提下使用、修改、
分发和集成本项目。
