"""
cv_parser.py — Extract plain text from uploaded CV files.

Supports:
  - PDF  (.pdf)  via pdfplumber
  - Word (.docx) via python-docx
  - Plain text (.txt)

Returns the extracted text as a single string, or raises ValueError for
unsupported formats or unreadable files.
"""

import io
import logging

logger = logging.getLogger(__name__)

MAX_CHARS = 15_000  # Trim before sending to Gemini to stay within token limits


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from a CV file supplied as raw bytes.

    Args:
        file_bytes: Raw file content.
        filename:   Original filename (used to detect the format).

    Returns:
        Extracted plain text, trimmed to MAX_CHARS.

    Raises:
        ValueError: If the file type is unsupported or extraction fails.
    """
    name = filename.lower()

    if name.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    elif name.endswith(".docx"):
        return _extract_docx(file_bytes)
    elif name.endswith(".txt"):
        return _extract_txt(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type for '{filename}'. "
            "Please upload a PDF, DOCX, or TXT file."
        )


def _extract_pdf(file_bytes: bytes) -> str:
    try:
        import pdfplumber
    except ImportError as e:
        raise ValueError("pdfplumber is not installed. Run: pip install pdfplumber") from e

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

    result = "\n".join(text_parts).strip()
    if not result:
        raise ValueError("Could not extract any text from the PDF. Is it a scanned image?")
    return result[:MAX_CHARS]


def _extract_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document
    except ImportError as e:
        raise ValueError("python-docx is not installed. Run: pip install python-docx") from e

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    result = "\n".join(paragraphs).strip()
    if not result:
        raise ValueError("Could not extract any text from the DOCX file.")
    return result[:MAX_CHARS]


def _extract_txt(file_bytes: bytes) -> str:
    try:
        result = file_bytes.decode("utf-8", errors="replace").strip()
    except Exception as e:
        raise ValueError(f"Could not read text file: {e}") from e
    if not result:
        raise ValueError("The text file appears to be empty.")
    return result[:MAX_CHARS]
