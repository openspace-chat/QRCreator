"""PNG, JPEG, and true-vector QR SVG exporters."""

import base64
import mimetypes
from html import escape
from io import BytesIO
from pathlib import Path

from PIL import Image

from .exceptions import LogoDecodeError, RenderingError
from .models import LogoLayout, LogoRequest, QRAnalysis, QRLayout, RGBA


def export_png(image: Image.Image, dpi: int | None = None) -> bytes:
    """Encode RGBA pixels as PNG, using DPI only as metadata."""

    output = BytesIO()
    options: dict[str, object] = {}
    if dpi is not None:
        if dpi <= 0:
            raise RenderingError("DPI metadata must be positive.")
        options["dpi"] = (dpi, dpi)
    image.convert("RGBA").save(output, format="PNG", **options)
    return output.getvalue()


def export_jpeg(image: Image.Image, dpi: int | None = None) -> bytes:
    """Encode opaque pixels as a high-quality RGB JPEG."""

    output = BytesIO()
    options: dict[str, object] = {
        "quality": 95,
        "subsampling": 0,
        "optimize": True,
    }
    if dpi is not None:
        if dpi <= 0:
            raise RenderingError("DPI metadata must be positive.")
        options["dpi"] = (dpi, dpi)
    image.convert("RGB").save(output, format="JPEG", **options)
    return output.getvalue()


def _number(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 1e-10:
        return str(rounded)
    return f"{value:.10f}".rstrip("0").rstrip(".")


def _svg_paint(color: RGBA) -> str:
    red, green, blue, alpha = color
    paint = f'fill="#{red:02x}{green:02x}{blue:02x}"'
    if alpha != 255:
        paint += f' fill-opacity="{alpha / 255:.6f}"'
    return paint


def _logo_shape_svg(
    layout: LogoLayout,
    global_x: int,
    global_y: int,
    fill: str,
) -> str:
    x = global_x + layout.cutout_x
    y = global_y + layout.cutout_y
    width = layout.cutout_width
    height = layout.cutout_height
    if layout.shape == "circle":
        return (
            f'<ellipse cx="{_number(x + width / 2)}" cy="{_number(y + height / 2)}" '
            f'rx="{_number(width / 2)}" ry="{_number(height / 2)}" {fill}/>'
        )
    radius = 0 if layout.shape == "square" else max(
        0, min(layout.corner_radius, width / 2, height / 2)
    )
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{_number(radius)}" ry="{_number(radius)}" {fill}/>'
    )


def _embedded_logo_svg(request: LogoRequest, layout: LogoLayout, qr_layout: QRLayout) -> str:
    if not request.file_path:
        raise LogoDecodeError("An enabled logo requires file_path.")
    path = Path(request.file_path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LogoDecodeError(f"Unable to read logo: {path}") from exc
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else mimetypes.guess_type(path.name)[0]
    if not mime or not mime.startswith("image/"):
        raise LogoDecodeError(f"Unsupported logo type: {path.suffix}")
    payload = base64.b64encode(raw).decode("ascii")
    x = qr_layout.qr_x + layout.logo_x
    y = qr_layout.qr_y + layout.logo_y
    return (
        f'<image x="{x}" y="{y}" width="{layout.logo_width}" height="{layout.logo_height}" '
        f'preserveAspectRatio="none" href="data:{escape(mime)};base64,{payload}"/>'
    )


def export_svg(
    analysis: QRAnalysis,
    layout: QRLayout,
    foreground_color: RGBA,
    background_color: RGBA,
    canvas_color: RGBA,
    logo_request: LogoRequest | None = None,
    logo_layout: LogoLayout | None = None,
) -> bytes:
    """Render the matrix directly as SVG rectangles, never as a base64 QR PNG."""

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{layout.canvas_width}" '
            f'height="{layout.canvas_height}" viewBox="0 0 {layout.canvas_width} {layout.canvas_height}">'
        ),
        f'<rect width="{layout.canvas_width}" height="{layout.canvas_height}" {_svg_paint(canvas_color)}/>',
    ]

    has_logo = bool(logo_request and logo_request.enabled and logo_layout)
    if has_logo:
        parts.extend(
            [
                '<defs><mask id="qr-cutout-mask" maskUnits="userSpaceOnUse">',
                f'<rect width="{layout.canvas_width}" height="{layout.canvas_height}" fill="white"/>',
                _logo_shape_svg(logo_layout, layout.qr_x, layout.qr_y, 'fill="black"'),
                '</mask></defs>',
                '<g mask="url(#qr-cutout-mask)">',
            ]
        )
    else:
        parts.append("<g>")

    parts.append(
        f'<rect x="{layout.qr_x}" y="{layout.qr_y}" width="{layout.qr_width}" '
        f'height="{layout.qr_height}" {_svg_paint(background_color)}/>'
    )
    module_width = layout.qr_width / analysis.total_modules
    module_height = layout.qr_height / analysis.total_modules
    quiet = analysis.quiet_zone_modules
    for y, row in enumerate(analysis.matrix):
        run_start: int | None = None
        for x in range(analysis.matrix_size + 1):
            dark = x < analysis.matrix_size and row[x]
            if dark and run_start is None:
                run_start = x
            elif not dark and run_start is not None:
                rect_x = layout.qr_x + (quiet + run_start) * module_width
                rect_y = layout.qr_y + (quiet + y) * module_height
                rect_width = (x - run_start) * module_width
                parts.append(
                    f'<rect x="{_number(rect_x)}" y="{_number(rect_y)}" '
                    f'width="{_number(rect_width)}" height="{_number(module_height)}" '
                    f'{_svg_paint(foreground_color)}/>'
                )
                run_start = None
    parts.append("</g>")
    if has_logo:
        if not logo_request.transparent_background:
            parts.append(
                _logo_shape_svg(
                    logo_layout,
                    layout.qr_x,
                    layout.qr_y,
                    _svg_paint(logo_request.background_color),
                )
            )
        parts.append(_embedded_logo_svg(logo_request, logo_layout, layout))
    parts.append("</svg>")
    return "".join(parts).encode("utf-8")
