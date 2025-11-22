from pdf_reader.models import (
    BoundingBox,
    Cell,
    ExtractionResult,
    PdfDocument,
    PdfPage,
    RunStats,
    TableDataFrameSpec,
    TableGrid,
    TableMetadata,
    TableRegion,
)


def test_pdf_document_page_count():
    pages = [PdfPage(index=0, width=800, height=600), PdfPage(index=1, width=800, height=600)]
    doc = PdfDocument(pages=pages)
    assert doc.page_count == 2


def test_table_grid_and_cells_invariants():
    bbox = BoundingBox(x0=0, y0=0, x1=100, y1=50)
    cells = [
        Cell(row_index=0, col_index=0, row_span=1, col_span=1, bbox=bbox, text="A1"),
        Cell(row_index=0, col_index=1, row_span=1, col_span=1, bbox=bbox, text="A2"),
        Cell(row_index=1, col_index=0, row_span=1, col_span=1, bbox=bbox, text="B1"),
        Cell(row_index=1, col_index=1, row_span=1, col_span=1, bbox=bbox, text="B2"),
    ]

    grid = TableGrid(
        table_id="t1",
        page_index=0,
        n_rows=2,
        n_cols=2,
        cells=cells,
    )

    assert grid.n_rows * grid.n_cols >= len(grid.cells)
    assert all(c.row_span >= 1 and c.col_span >= 1 for c in grid.cells)


def test_extraction_result_add_table_and_counts():
    bbox = BoundingBox(x0=0, y0=0, x1=100, y1=50)
    region = TableRegion(page_index=0, bbox=bbox)

    table_spec = TableDataFrameSpec(
        rows=[["A1", "A2"], ["B1", "B2"]],
        columns=[],
        table_metadata_id="meta-1",
    )
    metadata = TableMetadata(
        table_id="t1",
        page_index=0,
        region=region,
        grid_shape=(2, 2),
    )

    result = ExtractionResult()
    assert result.table_count == 0

    result.add_table(table_spec, metadata)
    assert result.table_count == 1
    assert len(result.metadata) == 1


def test_run_stats_defaults_and_mutation():
    stats = RunStats()
    assert stats.pages_processed == 0
    assert stats.tables_detected == 0
    assert stats.ocr_calls == 0
    assert stats.llm_fallback_calls == 0
    assert stats.errors == []

    stats.pages_processed = 3
    stats.tables_detected = 5
    stats.errors.append("sample error")

    assert stats.pages_processed == 3
    assert stats.tables_detected == 5
    assert "sample error" in stats.errors


