"""Rasterize QR matrices; logo handling intentionally lives elsewhere."""

from PIL import Image, ImageDraw

from .exceptions import RenderingError
from .models import Matrix, QRAnalysis, QRLayout, RGBA


def _validate_square_matrix(matrix: Matrix) -> int:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise RenderingError("QR matrix must be non-empty and square.")
    return size


def render_fixed_module_qr(
    matrix: Matrix,
    pixels_per_module: int,
    quiet_zone_modules: int,
    foreground_color: RGBA,
    background_color: RGBA,
) -> Image.Image:
    """Draw every logical module as an exact integer-pixel rectangle."""

    matrix_size = _validate_square_matrix(matrix)
    if pixels_per_module <= 0 or quiet_zone_modules < 0:
        raise RenderingError("Invalid module size or quiet zone.")
    total_modules = matrix_size + 2 * quiet_zone_modules
    image = Image.new(
        "RGBA",
        (total_modules * pixels_per_module, total_modules * pixels_per_module),
        background_color,
    )
    draw = ImageDraw.Draw(image)
    offset = quiet_zone_modules * pixels_per_module
    for y, row in enumerate(matrix):
        top = offset + y * pixels_per_module
        for x, dark in enumerate(row):
            if dark:
                left = offset + x * pixels_per_module
                draw.rectangle(
                    (
                        left,
                        top,
                        left + pixels_per_module - 1,
                        top + pixels_per_module - 1,
                    ),
                    fill=foreground_color,
                )
    return image


def render_fixed_size_qr(
    matrix: Matrix,
    width: int,
    height: int,
    quiet_zone_modules: int,
    foreground_color: RGBA,
    background_color: RGBA,
) -> Image.Image:
    """Rasterize to the exact requested dimensions, allowing uneven cells."""

    matrix_size = _validate_square_matrix(matrix)
    if width <= 0 or height <= 0 or quiet_zone_modules < 0:
        raise RenderingError("Invalid QR size or quiet zone.")

    total_modules = matrix_size + 2 * quiet_zone_modules
    logical = Image.new("RGBA", (total_modules, total_modules), background_color)
    pixels = logical.load()
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                pixels[x + quiet_zone_modules, y + quiet_zone_modules] = foreground_color

    # Nearest-neighbour maps the logical grid to the exact user-requested size.
    # Unlike fixed_module, uneven integer cell widths are allowed in this mode.
    return logical.resize((width, height), resample=Image.Resampling.NEAREST)


def render_qr(
    analysis: QRAnalysis,
    layout: QRLayout,
    foreground_color: RGBA,
    background_color: RGBA,
) -> Image.Image:
    """Dispatch to the renderer dedicated to the selected size mode."""

    if layout.size_mode == "fixed_module":
        if layout.pixels_per_module is None:
            raise RenderingError("fixed_module layout has no module pixel size.")
        return render_fixed_module_qr(
            analysis.matrix,
            layout.pixels_per_module,
            analysis.quiet_zone_modules,
            foreground_color,
            background_color,
        )
    if layout.size_mode == "fixed_size":
        return render_fixed_size_qr(
            analysis.matrix,
            layout.qr_width,
            layout.qr_height,
            analysis.quiet_zone_modules,
            foreground_color,
            background_color,
        )
    raise RenderingError(f"Unsupported size mode: {layout.size_mode!r}.")

