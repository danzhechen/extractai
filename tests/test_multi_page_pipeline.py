from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_reader import PipelineConfig, PipelineRunner


def _create_multi_page_pdf(path: Path, num_pages: int = 3) -> None:
    """Create a multi-page PDF with tables on each page."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for page_num in range(num_pages):
        # Add some content to each page
        c.drawString(100, 750, f"Page {page_num + 1} Header")
        c.drawString(100, 730, "Col1 Col2 Col3")
        c.drawString(100, 710, f"Row1Col1 Row1Col2 Row1Col3")
        c.drawString(100, 690, f"Row2Col1 Row2Col2 Row2Col3")
        if page_num < num_pages - 1:
            c.showPage()
    c.save()


def test_pipeline_processes_all_pages_by_default(tmp_path):
    """Test that pipeline processes all pages when page_indices is None."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=3)

    cfg = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150, extraction_preset="offline")
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Should process all 3 pages
    assert result.run_stats.pages_processed == 3
    # Should detect at least one table per page (3 tables total)
    assert result.run_stats.tables_detected >= 3
    assert len(result.tables) == result.run_stats.tables_detected
    assert len(result.metadata) == result.run_stats.tables_detected

    # Verify each table has correct page_index
    page_indices_found = {meta.page_index for meta in result.metadata}
    assert page_indices_found == {0, 1, 2}


def test_pipeline_processes_specific_page_range(tmp_path):
    """Test that pipeline processes only specified page indices."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=4)

    # Process only pages 0 and 2
    cfg = PipelineConfig(input_path=pdf_path, page_indices=[0, 2], dpi=150, extraction_preset="offline")
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Should process only 2 pages
    assert result.run_stats.pages_processed == 2
    # Should detect tables from those pages
    assert result.run_stats.tables_detected >= 2

    # Verify only pages 0 and 2 are processed
    page_indices_found = {meta.page_index for meta in result.metadata}
    assert page_indices_found == {0, 2}


def test_pipeline_handles_out_of_range_page_indices(tmp_path):
    """Test that pipeline handles out-of-range page indices gracefully."""
    pdf_path = tmp_path / "single_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=2)

    # Request pages 0, 1, and 5 (5 is out of range)
    cfg = PipelineConfig(input_path=pdf_path, page_indices=[0, 1, 5], dpi=150, extraction_preset="offline")
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Should process only valid pages (0 and 1)
    assert result.run_stats.pages_processed == 2
    # Should have an error for the out-of-range page
    assert any("Page index 5 out of range" in err for err in result.run_stats.errors)

    # Verify only pages 0 and 1 are processed
    page_indices_found = {meta.page_index for meta in result.metadata}
    assert page_indices_found == {0, 1}


def test_pipeline_table_ids_are_unique_and_include_page_index(tmp_path):
    """Test that table IDs are unique and include page index."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=2)

    cfg = PipelineConfig(input_path=pdf_path, page_indices=None, dpi=150, extraction_preset="offline")
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Collect all table IDs
    table_ids = {meta.table_id for meta in result.metadata}
    # Should have unique IDs
    assert len(table_ids) == len(result.metadata)

    # Verify table IDs follow pattern p{page_index}_t{table_index}
    for meta in result.metadata:
        assert meta.table_id.startswith(f"p{meta.page_index}_t")
        # Verify page_index matches between metadata and table_id
        assert str(meta.page_index) in meta.table_id


def test_pipeline_backward_compatible_with_single_page(tmp_path):
    """Test that single-page processing still works (backward compatibility)."""
    pdf_path = tmp_path / "single_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=1)

    # Process only first page (explicit)
    cfg = PipelineConfig(input_path=pdf_path, page_indices=[0], dpi=150, extraction_preset="offline")
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Should process 1 page
    assert result.run_stats.pages_processed == 1
    assert result.run_stats.tables_detected >= 1

    # All tables should be from page 0
    for meta in result.metadata:
        assert meta.page_index == 0


def test_pipeline_processes_empty_page_range_gracefully(tmp_path):
    """Test that pipeline handles empty page_indices list gracefully."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=3)

    # Empty page list
    cfg = PipelineConfig(input_path=pdf_path, page_indices=[], dpi=150, extraction_preset="offline")
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Should process 0 pages
    assert result.run_stats.pages_processed == 0
    assert result.run_stats.tables_detected == 0
    assert len(result.tables) == 0


