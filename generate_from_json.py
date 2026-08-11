"""Generate a QR image from a JSON payload shaped like future frontend data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from qr_backend import (
    LogoProtectedAreaError,
    LogoRequest,
    QRCoreRequest,
    QRGenerationError,
    QRRequest,
    QRResult,
    generate_qr,
)
from qr_backend.models import RGBA


DEFAULT_REQUEST_FILE = Path(__file__).with_name("examples") / "request_template.json"


def parse_rgba(value: object, field_name: str) -> RGBA:
    """Convert a frontend JSON RGB/RGBA array to the backend RGBA tuple."""

    if not isinstance(value, list) or len(value) not in {3, 4}:
        raise ValueError(f"{field_name} 必须是包含 3 或 4 个整数的 JSON 数组。")
    channels = value + [255] if len(value) == 3 else value
    if any(type(channel) is not int or not 0 <= channel <= 255 for channel in channels):
        raise ValueError(f"{field_name} 的各通道必须是 0 到 255 的整数。")
    return tuple(channels)  # type: ignore[return-value]


def _optional_int(data: dict[str, Any], key: str) -> int | None:
    value = data.get(key)
    return None if value is None else int(value)


def build_request(payload: dict[str, Any], base_dir: Path) -> QRRequest:
    """Translate one frontend-like JSON object into the public request model."""

    core_data = payload["core"]
    if not isinstance(core_data, dict):
        raise ValueError("core 必须是 JSON 对象。")

    use_eci = core_data.get("use_eci", True)
    if type(use_eci) is not bool:
        raise ValueError("core.use_eci 必须使用 JSON 布尔值 true 或 false。")
    version = _optional_int(core_data, "version")
    if version is not None and not 1 <= version <= 40:
        raise ValueError("core.version 必须是 1 到 40，或使用 null 自动选择。")

    core = QRCoreRequest(
        text=str(core_data["text"]),
        error_level=str(core_data["error_level"]).upper(),  # type: ignore[arg-type]
        encoding=str(core_data.get("encoding", "utf-8")),
        use_eci=use_eci,
        quiet_zone_modules=int(core_data.get("quiet_zone_modules", 4)),
        version=version,
    )

    size_mode = str(payload["size_mode"])
    if size_mode not in {"fixed_size", "fixed_module"}:
        raise ValueError("size_mode 只能是 fixed_size 或 fixed_module。")

    logo: LogoRequest | None = None
    logo_data = payload.get("logo")
    if logo_data is not None:
        if not isinstance(logo_data, dict):
            raise ValueError("logo 必须是 JSON 对象或 null。")
        logo_path = logo_data.get("file_path")
        if logo_path:
            path = Path(str(logo_path))
            if not path.is_absolute():
                path = (base_dir / path).resolve()
            logo_path = str(path)
        logo_enabled = logo_data.get("enabled", False)
        if type(logo_enabled) is not bool:
            raise ValueError("logo.enabled 必须使用 JSON 布尔值 true 或 false。")
        transparent_background = logo_data.get("transparent_background", True)
        if type(transparent_background) is not bool:
            raise ValueError(
                "logo.transparent_background 必须使用 JSON 布尔值 true 或 false。"
            )
        logo = LogoRequest(
            enabled=logo_enabled,
            file_path=logo_path,
            width=_optional_int(logo_data, "width"),
            height=_optional_int(logo_data, "height"),
            canvas_width=_optional_int(logo_data, "canvas_width"),
            canvas_height=_optional_int(logo_data, "canvas_height"),
            shape=str(logo_data.get("shape", "square")),  # type: ignore[arg-type]
            corner_radius=int(logo_data.get("corner_radius", 0)),
            padding=int(logo_data.get("padding", 0)),
            x=_optional_int(logo_data, "x"),
            y=_optional_int(logo_data, "y"),
            transparent_background=transparent_background,
            background_color=parse_rgba(
                logo_data.get("background_color", [255, 255, 255, 255]),
                "logo.background_color",
            ),
        )

    return QRRequest(
        core=core,
        size_mode=size_mode,  # type: ignore[arg-type]
        qr_width=_optional_int(payload, "qr_width"),
        qr_height=_optional_int(payload, "qr_height"),
        pixels_per_module=_optional_int(payload, "pixels_per_module"),
        canvas_width=_optional_int(payload, "canvas_width"),
        canvas_height=_optional_int(payload, "canvas_height"),
        qr_position_x=_optional_int(payload, "qr_position_x"),
        qr_position_y=_optional_int(payload, "qr_position_y"),
        foreground_color=parse_rgba(
            payload.get("foreground_color", [0, 0, 0, 255]),
            "foreground_color",
        ),
        background_color=parse_rgba(
            payload.get("background_color", [255, 255, 255, 0]),
            "background_color",
        ),
        canvas_color=parse_rgba(
            payload.get("canvas_color", [255, 255, 255, 255]),
            "canvas_color",
        ),
        logo=logo,
        output_format=str(payload.get("output_format", "png")).lower(),  # type: ignore[arg-type]
        dpi=_optional_int(payload, "dpi"),
    )


def resolve_output_path(payload: dict[str, Any], base_dir: Path, result: QRResult) -> Path:
    """Resolve and validate the requested output filename."""

    configured = payload.get("output_path", f"output/generated_qr.{result.output_format}")
    path = Path(str(configured))
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    expected_suffix = f".{result.output_format}"
    if not path.suffix:
        path = path.with_suffix(expected_suffix)
    elif path.suffix.lower() != expected_suffix:
        raise ValueError(
            f"output_path 后缀应为 {expected_suffix}，当前为 {path.suffix}。"
        )
    return path


def generate_from_payload(
    payload: dict[str, Any],
    base_dir: Path,
) -> tuple[QRResult, Path]:
    """Build, generate, and persist one frontend-like request."""

    request = build_request(payload, base_dir)
    result = generate_qr(request)
    output_path = resolve_output_path(payload, base_dir, result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result.image_bytes)
    return result, output_path


def result_summary(result: QRResult, output_path: Path) -> dict[str, object]:
    """Return console-friendly generation metadata."""

    return {
        "success": True,
        "output_path": str(output_path),
        "output_format": result.output_format,
        "version": result.version,
        "error_level": result.error_level,
        "matrix_size": result.matrix_size,
        "total_modules": result.total_modules,
        "qr_size": [result.qr_width, result.qr_height],
        "canvas_size": [result.canvas_width, result.canvas_height],
        "qr_position": [result.qr_x, result.qr_y],
        "size_mode": result.size_mode,
        "pixels_per_module": result.pixels_per_module,
        "logo_used": result.logo_used,
        "dpi": result.dpi,
        "byte_count": len(result.image_bytes),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="读取前端风格的 JSON 数据并生成二维码。"
    )
    parser.add_argument(
        "request_file",
        nargs="?",
        type=Path,
        default=DEFAULT_REQUEST_FILE,
        help="请求 JSON 文件，默认使用 examples/request_template.json。",
    )
    args = parser.parse_args(argv)
    request_file = args.request_file.resolve()

    try:
        payload = json.loads(request_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON 文件最外层必须是对象。")
        result, output_path = generate_from_payload(payload, request_file.parent)
    except LogoProtectedAreaError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except (QRGenerationError, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        error = {
            "success": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }
        print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result_summary(result, output_path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
