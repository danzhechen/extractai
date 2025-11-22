"""
Ground truth annotation format and utilities.

This module defines the schema for ground truth annotations and provides
utilities for loading, validating, and creating annotations.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from ..models import BoundingBox, Cell, TableGrid


@dataclass
class GroundTruthCell:
    """Ground truth annotation for a single cell.
    
    Attributes:
        row: Row index (0-based)
        col: Column index (0-based)
        rowspan: Number of rows spanned
        colspan: Number of columns spanned
        text: Cell text content
        bbox: Optional bounding box (normalized 0-1 coordinates)
    """
    
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    text: str = ""
    bbox: Optional[dict] = None  # {x0, y0, x1, y1}


@dataclass
class GroundTruthTable:
    """Ground truth annotation for a single table.
    
    Attributes:
        table_id: Unique identifier for the table
        bbox: Bounding box for entire table (normalized 0-1 coordinates)
        n_rows: Number of rows in table
        n_cols: Number of columns in table
        cells: List of cell annotations
    """
    
    table_id: str
    bbox: dict  # {x0, y0, x1, y1}
    n_rows: int
    n_cols: int
    cells: List[GroundTruthCell] = field(default_factory=list)


@dataclass
class GroundTruthAnnotation:
    """Ground truth annotation for a PDF page.
    
    Attributes:
        pdf_file: Name of PDF file
        page_index: Page index (0-based)
        tables: List of table annotations
        metadata: Optional metadata (source, license, annotator, etc.)
    """
    
    pdf_file: str
    page_index: int
    tables: List[GroundTruthTable] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def load_annotation(annotation_path: Path) -> GroundTruthAnnotation:
    """Load ground truth annotation from JSON file.
    
    Args:
        annotation_path: Path to annotation JSON file
        
    Returns:
        GroundTruthAnnotation object
        
    Raises:
        FileNotFoundError: If annotation file doesn't exist
        ValueError: If annotation format is invalid
    """
    if not annotation_path.exists():
        raise FileNotFoundError(f"Annotation file not found: {annotation_path}")
    
    with open(annotation_path) as f:
        data = json.load(f)
    
    # Parse annotation
    tables = []
    for table_data in data.get("tables", []):
        cells = []
        for cell_data in table_data.get("cells", []):
            cell = GroundTruthCell(**cell_data)
            cells.append(cell)
        
        table = GroundTruthTable(
            table_id=table_data["table_id"],
            bbox=table_data["bbox"],
            n_rows=table_data["n_rows"],
            n_cols=table_data["n_cols"],
            cells=cells,
        )
        tables.append(table)
    
    annotation = GroundTruthAnnotation(
        pdf_file=data["pdf_file"],
        page_index=data["page_index"],
        tables=tables,
        metadata=data.get("metadata", {}),
    )
    
    return annotation


def save_annotation(annotation: GroundTruthAnnotation, annotation_path: Path) -> None:
    """Save ground truth annotation to JSON file.
    
    Args:
        annotation: GroundTruthAnnotation object
        annotation_path: Path to save annotation JSON file
    """
    data = asdict(annotation)
    
    annotation_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(annotation_path, "w") as f:
        json.dump(data, f, indent=2)


def annotation_to_table_grid(annotation_table: GroundTruthTable) -> TableGrid:
    """Convert ground truth table annotation to TableGrid format.
    
    Args:
        annotation_table: Ground truth table annotation
        
    Returns:
        TableGrid object for comparison with pipeline output
    """
    cells = []
    
    for cell_data in annotation_table.cells:
        bbox = None
        if cell_data.bbox:
            bbox = BoundingBox(
                x0=cell_data.bbox["x0"],
                y0=cell_data.bbox["y0"],
                x1=cell_data.bbox["x1"],
                y1=cell_data.bbox["y1"],
            )
        
        cell = Cell(
            row_index=cell_data.row,
            col_index=cell_data.col,
            row_span=cell_data.rowspan,
            col_span=cell_data.colspan,
            text=cell_data.text,
            bbox=bbox,
        )
        cells.append(cell)
    
    table_grid = TableGrid(
        table_id=annotation_table.table_id,
        page_index=0,  # Set by caller if needed
        n_rows=annotation_table.n_rows,
        n_cols=annotation_table.n_cols,
        cells=cells,
    )
    
    return table_grid


def validate_annotation(annotation: GroundTruthAnnotation) -> List[str]:
    """Validate ground truth annotation for consistency.
    
    Args:
        annotation: GroundTruthAnnotation to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    for i, table in enumerate(annotation.tables):
        # Check table dimensions
        if table.n_rows <= 0:
            errors.append(f"Table {i}: n_rows must be positive, got {table.n_rows}")
        if table.n_cols <= 0:
            errors.append(f"Table {i}: n_cols must be positive, got {table.n_cols}")
        
        # Check cell positions
        for j, cell in enumerate(table.cells):
            if cell.row < 0 or cell.row >= table.n_rows:
                errors.append(
                    f"Table {i}, Cell {j}: row {cell.row} out of range [0, {table.n_rows})"
                )
            if cell.col < 0 or cell.col >= table.n_cols:
                errors.append(
                    f"Table {i}, Cell {j}: col {cell.col} out of range [0, {table.n_cols})"
                )
            
            # Check spans
            if cell.rowspan <= 0:
                errors.append(f"Table {i}, Cell {j}: rowspan must be positive")
            if cell.colspan <= 0:
                errors.append(f"Table {i}, Cell {j}: colspan must be positive")
            
            # Check if cell extends beyond table
            if cell.row + cell.rowspan > table.n_rows:
                errors.append(
                    f"Table {i}, Cell {j}: cell extends beyond table "
                    f"(row {cell.row} + rowspan {cell.rowspan} > {table.n_rows})"
                )
            if cell.col + cell.colspan > table.n_cols:
                errors.append(
                    f"Table {i}, Cell {j}: cell extends beyond table "
                    f"(col {cell.col} + colspan {cell.colspan} > {table.n_cols})"
                )
            
            # Check bbox if present
            if cell.bbox:
                bbox = cell.bbox
                if not (0 <= bbox["x0"] <= bbox["x1"] <= 1):
                    errors.append(f"Table {i}, Cell {j}: invalid bbox x coordinates")
                if not (0 <= bbox["y0"] <= bbox["y1"] <= 1):
                    errors.append(f"Table {i}, Cell {j}: invalid bbox y coordinates")
    
    return errors


