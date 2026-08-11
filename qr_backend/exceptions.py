"""Domain exceptions raised by the QR backend."""

from .models import LogoSafetyResult


class QRGenerationError(Exception):
    """Base class for expected generation failures."""


class QRCapacityError(QRGenerationError):
    """The content cannot be encoded in a standard QR Code."""


class LogoProtectedAreaError(QRGenerationError):
    """The requested logo cutout touches protected functional modules."""

    def __init__(self, result: LogoSafetyResult) -> None:
        self.result = result
        super().__init__("Logo cutout overlaps protected QR modules.")

    def as_dict(self) -> dict[str, object]:
        return {
            "error": "logo_overlaps_protected_area",
            "message": str(self),
            "protected_modules": [list(item) for item in self.result.overlapping_modules],
        }


class LogoDecodeError(QRGenerationError):
    """A logo file could not be read or decoded."""


class RenderingError(QRGenerationError):
    """Raster or vector rendering failed."""

