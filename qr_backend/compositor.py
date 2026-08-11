"""RGBA logo cutout, logo composition, and final-canvas composition."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, UnidentifiedImageError

from .exceptions import LogoDecodeError, RenderingError
from .models import LogoLayout, LogoRequest, RGBA


def _shape_mask(size: tuple[int, int], logo_layout: LogoLayout) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    left = logo_layout.cutout_x
    top = logo_layout.cutout_y
    right = left + logo_layout.cutout_width - 1
    bottom = top + logo_layout.cutout_height - 1
    box = (left, top, right, bottom)
    if logo_layout.shape == "circle":
        draw.ellipse(box, fill=255)
    elif logo_layout.shape == "square":
        draw.rectangle(box, fill=255)
    elif logo_layout.shape == "rounded_square":
        radius = max(
            0,
            min(
                logo_layout.corner_radius,
                logo_layout.cutout_width // 2,
                logo_layout.cutout_height // 2,
            ),
        )
        draw.rounded_rectangle(box, radius=radius, fill=255)
    else:
        raise RenderingError(f"Unsupported logo shape: {logo_layout.shape!r}.")
    return mask


def apply_logo_cutout(
    qr_image: Image.Image,
    logo_layout: LogoLayout,
    fill_color: RGBA = (0, 0, 0, 0),
) -> Image.Image:
    """Replace the selected QR region before placing the logo."""

    result = qr_image.convert("RGBA").copy()
    mask = _shape_mask(result.size, logo_layout)
    result.paste(fill_color, (0, 0, result.width, result.height), mask)
    return result


def load_logo_image(request: LogoRequest, logo_layout: LogoLayout) -> Image.Image:
    """Decode PNG, JPEG, or SVG and return exact-size RGBA pixels."""

    if not request.file_path:
        raise LogoDecodeError("An enabled logo requires file_path.")
    path = Path(request.file_path)
    if not path.is_file():
        raise LogoDecodeError(f"Logo file does not exist: {path}")

    try:
        if path.suffix.lower() == ".svg":
            try:
                import cairosvg
            except ImportError as exc:
                raise LogoDecodeError("CairoSVG is required for SVG logos in PNG output.") from exc
            png = cairosvg.svg2png(
                url=str(path),
                output_width=logo_layout.logo_width,
                output_height=logo_layout.logo_height,
            )
            with Image.open(BytesIO(png)) as image:
                return image.convert("RGBA").copy()

        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            return rgba.resize(
                (logo_layout.logo_width, logo_layout.logo_height),
                resample=Image.Resampling.LANCZOS,
            )
    except LogoDecodeError:
        raise
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise LogoDecodeError(f"Unable to decode logo: {path}") from exc


def _alpha_composite_clipped(
    base: Image.Image,
    overlay: Image.Image,
    x: int,
    y: int,
) -> Image.Image:
    result = base.convert("RGBA").copy()
    source = overlay.convert("RGBA")
    left = max(0, x)
    top = max(0, y)
    right = min(result.width, x + source.width)
    bottom = min(result.height, y + source.height)
    if right <= left or bottom <= top:
        return result
    crop = source.crop((left - x, top - y, right - x, bottom - y))
    result.alpha_composite(crop, dest=(left, top))
    return result


def composite_logo(
    qr_image: Image.Image,
    logo_image: Image.Image,
    logo_layout: LogoLayout,
) -> Image.Image:
    """Alpha-composite an already decoded logo onto the cut-out QR image."""

    if logo_image.size != (logo_layout.logo_width, logo_layout.logo_height):
        logo_image = logo_image.resize(
            (logo_layout.logo_width, logo_layout.logo_height),
            resample=Image.Resampling.LANCZOS,
        )
    return _alpha_composite_clipped(qr_image, logo_image, logo_layout.logo_x, logo_layout.logo_y)


def create_canvas(width: int, height: int, background_color: RGBA) -> Image.Image:
    """Create the independent final RGBA canvas."""

    if width <= 0 or height <= 0:
        raise RenderingError("Canvas dimensions must be positive.")
    return Image.new("RGBA", (width, height), background_color)


def paste_qr_to_canvas(
    canvas: Image.Image,
    qr_image: Image.Image,
    x: int,
    y: int,
) -> Image.Image:
    """Place the completed QR image in global canvas coordinates."""

    return _alpha_composite_clipped(canvas, qr_image, x, y)
