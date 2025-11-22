from pdf_reader.extraction import TableAssembler
from pdf_reader.models import BoundingBox, Cell, TableGrid, TableRegion


def _make_base_grid(n_rows: int, n_cols: int) -> TableGrid:
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=100.0, y1=100.0)
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
                    text=f"r{r}c{c}",
                )
            )

    return TableGrid(
        table_id="grid-span",
        page_index=region.page_index,
        n_rows=n_rows,
        n_cols=n_cols,
        cells=cells,
    )


def test_span_aware_assembly_propagates_horizontally_merged_header():
    grid = _make_base_grid(3, 3)

    # Simulate a header in row 0 spanning columns 0 and 1.
    header_cell = next(c for c in grid.cells if c.row_index == 0 and c.col_index == 0)
    header_cell.text = "HEADER"
    header_cell.col_span = 2

    assembler = TableAssembler()
    spec = assembler.to_dataframe_spec(grid)

    assert len(spec.rows) == 3
    assert all(len(row) == 3 for row in spec.rows)

    # Both covered header positions should contain the header text.
    assert spec.rows[0][0] == "HEADER"
    assert spec.rows[0][1] == "HEADER"


def test_span_aware_assembly_propagates_vertically_merged_body_cell():
    grid = _make_base_grid(4, 3)

    # Body cell at (1, 0) spans two rows.
    merged_cell = next(c for c in grid.cells if c.row_index == 1 and c.col_index == 0)
    merged_cell.text = "CATEGORY"
    merged_cell.row_span = 2

    assembler = TableAssembler()
    spec = assembler.to_dataframe_spec(grid)

    # Expect text propagated to rows 1 and 2 in column 0.
    assert spec.rows[1][0] == "CATEGORY"
    assert spec.rows[2][0] == "CATEGORY"


def test_span_aware_assembly_preserves_simple_table_behavior():
    grid = _make_base_grid(2, 3)
    assembler = TableAssembler()
    spec = assembler.to_dataframe_spec(grid)

    assert len(spec.rows) == 2
    assert all(len(row) == 3 for row in spec.rows)

    for r in range(2):
        for c in range(3):
            # In the non-merged case, each position should contain the original text.
            assert spec.rows[r][c] == f"r{r}c{c}"




