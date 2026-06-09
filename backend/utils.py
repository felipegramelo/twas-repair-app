"""
Shared utility functions used across backend routes.

Centralizes helpers that were previously duplicated or used cross-module
without explicit imports (causing F821 bugs at runtime).
"""
import io
from typing import List, Tuple

import fitz  # PyMuPDF


# Mapping of file extensions to MIME types (used in upload endpoints)
MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "pdf": "application/pdf",
}


def convert_pdf_to_images(pdf_data: bytes) -> List[Tuple[bytes, str]]:
    """Convert PDF pages to JPEG images.

    Returns a list of (jpeg_bytes, filename) tuples — one per page.
    """
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    images: List[Tuple[bytes, str]] = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("jpeg")
        images.append((img_data, f"page_{i + 1}.jpeg"))
    doc.close()
    return images


def format_currency(value: float) -> str:
    """Format value as Brazilian Real (e.g., 1234.56 -> 'R$ 1.234,56')."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_date_sortable(d: str) -> str:
    """Convert DD/MM/YYYY -> YYYY-MM-DD for sortable string comparison.

    Returns the original string on parse error so sorting still works.
    """
    if not d:
        return ""
    try:
        parts = d.split("/")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]:>02}-{parts[0]:>02}"
    except Exception:
        pass
    return d
