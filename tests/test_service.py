from io import BytesIO

import cairosvg
import pytest
from PIL import Image

from qr_backend import (
    LogoProtectedAreaError,
    LogoRequest,
    QRCoreRequest,
    QRRequest,
    RenderingError,
    generate_qr,
)


def test_png_service_returns_exact_canvas_and_metadata() -> None:
    request = QRRequest(
        core=QRCoreRequest("123ABC/中国", "H"),
        size_mode="fixed_size",
        qr_width=300,
        qr_height=300,
        canvas_width=350,
        canvas_height=350,
        dpi=300,
    )
    result = generate_qr(request)
    with Image.open(BytesIO(result.image_bytes)) as image:
        assert image.size == (350, 350)
        assert image.mode == "RGBA"
        assert image.info["dpi"][0] == pytest.approx(300, abs=0.1)
    assert result.qr_width == result.qr_height == 300
    assert result.error_level == "H"
    assert result.dpi == 300


@pytest.mark.parametrize("requested_format", ["jpg", "jpeg"])
def test_jpeg_service_returns_opaque_rgb_with_canonical_format(requested_format: str) -> None:
    request = QRRequest(
        core=QRCoreRequest("JPEG output", "H"),
        size_mode="fixed_size",
        qr_width=300,
        qr_height=300,
        canvas_width=350,
        canvas_height=350,
        foreground_color=(0, 0, 0, 255),
        background_color=(255, 255, 255, 255),
        canvas_color=(255, 255, 255, 255),
        output_format=requested_format,
        dpi=300,
    )
    result = generate_qr(request)
    with Image.open(BytesIO(result.image_bytes)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert image.size == (350, 350)
        assert image.info["dpi"][0] == pytest.approx(300, abs=0.1)
    assert result.output_format == "jpg"


@pytest.mark.parametrize(
    ("overrides", "field_name"),
    [
        ({"foreground_color": (0, 0, 0, 254)}, "foreground_color"),
        ({"background_color": (255, 255, 255, 0)}, "background_color"),
        ({"canvas_color": (255, 255, 255, 128)}, "canvas_color"),
        (
            {"logo": LogoRequest(enabled=True, transparent_background=True)},
            "logo.transparent_background",
        ),
        (
            {
                "logo": LogoRequest(
                    enabled=True,
                    transparent_background=False,
                    background_color=(255, 255, 255, 128),
                )
            },
            "logo.background_color",
        ),
    ],
)
def test_jpeg_rejects_transparency(overrides: dict[str, object], field_name: str) -> None:
    values: dict[str, object] = {
        "core": QRCoreRequest("JPEG transparency", "H"),
        "size_mode": "fixed_module",
        "pixels_per_module": 8,
        "foreground_color": (0, 0, 0, 255),
        "background_color": (255, 255, 255, 255),
        "canvas_color": (255, 255, 255, 255),
        "output_format": "jpg",
    }
    values.update(overrides)
    request = QRRequest(**values)
    with pytest.raises(RenderingError, match="JPEG does not support transparency") as caught:
        generate_qr(request)
    assert field_name in str(caught.value)


def test_jpg_logo_can_be_used_for_jpeg_output(tmp_path) -> None:
    logo_path = tmp_path / "logo.jpg"
    Image.new("RGB", (20, 20), (255, 80, 20)).save(logo_path, format="JPEG")
    request = QRRequest(
        core=QRCoreRequest("JPEG logo", "H"),
        size_mode="fixed_module",
        pixels_per_module=10,
        foreground_color=(0, 0, 0, 255),
        background_color=(255, 255, 255, 255),
        canvas_color=(255, 255, 255, 255),
        logo=LogoRequest(
            enabled=True,
            file_path=str(logo_path),
            width=12,
            height=12,
            transparent_background=False,
            background_color=(255, 255, 255, 255),
        ),
        output_format="jpg",
    )
    result = generate_qr(request)
    with Image.open(BytesIO(result.image_bytes)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"


def test_svg_service_has_vector_qr_body() -> None:
    request = QRRequest(
        core=QRCoreRequest("vector", "M"),
        size_mode="fixed_module",
        pixels_per_module=8,
        output_format="svg",
        canvas_color=(255, 255, 255, 0),
    )
    result = generate_qr(request)
    svg = result.image_bytes.decode("utf-8")
    assert svg.startswith("<?xml")
    assert "<rect" in svg
    assert "data:image/png" not in svg
    assert result.qr_width == result.total_modules * 8


def test_png_logo_and_transparent_canvas(tmp_path) -> None:
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (10, 10), (255, 0, 0, 128)).save(logo_path)
    request = QRRequest(
        core=QRCoreRequest("logo", "H"),
        size_mode="fixed_module",
        pixels_per_module=10,
        canvas_color=(0, 0, 0, 0),
        logo=LogoRequest(enabled=True, file_path=str(logo_path), width=10, height=10),
    )
    result = generate_qr(request)
    assert result.logo_used
    with Image.open(BytesIO(result.image_bytes)) as image:
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0


def test_logo_over_finder_is_rejected(tmp_path) -> None:
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(logo_path)
    request = QRRequest(
        core=QRCoreRequest("unsafe", "M"),
        size_mode="fixed_module",
        pixels_per_module=10,
        logo=LogoRequest(
            enabled=True,
            file_path=str(logo_path),
            width=20,
            height=20,
            x=40,
            y=40,
        ),
    )
    with pytest.raises(LogoProtectedAreaError) as caught:
        generate_qr(request)
    assert caught.value.as_dict()["error"] == "logo_overlaps_protected_area"


def test_svg_logo_is_rasterized_for_png_output(tmp_path) -> None:
    logo_path = tmp_path / "logo.svg"
    logo_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        '<circle cx="5" cy="5" r="5" fill="#00aa44" fill-opacity="0.5"/>'
        "</svg>",
        encoding="utf-8",
    )
    request = QRRequest(
        core=QRCoreRequest("svg logo", "H"),
        size_mode="fixed_module",
        pixels_per_module=10,
        logo=LogoRequest(
            enabled=True,
            file_path=str(logo_path),
            width=10,
            height=10,
            shape="circle",
        ),
    )
    result = generate_qr(request)
    with Image.open(BytesIO(result.image_bytes)) as image:
        assert image.format == "PNG"
        assert image.mode == "RGBA"


def test_png_logo_is_embedded_in_valid_vector_svg(tmp_path) -> None:
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (10, 10), (0, 80, 255, 128)).save(logo_path)
    request = QRRequest(
        core=QRCoreRequest("svg output", "H"),
        size_mode="fixed_size",
        qr_width=301,
        qr_height=299,
        canvas_width=321,
        canvas_height=319,
        output_format="svg",
        logo=LogoRequest(
            enabled=True,
            file_path=str(logo_path),
            width=10,
            height=10,
            shape="rounded_square",
            corner_radius=2,
        ),
    )
    result = generate_qr(request)
    svg = result.image_bytes.decode("utf-8")
    assert 'width="321" height="319"' in svg
    assert "data:image/png;base64," in svg
    rendered = cairosvg.svg2png(bytestring=result.image_bytes)
    with Image.open(BytesIO(rendered)) as image:
        assert image.size == (321, 319)
