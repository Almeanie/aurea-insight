"""Export module facade with lazy imports.

This prevents optional PDF dependencies (WeasyPrint native libs) from breaking
CSV/XLSX exports at import time.
"""

from typing import Any


async def generate_pdf_report(*args: Any, **kwargs: Any) -> bytes:
    from .pdf_report import generate_pdf_report as _generate_pdf_report
    return await _generate_pdf_report(*args, **kwargs)


def generate_findings_csv(*args: Any, **kwargs: Any) -> str:
    from .csv_export import generate_findings_csv as _generate_findings_csv
    return _generate_findings_csv(*args, **kwargs)


def generate_ajes_csv(*args: Any, **kwargs: Any) -> str:
    from .csv_export import generate_ajes_csv as _generate_ajes_csv
    return _generate_ajes_csv(*args, **kwargs)


def generate_ajes_xlsx(*args: Any, **kwargs: Any):
    from .excel_export import generate_ajes_xlsx as _generate_ajes_xlsx
    return _generate_ajes_xlsx(*args, **kwargs)


__all__ = [
    "generate_pdf_report",
    "generate_findings_csv",
    "generate_ajes_csv",
    "generate_ajes_xlsx",
]
