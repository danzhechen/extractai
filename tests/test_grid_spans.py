from pdf_reader.detection import GridStructureDetector
from pdf_reader.models import BoundingBox, TableRegion


def _make_region() -> TableRegion:
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=100.0)
    return TableRegion(page_index=0, bbox=bbox, confidence=1.0)


def test_span_hints_produce_horizontally_merged_header():
    region = _make_region()
    detector = GridStructureDetector()

    # 3x3 logical grid with a header cell spanning first two columns.
    span_hints = {(0, 0): (1, 2)}
    grid = detector.build_grid(
        region=region,
        n_rows=3,
        n_cols=3,
        table_id="merged-header",
        span_hints=span_hints,
    )

    assert grid.n_rows == 3
    assert grid.n_cols == 3

    # Find the header cell and check spans.
    header_cells = [c for c in grid.cells if c.row_index == 0 and c.col_index == 0]
    assert len(header_cells) == 1
    header = header_cells[0]
    assert header.row_span == 1
    assert header.col_span == 2

    # Other cells should remain 1x1.
    for cell in grid.cells:
        if cell is header:
            continue
        assert cell.row_span == 1
        assert cell.col_span == 1


def test_span_hints_produce_vertically_merged_cell():
    region = _make_region()
    detector = GridStructureDetector()

    # 4x3 logical grid with a cell spanning two rows in the first column.
    span_hints = {(1, 0): (2, 1)}
    grid = detector.build_grid(
        region=region,
        n_rows=4,
        n_cols=3,
        table_id="merged-vertical",
        span_hints=span_hints,
    )

    merged_cells = [c for c in grid.cells if c.row_index == 1 and c.col_index == 0]
    assert len(merged_cells) == 1
    merged = merged_cells[0]
    assert merged.row_span == 2
    assert merged.col_span == 1


def test_build_grid_without_span_hints_remains_backwards_compatible():
    region = _make_region()
    detector = GridStructureDetector()

    grid = detector.build_grid(
        region=region,
        n_rows=2,
        n_cols=3,
        table_id="simple-table",
    )

    assert grid.n_rows == 2
    assert grid.n_cols == 3
    assert len(grid.cells) == 6

    for cell in grid.cells:
        assert 0 <= cell.row_index < grid.n_rows
        assert 0 <= cell.col_index < grid.n_cols
        assert cell.row_span == 1
        assert cell.col_span == 1
        assert cell.bbox is not None
        assert cell.bbox.x1 > cell.bbox.x0
        assert cell.bbox.y1 > cell.bbox.y0




