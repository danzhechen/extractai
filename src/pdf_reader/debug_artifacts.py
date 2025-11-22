"""Debug artifacts generation for PDF table extraction pipeline.

This module provides utilities for generating visualization artifacts:
- Overlay images showing table regions, grid lines, and cell indices
- HTML reports with summary statistics and extracted tables
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from .models import (
    BoundingBox,
    ExtractionResult,
    TableDataFrameSpec,
    TableGrid,
    TableMetadata,
    TableRegion,
)


def _bbox_to_pixels(
    bbox: BoundingBox, width: int, height: int
) -> tuple[int, int, int, int]:
    """Convert potentially normalized bounding box to absolute pixel coordinates."""

    looks_normalized = (
        0.0 <= bbox.x0 <= 1.0
        and 0.0 <= bbox.y0 <= 1.0
        and 0.0 < bbox.x1 <= 1.0
        and 0.0 < bbox.y1 <= 1.0
    )
    if looks_normalized:
        x0 = int(bbox.x0 * width)
        y0 = int(bbox.y0 * height)
        x1 = int(bbox.x1 * width)
        y1 = int(bbox.y1 * height)
    else:
        x0 = int(bbox.x0)
        y0 = int(bbox.y0)
        x1 = int(bbox.x1)
        y1 = int(bbox.y1)

    return (
        max(0, min(x0, width)),
        max(0, min(y0, height)),
        max(0, min(x1, width)),
        max(0, min(y1, height)),
    )


def draw_table_overlay(
    page_image: Image.Image,
    regions: List[TableRegion],
    grids: List[TableGrid],
    output_path: Path,
) -> None:
    """Draw overlay visualization on a page image showing table structure.

    Args:
        page_image: The original page image (PIL Image).
        regions: List of detected table regions.
        grids: List of TableGrid instances corresponding to regions.
        output_path: Path where the overlay image will be saved.
    """
    # Create a copy of the page image for drawing
    overlay = page_image.copy()
    draw = ImageDraw.Draw(overlay)

    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10)
    except (OSError, IOError):
        # Fall back to default font if system font not available
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Draw table region bounding boxes (green rectangles)
    for region in regions:
        width, height = page_image.size
        x0, y0, x1, y1 = _bbox_to_pixels(region.bbox, width, height)
        draw.rectangle([x0, y0, x1, y1], outline="green", width=3)
        if region.section_label:
            label = region.section_label
            text_box = draw.textbbox((x0 + 4, y0 + 4), label, font=font)
            if text_box:
                draw.rectangle(text_box, fill="green")
                draw.text((x0 + 4, y0 + 4), label, fill="white", font=font)

    # Draw grid lines and cell annotations for each table
    for grid in grids:
        # Find corresponding region
        region = next((r for r in regions if r.page_index == grid.page_index), None)
        if region is None:
            continue

        width, height = page_image.size

        # Draw cell bounding boxes (color-coded)
        for cell in grid.cells:
            if cell.bbox is not None:
                cell_x0, cell_y0, cell_x1, cell_y1 = _bbox_to_pixels(
                    cell.bbox, width, height
                )
                color = "blue"
                if cell.is_filler:
                    color = "orange"
                elif cell.structure_source == "inferred":
                    color = "purple"
                draw.rectangle([cell_x0, cell_y0, cell_x1, cell_y1], outline=color, width=2)

                label = f"R{cell.row_index}C{cell.col_index}"
                text_x = cell_x0 + 4
                text_y = cell_y0 + 4
                bbox_text = draw.textbbox((text_x, text_y), label, font=small_font)
                if bbox_text:
                    draw.rectangle(bbox_text, fill="yellow", outline="black", width=1)
                    draw.text((text_x, text_y), label, fill="black", font=small_font)

    # Save the overlay image
    overlay.save(output_path, "PNG")


def generate_html_report(
    result: ExtractionResult,
    input_pdf_path: str,
    config_summary: dict,
    output_path: Path,
    overlay_image_paths: Optional[List[Path]] = None,
) -> None:
    """Generate an HTML report for a pipeline run.

    Args:
        result: The ExtractionResult from the pipeline run.
        input_pdf_path: Path to the input PDF file.
        config_summary: Dictionary with configuration summary (for display).
        output_path: Path where the HTML report will be saved.
        overlay_image_paths: Optional list of paths to overlay images (relative to report).
    """
    stats = result.run_stats
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build HTML content
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<title>PDF Table Extraction Report</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }",
        "h1 { color: #333; }",
        "h2 { color: #666; margin-top: 30px; }",
        ".section { background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        "table { border-collapse: collapse; width: 100%; margin: 10px 0; }",
        "table th, table td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
        "table th { background-color: #4CAF50; color: white; }",
        "table tr:nth-child(even) { background-color: #f2f2f2; }",
        ".metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }",
        ".metric-item { background-color: #e8f5e9; padding: 10px; border-radius: 5px; }",
        ".metric-label { font-weight: bold; color: #2e7d32; }",
        ".metric-value { font-size: 1.2em; color: #1b5e20; }",
        ".page-section { margin: 20px 0; }",
        ".table-preview { margin: 15px 0; }",
        "a { color: #4CAF50; text-decoration: none; }",
        "a:hover { text-decoration: underline; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>PDF Table Extraction Report</h1>",
        f"<p><strong>Generated:</strong> {html.escape(timestamp)}</p>",
        f"<p><strong>Input PDF:</strong> {html.escape(input_pdf_path)}</p>",
    ]

    # Configuration summary
    if config_summary:
        html_parts.append("<div class='section'>")
        html_parts.append("<h2>Configuration</h2>")
        html_parts.append("<ul>")
        for key, value in config_summary.items():
            html_parts.append(f"<li><strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}</li>")
        html_parts.append("</ul>")
        html_parts.append("</div>")

    # Metrics section
    html_parts.append("<div class='section'>")
    html_parts.append("<h2>Run Statistics</h2>")
    html_parts.append("<div class='metrics'>")
    html_parts.append(f"<div class='metric-item'><span class='metric-label'>Pages Processed:</span><br><span class='metric-value'>{stats.pages_processed}</span></div>")
    html_parts.append(f"<div class='metric-item'><span class='metric-label'>Tables Detected:</span><br><span class='metric-value'>{stats.tables_detected}</span></div>")
    html_parts.append(f"<div class='metric-item'><span class='metric-label'>Tables Extracted:</span><br><span class='metric-value'>{stats.tables_extracted}</span></div>")
    html_parts.append(f"<div class='metric-item'><span class='metric-label'>Total Cells:</span><br><span class='metric-value'>{stats.total_cells_extracted}</span></div>")
    html_parts.append(f"<div class='metric-item'><span class='metric-label'>Average Confidence:</span><br><span class='metric-value'>{stats.average_ocr_confidence:.2f}</span></div>")
    html_parts.append(f"<div class='metric-item'><span class='metric-label'>LLM Fallbacks:</span><br><span class='metric-value'>{stats.llm_fallback_count}</span></div>")
    html_parts.append(f"<div class='metric-item'><span class='metric-label'>Duration:</span><br><span class='metric-value'>{stats.total_duration_ms:.2f} ms</span></div>")
    if stats.pages_skipped > 0 or stats.tables_failed > 0:
        html_parts.append(f"<div class='metric-item'><span class='metric-label'>Pages Skipped:</span><br><span class='metric-value'>{stats.pages_skipped}</span></div>")
        html_parts.append(f"<div class='metric-item'><span class='metric-label'>Tables Failed:</span><br><span class='metric-value'>{stats.tables_failed}</span></div>")
    html_parts.append("</div>")
    html_parts.append("</div>")

    # Overlay images section
    if overlay_image_paths:
        html_parts.append("<div class='section'>")
        html_parts.append("<h2>Overlay Images</h2>")
        html_parts.append("<ul>")
        for overlay_path in overlay_image_paths:
            # Use relative path from report location
            rel_path = overlay_path.name if overlay_path.parent == output_path.parent else str(overlay_path.relative_to(output_path.parent))
            html_parts.append(f"<li><a href='{html.escape(rel_path)}'>{html.escape(overlay_path.name)}</a></li>")
        html_parts.append("</ul>")
        html_parts.append("</div>")

    # Sample tables section
    html_parts.append("<div class='section'>")
    html_parts.append("<h2>Extracted Tables</h2>")

    # Group tables by page
    tables_by_page: dict[int, List[tuple[TableDataFrameSpec, TableMetadata]]] = {}
    for table_spec, metadata in zip(result.tables, result.metadata):
        if metadata.status == "success":
            page_idx = metadata.page_index
            if page_idx not in tables_by_page:
                tables_by_page[page_idx] = []
            tables_by_page[page_idx].append((table_spec, metadata))

    for page_idx in sorted(tables_by_page.keys()):
        html_parts.append(f"<div class='page-section'>")
        html_parts.append(f"<h3>Page {page_idx}</h3>")

        for table_spec, metadata in tables_by_page[page_idx]:
            html_parts.append("<div class='table-preview'>")
            html_parts.append(f"<p><strong>Table ID:</strong> {html.escape(metadata.table_id)} | ")
            html_parts.append(f"<strong>Cells:</strong> {metadata.cell_count} | ")
            html_parts.append(f"<strong>Confidence:</strong> {metadata.average_confidence:.2f}</p>")
            if getattr(metadata, "irregularities", None):
                issues = ", ".join(metadata.irregularities)
                html_parts.append(
                    f"<p><strong>Irregularities:</strong> {html.escape(issues)} "
                    f"(structure confidence {getattr(metadata, 'structure_confidence', 0.0):.2f})</p>"
                )
            if getattr(metadata, "section_labels", None):
                sections = ", ".join(metadata.section_labels or [])
                html_parts.append(
                    f"<p><strong>Sections:</strong> {html.escape(sections)}</p>"
                )

            # Render table as HTML
            html_parts.append("<table>")
            # Header row (if columns have names)
            if table_spec.columns:
                html_parts.append("<thead><tr>")
                for col in table_spec.columns:
                    html_parts.append(f"<th>{html.escape(col.name)}</th>")
                html_parts.append("</tr></thead>")

            # Data rows
            html_parts.append("<tbody>")
            for row in table_spec.rows:
                html_parts.append("<tr>")
                for cell_value in row:
                    display_value = html.escape(str(cell_value)) if cell_value is not None else ""
                    html_parts.append(f"<td>{display_value}</td>")
                html_parts.append("</tr>")
            html_parts.append("</tbody>")
            html_parts.append("</table>")
            html_parts.append("</div>")

        html_parts.append("</div>")

    html_parts.append("</div>")

    # Errors section (if any)
    if stats.errors:
        html_parts.append("<div class='section'>")
        html_parts.append("<h2>Errors</h2>")
        html_parts.append("<ul>")
        for error in stats.errors:
            html_parts.append(f"<li>{html.escape(error)}</li>")
        html_parts.append("</ul>")
        html_parts.append("</div>")

    html_parts.append("</body>")
    html_parts.append("</html>")

    # Write HTML file
    output_path.write_text("\n".join(html_parts))

