from qr_backend.models import QRAnalysis


def make_analysis(version: int = 1, quiet_zone: int = 4) -> QRAnalysis:
    size = 17 + 4 * version
    matrix = tuple(tuple(False for _ in range(size)) for _ in range(size))
    return QRAnalysis(
        text="test",
        encoding="utf-8",
        use_eci=True,
        requested_error_level="M",
        actual_error_level="M",
        version=version,
        designator=f"{version}-M",
        mode="byte",
        mask=0,
        char_count=4,
        encoded_byte_count=4,
        matrix_size=size,
        quiet_zone_modules=quiet_zone,
        total_modules=size + 2 * quiet_zone,
        dark_module_count=0,
        light_module_count=size * size,
        matrix=matrix,
    )

