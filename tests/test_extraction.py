from pdf_reader.extraction import CellTextExtractor, TableAssembler
from pdf_reader.models import BoundingBox, Cell, TableGrid, TableRegion


def _make_simple_grid(n_rows: int, n_cols: int) -> TableGrid:
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


def test_cell_text_extractor_populates_placeholder_text():
    grid = _make_simple_grid(2, 2)
    extractor = CellTextExtractor()

    updated = extractor.fill_cell_text(grid)

    for cell in updated.cells:
        assert cell.text == f"r{cell.row_index}c{cell.col_index}"
        assert cell.text_source == extractor.placeholder_source


def test_table_assembler_builds_dataframe_spec_with_expected_shape_and_values():
    grid = _make_simple_grid(2, 3)
    extractor = CellTextExtractor()
    extractor.fill_cell_text(grid)

    assembler = TableAssembler()
    spec = assembler.to_dataframe_spec(grid)

    assert len(spec.rows) == 2
    assert all(len(row) == 3 for row in spec.rows)
    assert len(spec.columns) == 3

    for r in range(2):
        for c in range(3):
            assert spec.rows[r][c] == f"r{r}c{c}"
            assert spec.columns[c].name == f"col_{c}"




