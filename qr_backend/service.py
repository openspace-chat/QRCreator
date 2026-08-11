"""High-level orchestration for the complete QR generation workflow."""

from .compositor import (
    apply_logo_cutout,
    composite_logo,
    create_canvas,
    load_logo_image,
    paste_qr_to_canvas,
)
from .exceptions import LogoProtectedAreaError, RenderingError
from .exporter import export_jpeg, export_png, export_svg
from .function_mask import build_protected_mask
from .layout import solve_layout
from .logo import check_logo_overlap, solve_logo_layout
from .models import LogoLayout, QRRequest, QRResult, RGBA
from .qr_encoder import analyze_qr
from .renderer import render_qr


def _has_transparency(color: RGBA) -> bool:
    return color[3] < 255


def _validate_jpeg_opacity(request: QRRequest) -> None:
    transparent_fields: list[str] = []
    for name, color in (
        ("foreground_color", request.foreground_color),
        ("background_color", request.background_color),
        ("canvas_color", request.canvas_color),
    ):
        if _has_transparency(color):
            transparent_fields.append(name)

    logo = request.logo
    if logo and logo.enabled:
        if logo.transparent_background:
            transparent_fields.append("logo.transparent_background")
        elif _has_transparency(logo.background_color):
            transparent_fields.append("logo.background_color")

    if transparent_fields:
        fields = ", ".join(transparent_fields)
        raise RenderingError(
            "JPEG does not support transparency. Use fully opaque colors and a "
            f"non-transparent logo background, or select PNG/SVG. Transparent setting(s): {fields}."
        )


def generate_qr(request: QRRequest) -> QRResult:
    """Generate PNG, JPEG, or SVG bytes and return metadata."""

    requested_output_format = request.output_format.lower()
    output_format = "jpg" if requested_output_format == "jpeg" else requested_output_format
    if output_format not in {"png", "jpg", "svg"}:
        raise RenderingError(f"Unsupported output format: {request.output_format!r}.")
    if output_format == "jpg":
        _validate_jpeg_opacity(request)

    analysis = analyze_qr(request.core)
    layout = solve_layout(request, analysis)

    logo_request = request.logo
    logo_layout: LogoLayout | None = None
    logo_used = bool(logo_request and logo_request.enabled)
    if logo_used:
        assert logo_request is not None
        logo_layout = solve_logo_layout(logo_request, layout)
        protected_mask = build_protected_mask(analysis.version)
        safety = check_logo_overlap(logo_layout, analysis, layout, protected_mask)
        if not safety.safe:
            raise LogoProtectedAreaError(safety)

    if output_format in {"png", "jpg"}:
        qr_image = render_qr(
            analysis,
            layout,
            request.foreground_color,
            request.background_color,
        )
        if logo_used:
            assert logo_request is not None and logo_layout is not None
            logo_fill = (
                (0, 0, 0, 0)
                if logo_request.transparent_background
                else logo_request.background_color
            )
            qr_image = apply_logo_cutout(qr_image, logo_layout, logo_fill)
            logo_image = load_logo_image(logo_request, logo_layout)
            qr_image = composite_logo(qr_image, logo_image, logo_layout)
        canvas = create_canvas(layout.canvas_width, layout.canvas_height, request.canvas_color)
        canvas = paste_qr_to_canvas(canvas, qr_image, layout.qr_x, layout.qr_y)
        image_bytes = (
            export_png(canvas, request.dpi)
            if output_format == "png"
            else export_jpeg(canvas, request.dpi)
        )
    elif output_format == "svg":
        image_bytes = export_svg(
            analysis,
            layout,
            request.foreground_color,
            request.background_color,
            request.canvas_color,
            logo_request if logo_used else None,
            logo_layout,
        )
    return QRResult(
        image_bytes=image_bytes,
        output_format=output_format,
        version=analysis.version,
        error_level=analysis.actual_error_level,
        matrix_size=analysis.matrix_size,
        total_modules=analysis.total_modules,
        qr_width=layout.qr_width,
        qr_height=layout.qr_height,
        canvas_width=layout.canvas_width,
        canvas_height=layout.canvas_height,
        qr_x=layout.qr_x,
        qr_y=layout.qr_y,
        size_mode=layout.size_mode,
        pixels_per_module=layout.pixels_per_module,
        logo_used=logo_used,
        dpi=request.dpi,
    )
