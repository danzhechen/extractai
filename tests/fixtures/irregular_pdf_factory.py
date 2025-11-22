"""
Utilities for generating PDF fixtures that capture irregular table scenarios.

These helpers intentionally construct partially bordered tables, ragged schedules,
and multi-panel layouts to exercise Story 3.2 behaviors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def _init_canvas(path: Path) -> canvas.Canvas:
    """Create a canvas helper and ensure the directory exists."""

    path.parent.mkdir(parents=True, exist_ok=True)
    return canvas.Canvas(str(path), pagesize=letter)


def _draw_row_text(
    c: canvas.Canvas,
    entries: Iterable[Tuple[float, float, str]],
    font: str = "Helvetica",
    size: int = 11,
) -> None:
    """Draw multiple pieces of text for a single row."""

    c.setFont(font, size)
    for x, y, text in entries:
        c.drawString(x, y, text)


def create_partial_borders_pdf(tmp_dir: Path) -> Path:
    """
    Create a PDF that mimics a partially bordered financial statement.

    The table only has an outer border plus a few horizontal lines. Internal
    vertical lines are missing to force partial-border heuristics.
    """

    path = tmp_dir / "partial_borders.pdf"
    c = _init_canvas(path)
    page_width, page_height = letter

    table_x = 50
    table_y = page_height - 260
    table_width = page_width - 100
    table_height = 170

    c.setFont("Helvetica-Bold", 14)
    c.drawString(table_x, table_y + table_height + 20, "Consolidated Statement (Partial Borders)")

    c.setLineWidth(2)
    c.rect(table_x, table_y, table_width, table_height, stroke=1, fill=0)
    # A couple of horizontal separators but no vertical internal borders
    c.line(table_x, table_y + table_height - 45, table_x + table_width, table_y + table_height - 45)
    c.line(table_x, table_y + table_height - 90, table_x + table_width, table_y + table_height - 90)

    rows = [
        ("Revenue", "$ 1,240"),
        ("Cost of Goods Sold", "($ 730)"),
        ("Gross Profit", "$ 510"),
        ("Operating Expenses", "($ 180)"),
        ("Operating Income", "$ 330"),
    ]

    c.setFont("Helvetica", 12)
    for idx, (label, value) in enumerate(rows):
        y = table_y + table_height - 30 - idx * 32
        c.drawString(table_x + 12, y, label)
        c.drawRightString(table_x + table_width - 12, y, value)

    c.save()
    return path


def create_ragged_schedule_pdf(tmp_dir: Path) -> Path:
    """
    Create a PDF that simulates a ragged schedule.

    Some rows intentionally omit columns so the detector must insert filler cells.
    """

    path = tmp_dir / "ragged_schedule.pdf"
    c = _init_canvas(path)
    _, page_height = letter

    start_y = page_height - 80
    c.setFont("Helvetica-Bold", 13)
    c.drawString(60, start_y + 30, "Monthly Staffing Schedule (Ragged)")

    headers = [("Month", 60), ("Headcount", 210), ("Budget", 360)]
    c.setFont("Helvetica-Bold", 11)
    for label, x in headers:
        c.drawString(x, start_y, label)
    c.line(50, start_y - 5, 500, start_y - 5)

    rows = [
        ("Jan", "42", "40"),
        ("Feb", "39", None),  # missing budget
        ("Mar", None, "41"),  # missing actual/headcount
        ("Apr", "44", "43"),
        ("May", "37", None),
    ]

    y = start_y - 30
    c.setFont("Helvetica", 11)
    for month, actual, budget in rows:
        c.drawString(60, y, month)
        if actual is not None:
            c.drawString(210, y, actual)
        if budget is not None:
            c.drawString(360, y, budget)
        y -= 28

    c.save()
    return path


def create_multi_panel_pdf(tmp_dir: Path) -> Path:
    """
    Create a PDF with two stacked tables representing regional panels.

    Each panel is boxed separately so the region detector can assign section labels.
    """

    path = tmp_dir / "multi_panel.pdf"
    c = _init_canvas(path)
    page_width, page_height = letter

    panel_width = page_width - 120
    panel_height = 120
    start_y = page_height - 140

    sections = [
        ("North Region", [("Product A", "$ 120k"), ("Product B", "$ 98k"), ("Product C", "$ 76k")]),
        ("South Region", [("Product A", "$ 88k"), ("Product B", "$ 104k"), ("Product C", "$ 91k")]),
    ]

    for idx, (label, entries) in enumerate(sections):
        y = start_y - idx * (panel_height + 80)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(70, y + panel_height + 20, label)

        c.setLineWidth(1.5)
        c.rect(60, y, panel_width, panel_height, stroke=1, fill=0)
        c.line(200, y, 200, y + panel_height)
        c.line(60, y + panel_height - 40, 60 + panel_width, y + panel_height - 40)

        row_y = y + panel_height - 55
        c.setFont("Helvetica", 11)
        for product, value in entries:
            c.drawString(70, row_y, product)
            c.drawRightString(60 + panel_width - 10, row_y, value)
            row_y -= 30

    c.save()
    return path


__all__ = [
    "create_partial_borders_pdf",
    "create_ragged_schedule_pdf",
    "create_multi_panel_pdf",
]



