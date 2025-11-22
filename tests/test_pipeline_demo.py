from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_reader import PipelineConfig, PipelineRunner


def _create_sample_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(100, 750, "Header1 Header2 Header3")
    c.drawString(100, 730, "Row1Col1 Row1Col2 Row1Col3")
    c.showPage()
    c.save()


def test_pipeline_runner_extract_tables(tmp_path):
    pdf_path = tmp_path / "sample_pipeline.pdf"
    _create_sample_pdf(pdf_path)

    cfg = PipelineConfig(input_path=pdf_path, page_indices=[0], dpi=150, extraction_preset="offline")
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Should process at least one page and detect at least one table
    assert result.run_stats.pages_processed >= 1
    assert result.run_stats.tables_detected >= 1
    assert len(result.tables) == result.run_stats.tables_detected

    first_table = result.tables[0]
    # Expect default_rows x default_cols grid worth of cells
    assert len(first_table.rows) == cfg.default_rows
    assert all(len(row) == cfg.default_cols for row in first_table.rows)



