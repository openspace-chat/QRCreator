"""Logo geometry and protected-module overlap checks."""

from math import isclose

from .exceptions import LogoDecodeError
from .models import LogoLayout, LogoRequest, LogoSafetyResult, QRAnalysis, QRLayout


def solve_logo_layout(request: LogoRequest, qr_layout: QRLayout) -> LogoLayout:
    """Resolve logo and padded cutout rectangles in QR-local pixels."""

    if request.width is None or request.height is None:
        raise LogoDecodeError("An enabled logo requires width and height.")
    if request.width <= 0 or request.height <= 0 or request.padding < 0:
        raise LogoDecodeError("Invalid logo dimensions or padding.")
    if request.shape not in {"circle", "square", "rounded_square"}:
        raise LogoDecodeError(f"Unsupported logo cutout shape: {request.shape!r}.")

    logo_x = request.x if request.x is not None else (qr_layout.qr_width - request.width) // 2
    logo_y = request.y if request.y is not None else (qr_layout.qr_height - request.height) // 2
    cutout_width = request.canvas_width or request.width + 2 * request.padding
    cutout_height = request.canvas_height or request.height + 2 * request.padding
    if cutout_width < request.width or cutout_height < request.height:
        raise LogoDecodeError("Logo canvas cannot be smaller than the logo itself.")
    logo_center_x = logo_x + request.width / 2
    logo_center_y = logo_y + request.height / 2
    cutout_x = round(logo_center_x - cutout_width / 2)
    cutout_y = round(logo_center_y - cutout_height / 2)
    return LogoLayout(
        logo_x=logo_x,
        logo_y=logo_y,
        logo_width=request.width,
        logo_height=request.height,
        cutout_x=cutout_x,
        cutout_y=cutout_y,
        cutout_width=cutout_width,
        cutout_height=cutout_height,
        shape=request.shape,
        corner_radius=request.corner_radius,
    )


def _rect_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def _ellipse_intersects_rect(
    ellipse: tuple[float, float, float, float],
    rect: tuple[float, float, float, float],
) -> bool:
    left, top, right, bottom = ellipse
    if not _rect_overlap(ellipse, rect):
        return False
    rx = (right - left) / 2.0
    ry = (bottom - top) / 2.0
    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0
    nearest_x = min(max(cx, rect[0]), rect[2])
    nearest_y = min(max(cy, rect[1]), rect[3])
    value = ((nearest_x - cx) / rx) ** 2 + ((nearest_y - cy) / ry) ** 2
    return value < 1.0 or isclose(value, 1.0, abs_tol=1e-12)


def _rounded_rect_intersects_rect(
    rounded: tuple[float, float, float, float],
    radius: float,
    rect: tuple[float, float, float, float],
) -> bool:
    if not _rect_overlap(rounded, rect):
        return False
    left, top, right, bottom = rounded
    radius = max(0.0, min(radius, (right - left) / 2.0, (bottom - top) / 2.0))
    if radius == 0:
        return True
    horizontal_band = (left + radius, top, right - radius, bottom)
    vertical_band = (left, top + radius, right, bottom - radius)
    if _rect_overlap(horizontal_band, rect) or _rect_overlap(vertical_band, rect):
        return True
    for cx, cy in (
        (left + radius, top + radius),
        (right - radius, top + radius),
        (left + radius, bottom - radius),
        (right - radius, bottom - radius),
    ):
        nearest_x = min(max(cx, rect[0]), rect[2])
        nearest_y = min(max(cy, rect[1]), rect[3])
        if (nearest_x - cx) ** 2 + (nearest_y - cy) ** 2 <= radius**2:
            return True
    return False


def _cutout_intersects_module(layout: LogoLayout, module_rect: tuple[float, float, float, float]) -> bool:
    cutout = (
        float(layout.cutout_x),
        float(layout.cutout_y),
        float(layout.cutout_x + layout.cutout_width),
        float(layout.cutout_y + layout.cutout_height),
    )
    if layout.shape == "square":
        return _rect_overlap(cutout, module_rect)
    if layout.shape == "circle":
        return _ellipse_intersects_rect(cutout, module_rect)
    return _rounded_rect_intersects_rect(cutout, float(layout.corner_radius), module_rect)


def check_logo_overlap(
    logo_layout: LogoLayout,
    analysis: QRAnalysis,
    qr_layout: QRLayout,
    protected_mask: tuple[tuple[bool, ...], ...],
) -> LogoSafetyResult:
    """Map actual cutout geometry to body modules and return protected hits."""

    if len(protected_mask) != analysis.matrix_size or any(
        len(row) != analysis.matrix_size for row in protected_mask
    ):
        raise ValueError("Protected mask dimensions do not match the QR matrix.")

    scale_x = qr_layout.qr_width / analysis.total_modules
    scale_y = qr_layout.qr_height / analysis.total_modules
    quiet = analysis.quiet_zone_modules
    overlapping: list[tuple[int, int]] = []
    for y in range(analysis.matrix_size):
        top = (quiet + y) * scale_y
        bottom = (quiet + y + 1) * scale_y
        for x in range(analysis.matrix_size):
            if not protected_mask[y][x]:
                continue
            left = (quiet + x) * scale_x
            right = (quiet + x + 1) * scale_x
            if _cutout_intersects_module(logo_layout, (left, top, right, bottom)):
                overlapping.append((x, y))

    hits = tuple(overlapping)
    return LogoSafetyResult(
        safe=not hits,
        protected_module_count=len(hits),
        overlapping_modules=hits,
    )
