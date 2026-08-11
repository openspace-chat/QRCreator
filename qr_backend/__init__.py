"""Composable QR Code generation backend."""

from .exceptions import (
    LogoDecodeError,
    LogoProtectedAreaError,
    QRCapacityError,
    QRGenerationError,
    RenderingError,
)
from .models import (
    LogoLayout,
    LogoRequest,
    LogoSafetyResult,
    QRAnalysis,
    QRCoreRequest,
    QRLayout,
    QRRequest,
    QRResult,
)
from .qr_encoder import analyze_all_error_levels, analyze_qr
from .service import generate_qr

__all__ = [
    "LogoDecodeError",
    "LogoLayout",
    "LogoProtectedAreaError",
    "LogoRequest",
    "LogoSafetyResult",
    "QRAnalysis",
    "QRCapacityError",
    "QRCoreRequest",
    "QRGenerationError",
    "QRLayout",
    "QRRequest",
    "QRResult",
    "RenderingError",
    "analyze_all_error_levels",
    "analyze_qr",
    "generate_qr",
]
