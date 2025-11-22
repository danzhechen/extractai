from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import pdfplumber
from PIL import Image

from .models import PdfDocument, PdfPage

PageImage = Image.Image


class PdfIngestionError(Exception):
    """Domain-specific error for PDF ingestion problems."""


@dataclass
class PdfIngestionService:
    """Service responsible for loading PDFs and rendering pages as images.

    Typical usage:

        service = PdfIngestionService()
        doc = service.load_pdf("report.pdf")
        image = service.render_page(page_index=0, dpi=200)
    """

    default_dpi: int = 200

    _pdf: Optional[pdfplumber.PDF] = None
    _document: Optional[PdfDocument] = None

    def load_pdf(self, input: Union[str, Path, bytes]) -> PdfDocument:
        """Load a PDF from a file path or bytes and return a PdfDocument.

        Raises:
            PdfIngestionError: if the file cannot be opened or parsed.
            TypeError: if the input type is unsupported.
        """
        try:
            if isinstance(input, (str, Path)):
                path = Path(input)
                if not path.exists():
                    raise PdfIngestionError(f"PDF file not found: {path}")
                pdf = pdfplumber.open(str(path))
            elif isinstance(input, bytes):
                pdf = pdfplumber.open(io.BytesIO(input))
            else:
                raise TypeError("input must be a path-like string, Path, or bytes")
        except PdfIngestionError:
            raise
        except Exception as exc:  # pragma: no cover - library-specific errors
            raise PdfIngestionError(f"Failed to open PDF: {exc}") from exc

        pages = []
        for idx, page in enumerate(pdf.pages):
            width = float(page.width or 0)
            height = float(page.height or 0)
            pages.append(PdfPage(index=idx, width=width, height=height))

        self._pdf = pdf
        self._document = PdfDocument(pages=pages)
        return self._document

    def render_page(self, page_index: int, dpi: Optional[int] = None) -> PageImage:
        """Render a page of the currently loaded PDF as a Pillow Image.

        Args:
            page_index: Zero-based index of the page to render.
            dpi: Desired rendering DPI. If None, uses self.default_dpi.

        Raises:
            PdfIngestionError: if no PDF is loaded or page_index is out of range.
        """
        if self._pdf is None or self._document is None:
            raise PdfIngestionError("No PDF loaded. Call load_pdf() first.")

        if page_index < 0 or page_index >= self._document.page_count:
            raise PdfIngestionError(
                f"page_index {page_index} out of range "
                f"(valid: 0..{self._document.page_count - 1})"
            )

        dpi_value = dpi or self.default_dpi
        page = self._pdf.pages[page_index]
        page_image = page.to_image(resolution=dpi_value)
        return page_image.original




