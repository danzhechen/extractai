from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_reader import PdfDocument
from pdf_reader.ingestion import PdfIngestionError, PdfIngestionService


def _create_sample_pdf(path: Path) -> None:
    """Create a minimal single-page PDF for testing."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(100, 750, "Hello, PDF!")
    c.showPage()
    c.save()


def test_load_pdf_and_render_page(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _create_sample_pdf(pdf_path)

    service = PdfIngestionService()
    doc = service.load_pdf(pdf_path)

    assert isinstance(doc, PdfDocument)
    assert doc.page_count == 1
    assert doc.pages[0].width > 0
    assert doc.pages[0].height > 0

    image = service.render_page(0, dpi=150)
    assert image is not None
    assert image.width > 0
    assert image.height > 0


def test_missing_file_raises_error(tmp_path):
    missing_path = tmp_path / "does-not-exist.pdf"
    service = PdfIngestionService()

    with pytest.raises(PdfIngestionError):
        service.load_pdf(missing_path)


def test_out_of_range_page_index_raises_error(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _create_sample_pdf(pdf_path)

    service = PdfIngestionService()
    service.load_pdf(pdf_path)

    with pytest.raises(PdfIngestionError):
        service.render_page(5)




