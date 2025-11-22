from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PIL import Image

from .llm_extraction import LLMExtractionService, LLMExtractionError
from .models import Cell, ColumnSpec, TableDataFrameSpec, TableGrid

PageImage = Image.Image


@dataclass
class CellTextExtractor:
    """Cell text extractor with OCR and optional LLM fallback.

    This extractor fills in cell text using a primary method (currently placeholder
    text, but designed to support OCR). When OCR confidence is below a threshold
    and LLM fallback is enabled, it uses an LLM service to extract text.

    Attributes:
        placeholder_source: Source identifier for placeholder text (default: "mock").
        ocr_confidence_threshold: Confidence threshold below which LLM fallback is triggered.
        llm_fallback_enabled: Whether to use LLM fallback for low-confidence cells.
        llm_service: Optional LLM extraction service for fallback.
    """

    placeholder_source: str = "mock"
    ocr_confidence_threshold: float = 0.5
    llm_fallback_enabled: bool = False
    llm_service: Optional[LLMExtractionService] = None

    def _extract_with_ocr(self, cell: Cell, page_image: Optional[PageImage] = None) -> tuple[str, float]:
        """Extract text using primary OCR method (placeholder for now).

        Returns:
            Tuple of (extracted_text, confidence_score).
        """
        # For now, use placeholder text with simulated confidence
        # In a real implementation, this would call actual OCR
        text = f"r{cell.row_index}c{cell.col_index}"
        # Simulate confidence: use a default high confidence for placeholder
        confidence = 0.9
        return text, confidence

    def _extract_with_llm(
        self, cell: Cell, page_image: Optional[PageImage] = None
    ) -> str:
        """Extract text using LLM fallback.

        Args:
            cell: Cell to extract text from.
            page_image: Optional full page image for context.

        Returns:
            Extracted text string.

        Raises:
            LLMExtractionError: If LLM extraction fails.
        """
        if self.llm_service is None:
            raise LLMExtractionError("LLM service not configured")

        # Crop cell region from page image if available
        if page_image is not None and cell.bbox is not None:
            bbox = cell.bbox
            cell_image = page_image.crop((bbox.x0, bbox.y0, bbox.x1, bbox.y1))
        else:
            # Create a small placeholder image if no bbox/page_image
            cell_image = Image.new("RGB", (100, 50), color="white")

        context = f"table cell at row {cell.row_index}, column {cell.col_index}"
        return self.llm_service.extract_text_from_image(cell_image, context=context)

    def fill_cell_text(
        self, grid: TableGrid, page_image: Optional[PageImage] = None
    ) -> TableGrid:
        """Populate Cell.text for any empty cells, using OCR with optional LLM fallback.

        Args:
            grid: TableGrid to populate.
            page_image: Optional full page image for LLM fallback context.

        Returns:
            Updated TableGrid with populated cell text.
        """
        for cell in grid.cells:
            if not cell.text:
                # Try primary OCR extraction
                text, confidence = self._extract_with_ocr(cell, page_image)
                cell.text_confidence = confidence

                # Check if we should use LLM fallback
                if (
                    self.llm_fallback_enabled
                    and self.llm_service is not None
                    and confidence < self.ocr_confidence_threshold
                ):
                    try:
                        text = self._extract_with_llm(cell, page_image)
                        cell.text_source = "llm_fallback"  # type: ignore[assignment]
                    except LLMExtractionError:
                        # If LLM fails, fall back to OCR result
                        # Use placeholder_source for backward compatibility with placeholder text
                        cell.text_source = self.placeholder_source  # type: ignore[assignment]
                else:
                    # Use placeholder_source for backward compatibility when using placeholder text
                    # In the future, when real OCR is implemented, this should be "ocr"
                    cell.text_source = self.placeholder_source  # type: ignore[assignment]

                cell.text = text

        return grid


@dataclass
class TableAssembler:
    """Convert a TableGrid into a TableDataFrameSpec suitable for dataframe use.

    Span resolution strategy (Story 2.2):
    - For cells with ``row_span`` or ``col_span`` greater than 1, this assembler
      **propagates the cell's text into every covered output position**.
    - Non-merged cells remain 1x1 and behave as before.
    - If multiple cells map to the same output position, the first encountered
      wins; later writes are ignored. This keeps behavior deterministic while
      avoiding hard failures on mildly inconsistent grids.

    This strategy is simple and predictable for downstream users and remains
    compatible with earlier stories where all spans are 1x1.
    """

    def to_dataframe_spec(
        self, grid: TableGrid, filler_value: Optional[str] = None
    ) -> TableDataFrameSpec:
        rows: List[List[Optional[str]]] = [
            [None for _ in range(grid.n_cols)] for _ in range(grid.n_rows)
        ]

        for cell in grid.cells:
            # Guard against out-of-range indices in case of malformed grids
            if cell.row_span <= 0 or cell.col_span <= 0:
                continue

            start_row = cell.row_index
            start_col = cell.col_index
            end_row = start_row + cell.row_span
            end_col = start_col + cell.col_span

            for r in range(start_row, end_row):
                if not (0 <= r < grid.n_rows):
                    continue
                for c in range(start_col, end_col):
                    if not (0 <= c < grid.n_cols):
                        continue
                    # First-write-wins: do not overwrite existing values.
                    if rows[r][c] is None:
                        if cell.is_filler and filler_value is not None:
                            value = filler_value
                        else:
                            value = cell.text
                        rows[r][c] = value

        columns = [
            ColumnSpec(name=f"col_{c}", level=0) for c in range(grid.n_cols)
        ]

        return TableDataFrameSpec(
            rows=rows,
            columns=columns,
            table_metadata_id=f"{grid.table_id}-meta",
        )


