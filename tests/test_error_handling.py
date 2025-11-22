from pathlib import Path
from unittest.mock import MagicMock, patch

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_reader import PipelineConfig, PipelineRunner
from pdf_reader.ingestion import PdfIngestionError
from pdf_reader.models import TableMetadata


def _create_sample_pdf(path: Path, num_pages: int = 2) -> None:
    """Create a multi-page PDF with tables."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for page_num in range(num_pages):
        c.drawString(100, 750, f"Page {page_num + 1} Header")
        c.drawString(100, 730, "Col1 Col2 Col3")
        c.drawString(100, 710, "Row1Col1 Row1Col2 Row1Col3")
        if page_num < num_pages - 1:
            c.showPage()
    c.save()


def test_pipeline_handles_page_rendering_failure_gracefully(tmp_path):
    """Test that pipeline skips pages that fail to render and continues processing."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=3)

    runner = PipelineRunner()
    config = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150),
    extraction_preset="offline",

    # Mock render_page to fail on page 1
    original_render = runner.ingestion.render_page

    def mock_render_page(page_index: int, dpi: int = None):
        if page_index == 1:
            raise PdfIngestionError(f"Page {page_index} rendering failed")
        return original_render(page_index, dpi)

    runner.ingestion.render_page = mock_render_page

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should process 3 pages (attempted)
    assert result.run_stats.pages_processed == 3
    # Should skip 1 page
    assert result.run_stats.pages_skipped == 1
    # Should still detect tables from other pages
    assert result.run_stats.tables_detected >= 2  # At least from pages 0 and 2
    # Should have error message for page 1
    assert any("Page 1" in err and "rendering" in err for err in result.run_stats.errors)
    # Should have successfully extracted tables
    assert len(result.tables) >= 2


def test_pipeline_handles_detection_failure_gracefully(tmp_path):
    """Test that pipeline handles table detection failures and continues."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=2)

    runner = PipelineRunner()
    config = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150),
    extraction_preset="offline",

    # Mock detect to fail on page 1
    original_detect = runner.region_detector.detect

    def mock_detect(page_image, page_index: int):
        if page_index == 1:
            raise ValueError("Detection failed")
        return original_detect(page_image, page_index)

    runner.region_detector.detect = mock_detect

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should process 2 pages
    assert result.run_stats.pages_processed == 2
    # Should skip 1 page due to detection failure
    assert result.run_stats.pages_skipped == 1
    # Should have error message
    assert any("Page 1" in err and "detection" in err.lower() for err in result.run_stats.errors)
    # Should still have tables from page 0
    assert result.run_stats.tables_detected >= 1


def test_pipeline_handles_extraction_failure_gracefully(tmp_path):
    """Test that pipeline handles table extraction failures and continues."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=2)

    runner = PipelineRunner()
    config = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150),
    extraction_preset="offline",

    # Mock build_grid to fail for the first table
    original_build_grid = runner.grid_detector.build_grid
    call_count = [0]

    def mock_build_grid(region, n_rows: int, n_cols: int, table_id: str = "t1"):
        call_count[0] += 1
        if call_count[0] == 1:  # Fail first table
            raise ValueError("Grid construction failed")
        return original_build_grid(region, n_rows, n_cols, table_id)

    runner.grid_detector.build_grid = mock_build_grid

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should have some tables detected
    assert result.run_stats.tables_detected >= 1
    # Should have at least one failed table
    assert result.run_stats.tables_failed >= 1
    # Should have error message
    assert any("extraction failed" in err.lower() for err in result.run_stats.errors)
    # Should have successfully extracted tables
    assert len(result.tables) >= 1
    # Should have metadata for failed tables
    failed_metadata = [m for m in result.metadata if m.status == "extraction_failed"]
    assert len(failed_metadata) >= 1
    assert failed_metadata[0].error_message is not None


def test_pipeline_handles_pages_with_no_tables(tmp_path):
    """Test that pipeline handles pages with no tables found (not an error)."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=2)

    runner = PipelineRunner()
    config = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150),
    extraction_preset="offline",

    # Mock detect to return empty list for page 1
    original_detect = runner.region_detector.detect

    def mock_detect(page_image, page_index: int):
        if page_index == 1:
            return []  # No tables found
        return original_detect(page_image, page_index)

    runner.region_detector.detect = mock_detect

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should process 2 pages
    assert result.run_stats.pages_processed == 2
    # Should not skip any pages (no tables is not an error)
    assert result.run_stats.pages_skipped == 0
    # Should have tables from page 0
    assert result.run_stats.tables_detected >= 1
    # Should not have errors for empty detection
    assert not any("no tables" in err.lower() for err in result.run_stats.errors)


def test_pipeline_backward_compatible_with_successful_run(tmp_path):
    """Test that successful runs have zero error counts (backward compatibility)."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    config = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150),
    extraction_preset="offline",

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should process successfully
    assert result.run_stats.pages_processed >= 1
    assert result.run_stats.tables_detected >= 1
    # Should have zero error counts
    assert result.run_stats.pages_skipped == 0
    assert result.run_stats.tables_failed == 0
    # Should have no errors
    assert len(result.run_stats.errors) == 0
    # All metadata should have success status
    for metadata in result.metadata:
        assert metadata.status == "success"
        assert metadata.error_message is None


def test_pipeline_mixed_success_and_failure_scenario(tmp_path):
    """Test pipeline with mixed success and failure scenarios."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=4)

    runner = PipelineRunner()
    config = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150),
    extraction_preset="offline",

    # Mock to fail page 1 rendering and page 3 detection
    original_render = runner.ingestion.render_page
    original_detect = runner.region_detector.detect

    def mock_render_page(page_index: int, dpi: int = None):
        if page_index == 1:
            raise PdfIngestionError("Rendering failed")
        return original_render(page_index, dpi)

    def mock_detect(page_image, page_index: int):
        if page_index == 3:
            raise ValueError("Detection failed")
        return original_detect(page_image, page_index)

    runner.ingestion.render_page = mock_render_page
    runner.region_detector.detect = mock_detect

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should process 4 pages
    assert result.run_stats.pages_processed == 4
    # Should skip 2 pages (page 1 and 3)
    assert result.run_stats.pages_skipped == 2
    # Should have tables from pages 0 and 2
    assert result.run_stats.tables_detected >= 2
    # Should have error messages
    assert len(result.run_stats.errors) >= 2
    # Should have successfully extracted tables
    assert len(result.tables) >= 2
    # All extracted tables should have success status
    for table_meta in result.metadata:
        if table_meta.status == "success":
            # Verify it's in the tables list
            # table_metadata_id format is "{table_id}-meta"
            assert any(t.table_metadata_id == f"{table_meta.table_id}-meta" for t in result.tables)


def test_table_metadata_includes_error_status_for_failed_tables(tmp_path):
    """Test that failed tables have appropriate error status in metadata."""
    pdf_path = tmp_path / "test.pdf"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    config = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150),
    extraction_preset="offline",

    # Mock assembler to fail
    original_to_spec = runner.assembler.to_dataframe_spec

    def mock_to_spec(grid):
        if grid.table_id == "p0_t0":
            raise ValueError("Assembly failed")
        return original_to_spec(grid)

    runner.assembler.to_dataframe_spec = mock_to_spec

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should have failed table
    assert result.run_stats.tables_failed >= 1
    # Should have failed metadata entry
    failed_metadata = [m for m in result.metadata if m.status == "extraction_failed"]
    assert len(failed_metadata) >= 1
    assert failed_metadata[0].error_message is not None
    assert "Assembly failed" in failed_metadata[0].error_message

