"""Pure layout calculations for QR-pixel and final-canvas spaces."""

from .exceptions import RenderingError
from .models import QRAnalysis, QRLayout, QRRequest


def solve_layout(request: QRRequest, analysis: QRAnalysis) -> QRLayout:
    """Resolve QR size, module scale and canvas position without drawing."""

    total_modules = analysis.total_modules
    if total_modules <= 0:
        raise RenderingError("The total module count must be positive.")

    if request.size_mode == "fixed_size":
        if request.qr_width is None or request.qr_height is None:
            raise RenderingError("fixed_size requires qr_width and qr_height.")
        qr_width = request.qr_width
        qr_height = request.qr_height
        pixels_per_module = None
        module_width = qr_width / total_modules
        module_height = qr_height / total_modules
    elif request.size_mode == "fixed_module":
        if request.pixels_per_module is None:
            raise RenderingError("fixed_module requires pixels_per_module.")
        pixels_per_module = request.pixels_per_module
        qr_width = total_modules * pixels_per_module
        qr_height = total_modules * pixels_per_module
        module_width = float(pixels_per_module)
        module_height = float(pixels_per_module)
    else:
        raise RenderingError(f"Unsupported size mode: {request.size_mode!r}.")

    if qr_width <= 0 or qr_height <= 0:
        raise RenderingError("QR dimensions must be positive.")

    canvas_width = request.canvas_width if request.canvas_width is not None else qr_width
    canvas_height = request.canvas_height if request.canvas_height is not None else qr_height
    if canvas_width <= 0 or canvas_height <= 0:
        raise RenderingError("Canvas dimensions must be positive.")

    qr_x = (
        request.qr_position_x
        if request.qr_position_x is not None
        else (canvas_width - qr_width) // 2
    )
    qr_y = (
        request.qr_position_y
        if request.qr_position_y is not None
        else (canvas_height - qr_height) // 2
    )

    return QRLayout(
        size_mode=request.size_mode,
        qr_width=qr_width,
        qr_height=qr_height,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        qr_x=qr_x,
        qr_y=qr_y,
        module_width=module_width,
        module_height=module_height,
        pixels_per_module=pixels_per_module,
    )
