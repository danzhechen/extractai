from pathlib import Path

import pytest
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_reader import PipelineConfig, PipelineRunner
from pdf_reader.debug_artifacts import draw_table_overlay, generate_html_report
from pdf_reader.models import BoundingBox, ExtractionResult, RunStats, TableGrid, TableMetadata, TableRegion


def _create_sample_pdf(path: Path, num_pages: int = 1) -> None:
    """Create a test PDF."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for page_num in range(num_pages):
        c.drawString(100, 750, "Header1 Header2 Header3")
        c.drawString(100, 730, "Row1Col1 Row1Col2 Row1Col3")
        if page_num < num_pages - 1:
            c.showPage()
    c.save()


def test_overlay_images_generated_when_enabled(tmp_path):
    """Test that overlay images are generated when debug artifacts are enabled."""
    pdf_path = tmp_path / "test.pdf"
    output_dir = tmp_path / "debug_output"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    config = PipelineConfig(
        input_path=pdf_path,
        page_indices=[0],
        enable_debug_artifacts=True,
        debug_output_dir=str(output_dir),
        generate_overlays=True,
        extraction_preset="offline",
    )

    result = runner.extract_tables(str(pdf_path), config=config)

    # Check that overlay image was created
    overlay_path = output_dir / "page_0_overlay.png"
    assert overlay_path.exists(), "Overlay image should be generated"
    assert overlay_path.stat().st_size > 0, "Overlay image should be non-empty"

    # Verify it's a valid PNG image
    img = Image.open(overlay_path)
    assert img.format == "PNG", "Overlay should be PNG format"
    assert img.size[0] > 0 and img.size[1] > 0, "Overlay should have valid dimensions"


def test_overlay_images_not_generated_when_disabled(tmp_path):
    """Test that overlay images are not generated when debug artifacts are disabled."""
    pdf_path = tmp_path / "test.pdf"
    output_dir = tmp_path / "debug_output"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    config = PipelineConfig(
        input_path=pdf_path,
        page_indices=[0],
        enable_debug_artifacts=False,  # Disabled
        debug_output_dir=str(output_dir),
        extraction_preset="offline",
    )

    result = runner.extract_tables(str(pdf_path), config=config)

    # Check that no overlay images were created
    overlay_path = output_dir / "page_0_overlay.png"
    assert not overlay_path.exists(), "Overlay image should not be generated when disabled"


def test_html_report_generated_when_enabled(tmp_path):
    """Test that HTML report is generated when debug artifacts are enabled."""
    pdf_path = tmp_path / "test.pdf"
    output_dir = tmp_path / "debug_output"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    config = PipelineConfig(
        input_path=pdf_path,
        page_indices=[0],
        enable_debug_artifacts=True,
        debug_output_dir=str(output_dir),
        generate_html_report=True,
        extraction_preset="offline",
    )

    result = runner.extract_tables(str(pdf_path), config=config)

    # Check that HTML report was created
    report_path = output_dir / "extraction_report.html"
    assert report_path.exists(), "HTML report should be generated"
    assert report_path.stat().st_size > 0, "HTML report should be non-empty"

    # Verify report content
    report_content = report_path.read_text()
    assert "PDF Table Extraction Report" in report_content
    assert "Run Statistics" in report_content
    assert "Extracted Tables" in report_content
    assert str(result.run_stats.tables_detected) in report_content


def test_html_report_not_generated_when_disabled(tmp_path):
    """Test that HTML report is not generated when debug artifacts are disabled."""
    pdf_path = tmp_path / "test.pdf"
    output_dir = tmp_path / "debug_output"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    config = PipelineConfig(
        input_path=pdf_path,
        page_indices=[0],
        enable_debug_artifacts=False,  # Disabled
        debug_output_dir=str(output_dir),
        extraction_preset="offline",
    )

    result = runner.extract_tables(str(pdf_path), config=config)

    # Check that no HTML report was created
    report_path = output_dir / "extraction_report.html"
    assert not report_path.exists(), "HTML report should not be generated when disabled"


def test_html_report_contains_expected_sections(tmp_path):
    """Test that HTML report contains expected sections and data."""
    pdf_path = tmp_path / "test.pdf"
    output_dir = tmp_path / "debug_output"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    config = PipelineConfig(
        input_path=pdf_path,
        page_indices=[0],
        enable_debug_artifacts=True,
        debug_output_dir=str(output_dir),
        generate_html_report=True,
        extraction_preset="offline",
    )

    result = runner.extract_tables(str(pdf_path), config=config)

    report_path = output_dir / "extraction_report.html"
    report_content = report_path.read_text()

    # Check for key sections
    assert "<h1>PDF Table Extraction Report</h1>" in report_content
    assert "<h2>Run Statistics</h2>" in report_content
    assert "<h2>Extracted Tables</h2>" in report_content

    # Check for metrics
    assert "Pages Processed" in report_content
    assert "Tables Detected" in report_content
    assert "Tables Extracted" in report_content

    # Check for table data
    if result.tables:
        assert "<table>" in report_content
        assert "<thead>" in report_content or "<tbody>" in report_content


def test_overlay_image_contains_visual_elements(tmp_path):
    """Test that overlay images contain expected visual elements."""
    pdf_path = tmp_path / "test.pdf"
    output_dir = tmp_path / "debug_output"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    config = PipelineConfig(
        input_path=pdf_path,
        page_indices=[0],
        enable_debug_artifacts=True,
        debug_output_dir=str(output_dir),
        generate_overlays=True,
        extraction_preset="offline",
    )

    result = runner.extract_tables(str(pdf_path), config=config)

    overlay_path = output_dir / "page_0_overlay.png"
    assert overlay_path.exists()

    # Load and verify image
    img = Image.open(overlay_path)
    # Image should have reasonable dimensions (not empty)
    assert img.size[0] > 100 and img.size[1] > 100, "Overlay should have reasonable dimensions"


def test_debug_output_directory_created(tmp_path):
    """Test that debug output directory is created when artifacts are enabled."""
    pdf_path = tmp_path / "test.pdf"
    output_dir = tmp_path / "new_debug_dir"  # Directory that doesn't exist yet

    runner = PipelineRunner()
    config = PipelineConfig(
        input_path=pdf_path,
        page_indices=[0],
        enable_debug_artifacts=True,
        debug_output_dir=str(output_dir),
        extraction_preset="offline",
    )

    # Directory should be created during __post_init__
    assert output_dir.exists(), "Debug output directory should be created"


def test_backward_compatibility_no_artifacts_by_default(tmp_path):
    """Test that artifacts are not generated by default (backward compatibility)."""
    pdf_path = tmp_path / "test.pdf"
    output_dir = tmp_path / "debug_output"
    _create_sample_pdf(pdf_path, num_pages=1)

    runner = PipelineRunner()
    # Use default config (enable_debug_artifacts=False)
    config = PipelineConfig(input_path=pdf_path, page_indices=[0], extraction_preset="offline")

    result = runner.extract_tables(str(pdf_path), config=config)

    # Should still extract tables successfully
    assert result.run_stats.tables_detected >= 1

    # But no artifacts should be generated
    overlay_path = output_dir / "page_0_overlay.png"
    report_path = output_dir / "extraction_report.html"
    assert not overlay_path.exists(), "No overlay should be generated by default"
    assert not report_path.exists(), "No report should be generated by default"


def test_draw_table_overlay_function(tmp_path):
    """Test the draw_table_overlay function directly."""
    # Create a test image
    test_image = Image.new("RGB", (800, 600), color="white")
    draw = Image.new("RGB", (800, 600), color="white")

    # Create test regions and grids
    bbox = BoundingBox(x0=0.1, y0=0.1, x1=0.9, y1=0.9)
    region = TableRegion(page_index=0, bbox=bbox, confidence=1.0)

    # Create a simple grid
    from pdf_reader.models import Cell

    cells = [
        Cell(row_index=0, col_index=0, bbox=BoundingBox(x0=0.1, y0=0.1, x1=0.5, y1=0.5)),
        Cell(row_index=0, col_index=1, bbox=BoundingBox(x0=0.5, y0=0.1, x1=0.9, y1=0.5)),
        Cell(row_index=1, col_index=0, bbox=BoundingBox(x0=0.1, y0=0.5, x1=0.5, y1=0.9)),
        Cell(row_index=1, col_index=1, bbox=BoundingBox(x0=0.5, y0=0.5, x1=0.9, y1=0.9)),
    ]
    grid = TableGrid(table_id="test_table", page_index=0, n_rows=2, n_cols=2, cells=cells)

    overlay_path = tmp_path / "test_overlay.png"
    draw_table_overlay(test_image, [region], [grid], overlay_path)

    assert overlay_path.exists()
    assert overlay_path.stat().st_size > 0

    # Verify it's a valid image
    img = Image.open(overlay_path)
    assert img.format == "PNG"


def test_generate_html_report_function(tmp_path):
    """Test the generate_html_report function directly."""
    # Create a minimal ExtractionResult
    stats = RunStats(
        pages_processed=1,
        tables_detected=1,
        tables_extracted=1,
        total_cells_extracted=4,
        average_ocr_confidence=0.9,
    )
    result = ExtractionResult(run_stats=stats)

    report_path = tmp_path / "test_report.html"
    generate_html_report(
        result,
        "test.pdf",
        {"DPI": 200},
        report_path,
        overlay_image_paths=None,
    )

    assert report_path.exists()
    assert report_path.stat().st_size > 0

    content = report_path.read_text()
    assert "PDF Table Extraction Report" in content
    assert "test.pdf" in content
    assert "Run Statistics" in content


