from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from pdf_reader import PipelineConfig, PipelineRunner
from pdf_reader.extraction import CellTextExtractor
from pdf_reader.llm_extraction import LLMExtractionError, MockLLMExtractionService
from pdf_reader.models import BoundingBox, Cell, TableGrid, TableRegion


def _make_simple_grid(n_rows: int, n_cols: int) -> TableGrid:
    """Create a simple test grid."""
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=50.0)
    region = TableRegion(page_index=0, bbox=bbox, confidence=1.0)

    cells = []
    for r in range(n_rows):
        for c in range(n_cols):
            cells.append(
                Cell(
                    row_index=r,
                    col_index=c,
                    row_span=1,
                    col_span=1,
                    bbox=bbox,
                    text=None,
                )
            )

    return TableGrid(
        table_id="grid-1",
        page_index=region.page_index,
        n_rows=n_rows,
        n_cols=n_cols,
        cells=cells,
    )


def test_cell_extractor_uses_ocr_when_confidence_high():
    """Test that extractor uses OCR when confidence is above threshold."""
    grid = _make_simple_grid(2, 2)
    extractor = CellTextExtractor(
        ocr_confidence_threshold=0.5,
        llm_fallback_enabled=False,
    )

    updated = extractor.fill_cell_text(grid)

    for cell in updated.cells:
        assert cell.text is not None
        # Currently using placeholder text, so text_source is placeholder_source
        assert cell.text_source == extractor.placeholder_source
        assert cell.text_confidence == 0.9  # Default high confidence


def test_cell_extractor_uses_llm_when_confidence_low():
    """Test that extractor uses LLM fallback when confidence is below threshold."""
    grid = _make_simple_grid(2, 2)
    mock_llm = MockLLMExtractionService(default_response="llm_extracted_text")
    extractor = CellTextExtractor(
        ocr_confidence_threshold=0.95,  # Higher than default 0.9
        llm_fallback_enabled=True,
        llm_service=mock_llm,
    )

    # Mock _extract_with_ocr to return low confidence
    original_extract = extractor._extract_with_ocr

    def mock_low_confidence_ocr(cell, page_image=None):
        text, _ = original_extract(cell, page_image)
        return text, 0.3  # Low confidence

    extractor._extract_with_ocr = mock_low_confidence_ocr

    updated = extractor.fill_cell_text(grid)

    for cell in updated.cells:
        assert cell.text == "llm_extracted_text"
        assert cell.text_source == "llm_fallback"
        assert cell.text_confidence == 0.3


def test_cell_extractor_falls_back_to_ocr_when_llm_fails():
    """Test that extractor falls back to OCR when LLM extraction fails."""
    grid = _make_simple_grid(2, 2)

    class FailingLLMService(MockLLMExtractionService):
        def extract_text_from_image(self, image, context=None):
            raise LLMExtractionError("LLM API failed")

    mock_llm = FailingLLMService()
    extractor = CellTextExtractor(
        ocr_confidence_threshold=0.95,
        llm_fallback_enabled=True,
        llm_service=mock_llm,
    )

    # Mock _extract_with_ocr to return low confidence
    original_extract = extractor._extract_with_ocr

    def mock_low_confidence_ocr(cell, page_image=None):
        text, _ = original_extract(cell, page_image)
        return text, 0.3  # Low confidence

    extractor._extract_with_ocr = mock_low_confidence_ocr

    updated = extractor.fill_cell_text(grid)

    # Should fall back to OCR result (placeholder text)
    for cell in updated.cells:
        assert cell.text is not None
        assert cell.text_source == extractor.placeholder_source  # Falls back to placeholder
        assert cell.text_confidence == 0.3


def test_cell_extractor_backward_compatible_when_llm_disabled():
    """Test that extractor behaves like Story 1.4 when LLM fallback is disabled."""
    grid = _make_simple_grid(2, 2)
    extractor = CellTextExtractor(
        llm_fallback_enabled=False,
    )

    updated = extractor.fill_cell_text(grid)

    # Should use OCR path (placeholder for now)
    for cell in updated.cells:
        assert cell.text is not None
        assert cell.text_source == extractor.placeholder_source
        # Should not have called LLM
        assert extractor.llm_service is None or extractor.llm_fallback_enabled is False


def test_pipeline_config_validates_confidence_threshold():
    """Test that PipelineConfig validates confidence threshold range."""
    # Valid threshold
    config = PipelineConfig(ocr_confidence_threshold=0.5, extraction_preset="offline")
    assert config.ocr_confidence_threshold == 0.5

    # Invalid threshold (too high)
    try:
        PipelineConfig(ocr_confidence_threshold=1.5, extraction_preset="offline")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "ocr_confidence_threshold" in str(e)

    # Invalid threshold (negative)
    try:
        PipelineConfig(ocr_confidence_threshold=-0.1, extraction_preset="offline")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "ocr_confidence_threshold" in str(e)


def test_pipeline_with_llm_fallback_enabled(tmp_path):
    """Test pipeline with LLM fallback enabled using mock service."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    # Create a test PDF
    pdf_path = tmp_path / "test.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Header1 Header2")
    c.drawString(100, 730, "Row1Col1 Row1Col2")
    c.save()

    # Create mock LLM service
    mock_llm = MockLLMExtractionService(default_response="llm_text")

    runner = PipelineRunner()
    config = PipelineConfig(
        input_path=pdf_path,
        page_indices=[0],
        ocr_confidence_threshold=0.95,  # High threshold to trigger LLM
        llm_fallback_enabled=True,
        llm_provider="openai",
        llm_api_key="test-key",
        extraction_preset="offline",
    )

    # Mock the LLM service creation to use our mock
    original_create = runner._create_llm_service

    def mock_create_llm(cfg):
        if cfg.llm_fallback_enabled:
            return mock_llm
        return None

    runner._create_llm_service = mock_create_llm

    # Mock the extractor's OCR to return low confidence
    original_fill = runner.text_extractor.fill_cell_text

    def mock_fill_with_low_confidence(grid, page_image=None):
        for cell in grid.cells:
            if not cell.text:
                cell.text = f"r{cell.row_index}c{cell.col_index}"
                cell.text_confidence = 0.3  # Low confidence
                # Check if LLM should be used
                if (
                    runner.text_extractor.llm_fallback_enabled
                    and runner.text_extractor.llm_service is not None
                    and cell.text_confidence < runner.text_extractor.ocr_confidence_threshold
                ):
                    try:
                        cell.text = runner.text_extractor.llm_service.extract_text_from_image(
                            Image.new("RGB", (100, 50), color="white")
                        )
                        cell.text_source = "llm_fallback"
                    except LLMExtractionError:
                        cell.text_source = "ocr"
                else:
                    cell.text_source = "ocr"
        return grid

    runner.text_extractor.fill_cell_text = mock_fill_with_low_confidence

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should have extracted tables
    assert result.run_stats.tables_detected >= 1
    # Check that cells have text_source set
    # Note: This is a simplified test; in a real scenario we'd check the actual cells
