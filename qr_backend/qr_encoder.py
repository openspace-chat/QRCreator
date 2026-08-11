import segno
from segno import DataOverflowError

from .exceptions import QRCapacityError
from .models import QRCoreRequest, QRAnalysis

ERROR_LEVELS = ("L", "M", "Q", "H")

def analyze_qr(request: QRCoreRequest) -> QRAnalysis:
    """
    根据内容和指定纠错等级生成二维码编码分析结果。

    本函数：
    - 自动选择最小QR版本
    - 自动选择最优编码模式/模式组合
    - 使用指定字符编码
    - 可启用ECI
    - 严格使用用户指定纠错等级
    - 返回二维码原始模块矩阵

    本函数不进行任何图片绘制。
    """

    # --------------------------------------------------
    # 1. 内容编码信息
    # --------------------------------------------------
    encoded_data = request.text.encode(request.encoding)
    char_count = len(request.text)
    encoded_byte_count = len(encoded_data)

    # --------------------------------------------------
    # 2. 生成标准QR Code
    # --------------------------------------------------

    try:
        qr = segno.make_qr(
            request.text,
            error=request.error_level,
            # None = 自动选择能够容纳数据的最小版本；批量导出可锁定版本。
            version=request.version,
            # None = 自动选择编码模式
            mode=None,
            encoding=request.encoding,
            eci=request.use_eci,
            # 非常重要：禁止 Segno 自动提升纠错等级
            boost_error=False,
        )
    except DataOverflowError as exc:
        raise QRCapacityError("Content exceeds standard QR Code capacity.") from exc


    # --------------------------------------------------
    # 3. 获取二维码模块矩阵
    # --------------------------------------------------

    matrix = tuple(
        tuple(bool(module) for module in row)
        for row in qr.matrix
    )


    # --------------------------------------------------
    # 4. 主体模块尺寸
    # --------------------------------------------------

    matrix_size = len(matrix)
    if matrix_size == 0:
        raise RuntimeError("QR matrix is empty.")


    # --------------------------------------------------
    # 5. 加入静区后的逻辑模块尺寸
    # --------------------------------------------------

    total_modules = (
        matrix_size
        + request.quiet_zone_modules * 2
    )


    # --------------------------------------------------
    # 6. 黑白模块统计
    # --------------------------------------------------

    dark_module_count = sum(
        sum(row)
        for row in matrix
    )

    body_module_count = matrix_size * matrix_size

    light_module_count = (
        body_module_count
        - dark_module_count
    )


    # --------------------------------------------------
    # 7. 返回分析结果
    # --------------------------------------------------

    return QRAnalysis(
        text=request.text,
        encoding=request.encoding,
        use_eci=request.use_eci,
        requested_error_level=request.error_level,
        actual_error_level=qr.error,
        version=int(qr.version),
        designator=qr.designator,
        mode=qr.mode,
        mask=qr.mask,
        char_count=char_count,
        encoded_byte_count=encoded_byte_count,
        matrix_size=matrix_size,
        quiet_zone_modules=request.quiet_zone_modules,
        total_modules=total_modules,
        dark_module_count=dark_module_count,
        light_module_count=light_module_count,
        matrix=matrix,
    )


def analyze_all_error_levels(
    text: str,
    encoding: str = "utf-8",
    use_eci: bool = True,
    quiet_zone_modules: int = 4,
) -> tuple[QRAnalysis, ...]:
    """
    对同一文本分别计算L、M、Q、H四个纠错等级。
    """

    results = []

    for level in ERROR_LEVELS:

        request = QRCoreRequest(
            text=text,
            error_level=level,
            encoding=encoding,
            use_eci=use_eci,
            quiet_zone_modules=quiet_zone_modules,
        )

        result = analyze_qr(request)

        results.append(result)

    return tuple(results)
