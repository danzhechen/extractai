from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from .detection.line_detection import (
    LineDetectionConfig,
    detect_horizontal_lines,
    detect_vertical_lines,
)
from .models import BoundingBox, Cell, TableGrid, TableRegion


PageImage = Image.Image
logger = logging.getLogger(__name__)


def _pil_to_cv2(image: PageImage) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR image."""

    if image.mode != "RGB":
        image = image.convert("RGB")
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _bbox_to_pixels(
    bbox: BoundingBox, page_width: int, page_height: int
) -> Tuple[int, int, int, int]:
    """Convert a bounding box to absolute pixel coordinates."""

    looks_normalized = (
        0.0 <= bbox.x0 <= 1.0
        and 0.0 <= bbox.y0 <= 1.0
        and 0.0 < bbox.x1 <= 1.0
        and 0.0 < bbox.y1 <= 1.0
    )
    if looks_normalized:
        x0 = int(bbox.x0 * page_width)
        y0 = int(bbox.y0 * page_height)
        x1 = int(bbox.x1 * page_width)
        y1 = int(bbox.y1 * page_height)
    else:
        x0 = int(bbox.x0)
        y0 = int(bbox.y0)
        x1 = int(bbox.x1)
        y1 = int(bbox.y1)

    x0 = max(0, min(x0, page_width))
    x1 = max(0, min(x1, page_width))
    y0 = max(0, min(y0, page_height))
    y1 = max(0, min(y1, page_height))
    return x0, y0, x1, y1


def _relax_line_detection_config(config: LineDetectionConfig) -> LineDetectionConfig:
    """Return a more permissive configuration for thin or faint table lines."""

    def _scaled(value: int, scale: float, minimum: int) -> int:
        return max(minimum, int(round(value * scale)))

    return LineDetectionConfig(
        enable_line_detection=config.enable_line_detection,
        min_line_length=_scaled(config.min_line_length, 0.5, 8),
        gap_tolerance=_scaled(config.gap_tolerance, 0.7, 3),
        horizontal_kernel_size=(
            _scaled(config.horizontal_kernel_size[0], 0.6, 10),
            config.horizontal_kernel_size[1],
        ),
        vertical_kernel_size=(
            config.vertical_kernel_size[0],
            _scaled(config.vertical_kernel_size[1], 0.6, 10),
        ),
        morph_iterations=max(1, config.morph_iterations),
        min_line_separation=max(1, int(round(config.min_line_separation * 0.8))),
    )


@dataclass
class TableRegionDetector:
    """Minimal table region detector.

    For the initial vertical slice, this detector simply returns a single
    region that covers the entire page image. This is sufficient to exercise
    downstream components without committing to a specific detection strategy.
    """

    enable_multi_panel_detection: bool = False
    min_region_area_ratio: float = 0.02
    detection_kernel_size: Tuple[int, int] = (25, 8)

    def detect(self, page_image: PageImage, page_index: int) -> List[TableRegion]:
        width, height = page_image.size

        if not self.enable_multi_panel_detection:
            bbox = BoundingBox(x0=0.0, y0=0.0, x1=float(width), y1=float(height))
            region = TableRegion(page_index=page_index, bbox=bbox, confidence=1.0)
            return [region]

        regions = self._detect_multi_panel_regions(page_image, page_index)
        if regions:
            return regions

        bbox = BoundingBox(x0=0.0, y0=0.0, x1=float(width), y1=float(height))
        region = TableRegion(page_index=page_index, bbox=bbox, confidence=0.5)
        return [region]

    def _detect_multi_panel_regions(
        self, page_image: PageImage, page_index: int
    ) -> List[TableRegion]:
        """Detect distinct table panels using contour analysis."""

        cv_image = _pil_to_cv2(page_image)
        height, width = cv_image.shape[:2]
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 2
        )

        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, self.detection_kernel_size
        )
        dilated = cv2.dilate(binary, kernel, iterations=1)

        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        min_area = self.min_region_area_ratio * width * height
        regions: List[TableRegion] = []
        for idx, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < min_area:
                continue

            pad = max(5, int(0.01 * min(width, height)))
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(width, x + w + pad)
            y1 = min(height, y + h + pad)

            bbox = BoundingBox(x0=float(x0), y0=float(y0), x1=float(x1), y1=float(y1))
            regions.append(
                TableRegion(
                    page_index=page_index,
                    bbox=bbox,
                    confidence=0.8,
                    section_label=f"section_{idx + 1}",
                )
            )

        regions.sort(key=lambda r: (r.bbox.y0, r.bbox.x0))
        return regions


@dataclass
class GridStructureDetector:
    """Grid structure detector with optional span-aware behavior and line detection.

    By default, given a TableRegion, this implementation evenly divides the
    region into an ``n_rows x n_cols`` grid, creating one Cell per grid
    position with ``row_span = col_span = 1``.

    For Story 2.0 (geometric line detection), the detector can optionally use
    actual line detection to identify table borders and grid lines from page
    images, constructing cells based on detected line positions rather than
    even divisions.

    For Story 2.1 (merged cells and spans), the detector can optionally take
    a set of span hints that describe where merged cells should exist in the
    logical grid. This keeps the core behavior simple for basic tables while
    allowing tests or future geometric heuristics to populate ``row_span``
    and ``col_span`` for curated examples.
    """

    line_detection_config: Optional[LineDetectionConfig] = None
    enable_irregular_detection: bool = False
    ragged_mode: Literal["strict", "ragged"] = "strict"
    filler_token: Optional[str] = None
    min_text_height: int = 8
    min_text_width: int = 8
    row_cluster_threshold: float = 0.02
    col_cluster_threshold: float = 0.02

    def _apply_span_hints(
        self,
        cells: List[Cell],
        span_hints: Optional[Dict[Tuple[int, int], Tuple[int, int]]],
    ) -> None:
        """Apply span hints in-place to the given list of cells.

        ``span_hints`` is a mapping from ``(row_index, col_index)`` to
        ``(row_span, col_span)``. Hints must use positive span values; invalid
        hints are ignored defensively rather than raising, to avoid breaking
        callers on partial configurations.
        """
        if not span_hints:
            return

        index_to_cell: Dict[Tuple[int, int], Cell] = {
            (cell.row_index, cell.col_index): cell for cell in cells
        }

        for (row_idx, col_idx), (row_span, col_span) in span_hints.items():
            cell = index_to_cell.get((row_idx, col_idx))
            if cell is None:
                continue
            if row_span <= 0 or col_span <= 0:
                # Ignore invalid spans; invariants are enforced by TableGrid.
                continue
            cell.row_span = row_span
            cell.col_span = col_span

    def build_grid(
        self,
        region: TableRegion,
        n_rows: int,
        n_cols: int,
        table_id: str = "t1",
        span_hints: Optional[Dict[Tuple[int, int], Tuple[int, int]]] = None,
        page_image: Optional[PageImage] = None,
    ) -> TableGrid:
        """Build a table grid from a detected region.

        Args:
            region: Detected table region.
            n_rows: Number of rows (used as fallback if line detection fails).
            n_cols: Number of columns (used as fallback if line detection fails).
            table_id: Unique identifier for the table.
            span_hints: Optional span hints for merged cells.
            page_image: Optional page image for line detection. If provided and
                line detection is enabled, uses detected lines to construct the grid.

        Returns:
            TableGrid with cells constructed from detected lines (if available)
            or even division (fallback).
        """
        if n_rows <= 0 or n_cols <= 0:
            raise ValueError("n_rows and n_cols must be positive")

        # Attempt irregular detection first when explicitly enabled
        if self.enable_irregular_detection and page_image is not None:
            irregular_grid = self._build_grid_from_text_clusters(
                region,
                table_id,
                span_hints,
                page_image,
                base_irregularities=["partial_borders"],
            )
            if irregular_grid is not None:
                return irregular_grid

        # Try line detection if enabled and page_image is provided
        config = self.line_detection_config or LineDetectionConfig()
        grid_from_lines: Optional[TableGrid] = None
        if config.enable_line_detection and page_image is not None:
            logger.debug(
                "Attempting line detection | table_id=%s | page_index=%s | min_len=%s | gap=%s | morph_iter=%s",
                table_id,
                region.page_index,
                config.min_line_length,
                config.gap_tolerance,
                config.morph_iterations,
            )
            grid_from_lines = self._build_grid_from_lines(
                region, n_rows, n_cols, table_id, span_hints, page_image, config
            )
            if grid_from_lines is not None and not self.enable_irregular_detection:
                logger.debug(
                    "Line detection succeeded | table_id=%s | page_index=%s | rows=%s | cols=%s",
                    table_id,
                    region.page_index,
                    grid_from_lines.n_rows,
                    grid_from_lines.n_cols,
                )
                return grid_from_lines
        elif not config.enable_line_detection:
            logger.debug(
                "Line detection disabled via config | table_id=%s | page_index=%s",
                table_id,
                region.page_index,
            )
        elif page_image is None:
            logger.debug(
                "Line detection skipped (page image missing) | table_id=%s | page_index=%s",
                table_id,
                region.page_index,
            )

        if self.enable_irregular_detection and page_image is not None and grid_from_lines is None:
            irregular_grid = self._build_grid_from_text_clusters(
                region,
                table_id,
                span_hints,
                page_image,
                base_irregularities=["partial_borders"],
            )
            if irregular_grid is not None:
                return irregular_grid

        if grid_from_lines is not None:
            logger.debug(
                "Returning line-detected grid after irregular attempt | table_id=%s | page_index=%s | rows=%s | cols=%s",
                table_id,
                region.page_index,
                grid_from_lines.n_rows,
                grid_from_lines.n_cols,
            )
            return grid_from_lines

        # Fallback to irregular detection when line detection fails entirely
        if self.enable_irregular_detection and page_image is not None:
            irregular_grid = self._build_grid_from_text_clusters(
                region,
                table_id,
                span_hints,
                page_image,
                base_irregularities=["partial_borders"],
            )
            if irregular_grid is not None:
                return irregular_grid

        # Final fallback to even division
        logger.debug(
            "Falling back to even division | table_id=%s | page_index=%s | requested_rows=%s | requested_cols=%s",
            table_id,
            region.page_index,
            n_rows,
            n_cols,
        )
        return self._build_grid_even_division(
            region, n_rows, n_cols, table_id, span_hints
        )

    def _build_grid_from_lines(
        self,
        region: TableRegion,
        n_rows: int,
        n_cols: int,
        table_id: str,
        span_hints: Optional[Dict[Tuple[int, int], Tuple[int, int]]],
        page_image: PageImage,
        config: LineDetectionConfig,
    ) -> Optional[TableGrid]:
        """Build grid from detected lines.

        Returns None if line detection fails or produces invalid results.
        """
        try:
            # Detect lines within the region
            horizontal_lines = detect_horizontal_lines(
                page_image, region=region, config=config
            )
            vertical_lines = detect_vertical_lines(
                page_image, region=region, config=config
            )

            logger.debug(
                "Raw line detection counts | table_id=%s | page_index=%s | horizontal=%s | vertical=%s",
                table_id,
                region.page_index,
                len(horizontal_lines),
                len(vertical_lines),
            )

            # Need at least 2 horizontal lines (top and bottom) and 2 vertical lines (left and right)
            if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
                logger.debug(
                    "Insufficient raw lines detected | table_id=%s | page_index=%s | horizontal=%s | vertical=%s",
                    table_id,
                    region.page_index,
                    len(horizontal_lines),
                    len(vertical_lines),
                )
                relaxed_config = _relax_line_detection_config(config)
                if relaxed_config != config:
                    logger.debug(
                        "Retrying line detection with relaxed parameters | table_id=%s | page_index=%s | min_len=%s | gap=%s | kernels=%s/%s",
                        table_id,
                        region.page_index,
                        relaxed_config.min_line_length,
                        relaxed_config.gap_tolerance,
                        relaxed_config.horizontal_kernel_size,
                        relaxed_config.vertical_kernel_size,
                    )
                    horizontal_lines = detect_horizontal_lines(
                        page_image, region=region, config=relaxed_config
                    )
                    vertical_lines = detect_vertical_lines(
                        page_image, region=region, config=relaxed_config
                    )
                    logger.debug(
                        "Relaxed detection counts | table_id=%s | page_index=%s | horizontal=%s | vertical=%s",
                        table_id,
                        region.page_index,
                        len(horizontal_lines),
                        len(vertical_lines),
                    )
                    config = relaxed_config

            if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
                logger.debug(
                    "Line detection failed after relaxation | table_id=%s | page_index=%s",
                    table_id,
                    region.page_index,
                )
                return None

            # Lines are in pixel coordinates (matching region.bbox convention)
            # Filter lines to be within region bounds and convert to region-relative
            page_width, page_height = page_image.size
            region_x0, region_y0, region_x1, region_y1 = _bbox_to_pixels(
                region.bbox, page_width, page_height
            )
            region_width = region_x1 - region_x0
            region_height = region_y1 - region_y0

            h_lines_in_region = [
                (y - region_y0) / region_height if region_height > 0 else 0.0
                for y in horizontal_lines
                if region_y0 <= y <= region_y1
            ]
            v_lines_in_region = [
                (x - region_x0) / region_width if region_width > 0 else 0.0
                for x in vertical_lines
                if region_x0 <= x <= region_x1
            ]

            logger.debug(
                "Region-clamped line counts | table_id=%s | page_index=%s | horizontal=%s | vertical=%s",
                table_id,
                region.page_index,
                len(h_lines_in_region),
                len(v_lines_in_region),
            )

            # Ensure we have at least top/bottom and left/right boundaries
            if len(h_lines_in_region) < 2 or len(v_lines_in_region) < 2:
                logger.debug(
                    "Not enough region lines after clamping | table_id=%s | page_index=%s",
                    table_id,
                    region.page_index,
                )
                return None

            # Use detected lines to determine row and column boundaries
            # Sort to ensure proper ordering
            h_lines_in_region = sorted(set(h_lines_in_region))
            v_lines_in_region = sorted(set(v_lines_in_region))

            # Determine actual grid dimensions from detected lines
            detected_rows = len(h_lines_in_region) - 1
            detected_cols = len(v_lines_in_region) - 1

            # Use detected dimensions if reasonable, otherwise fall back to provided n_rows/n_cols
            if detected_rows > 0 and detected_cols > 0:
                n_rows = detected_rows
                n_cols = detected_cols
            else:
                return None

            # Build cells from line intersections
            # h_lines_in_region and v_lines_in_region are in region-relative coordinates (0.0-1.0)
            cells: List[Cell] = []
            for r in range(n_rows):
                for c in range(n_cols):
                    # Cell boundaries from line positions (convert back to absolute pixel coordinates)
                    x0 = region_x0 + v_lines_in_region[c] * region_width
                    y0 = region_y0 + h_lines_in_region[r] * region_height
                    x1 = region_x0 + (
                        v_lines_in_region[c + 1] * region_width
                        if c + 1 < len(v_lines_in_region)
                        else region_x1
                    )
                    y1 = region_y0 + (
                        h_lines_in_region[r + 1] * region_height
                        if r + 1 < len(h_lines_in_region)
                        else region_y1
                    )

                    cell_bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
                    cells.append(
                        Cell(
                            row_index=r,
                            col_index=c,
                            row_span=1,
                            col_span=1,
                            bbox=cell_bbox,
                        )
                    )

            # Apply span hints
            self._apply_span_hints(cells, span_hints)

            return TableGrid(
                table_id=table_id,
                page_index=region.page_index,
                n_rows=n_rows,
                n_cols=n_cols,
                cells=cells,
                irregularities=[],
                structure_confidence=1.0,
                section_labels=[region.section_label]
                if region.section_label
                else None,
            )
        except Exception as exc:
            logger.exception(
                "Line detection raised exception | table_id=%s | page_index=%s | error=%s",
                table_id,
                region.page_index,
                exc,
            )
            # If line detection fails, return None to trigger fallback
            return None

    def _build_grid_from_text_clusters(
        self,
        region: TableRegion,
        table_id: str,
        span_hints: Optional[Dict[Tuple[int, int], Tuple[int, int]]],
        page_image: PageImage,
        base_irregularities: Optional[List[str]],
    ) -> Optional[TableGrid]:
        """Build a grid by clustering text blocks (supports ragged tables)."""

        page_width, page_height = page_image.size
        region_x0, region_y0, region_x1, region_y1 = _bbox_to_pixels(
            region.bbox, page_width, page_height
        )
        region_width = region_x1 - region_x0
        region_height = region_y1 - region_y0

        if region_width <= 0 or region_height <= 0:
            return None

        cv_image = _pil_to_cv2(page_image)
        roi = cv_image[region_y0:region_y1, region_x0:region_x1]
        if roi.size == 0:
            return None

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 2
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(
            processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        min_text_height_px = max(self.min_text_height, int(0.01 * region_height))
        min_text_width_px = max(self.min_text_width, int(0.01 * region_width))

        boxes: List[Dict[str, float]] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < min_text_width_px or h < min_text_height_px:
                continue
            boxes.append(
                {
                    "x0": float(x),
                    "y0": float(y),
                    "x1": float(x + w),
                    "y1": float(y + h),
                    "center_x": float(x + w / 2.0),
                    "center_y": float(y + h / 2.0),
                }
            )

        if not boxes:
            return None

        row_threshold_px = max(4, int(self.row_cluster_threshold * region_height))
        col_threshold_px = max(4, int(self.col_cluster_threshold * region_width))

        row_clusters = self._cluster_boxes(boxes, "center_y", row_threshold_px)
        col_clusters = self._cluster_boxes(boxes, "center_x", col_threshold_px)

        if not row_clusters or not col_clusters:
            return None

        for idx, col_cluster in enumerate(col_clusters):
            col_cluster["index"] = idx
            col_cluster["min_x0"] = min(box["x0"] for box in col_cluster["boxes"])
            col_cluster["max_x1"] = max(box["x1"] for box in col_cluster["boxes"])

        def _match_column(center_x: float) -> int:
            return min(
                range(len(col_clusters)),
                key=lambda idx: abs(center_x - col_clusters[idx]["center"]),
            )

        for box in boxes:
            box["column_index"] = _match_column(box["center_x"])

        n_rows = len(row_clusters)
        n_cols = len(col_clusters)
        total_cells = n_rows * n_cols
        if total_cells == 0:
            return None

        col_padding = max(2, int(0.01 * region_width))
        row_padding = max(2, int(0.01 * region_height))

        cells: List[Cell] = []
        filler_cells = 0
        explicit_cells = 0

        for row_idx, row_cluster in enumerate(row_clusters):
            row_boxes = row_cluster["boxes"]
            row_assignments: Dict[int, Dict[str, float]] = {
                int(box["column_index"]): box for box in row_boxes
            }
            row_y0 = min(box["y0"] for box in row_boxes)
            row_y1 = max(box["y1"] for box in row_boxes)
            row_y0 = max(0.0, row_y0 - row_padding)
            row_y1 = min(float(region_height), row_y1 + row_padding)

            for col_cluster in col_clusters:
                col_idx = int(col_cluster["index"])
                if col_idx in row_assignments:
                    box = row_assignments[col_idx]
                    cell_x0 = max(col_cluster["min_x0"], box["x0"] - col_padding)
                    cell_x1 = min(col_cluster["max_x1"], box["x1"] + col_padding)
                    filler = False
                    explicit_cells += 1
                    structure_conf = 0.95
                    structure_source: Literal["explicit", "inferred", "filler"] = "explicit"
                else:
                    filler = True
                    filler_cells += 1
                    structure_conf = 0.5 if self.ragged_mode == "ragged" else 0.2
                    structure_source = "filler"
                    cell_x0 = col_cluster["min_x0"]
                    cell_x1 = col_cluster["max_x1"]

                abs_x0 = float(region_x0 + cell_x0)
                abs_x1 = float(region_x0 + cell_x1)
                abs_y0 = float(region_y0 + row_y0)
                abs_y1 = float(region_y0 + row_y1)

                cell_bbox = BoundingBox(
                    x0=abs_x0,
                    y0=abs_y0,
                    x1=abs_x1,
                    y1=abs_y1,
                )
                cell = Cell(
                    row_index=row_idx,
                    col_index=col_idx,
                    row_span=1,
                    col_span=1,
                    bbox=cell_bbox,
                    structure_confidence=structure_conf,
                    structure_source=structure_source,
                    is_filler=filler,
                )
                cells.append(cell)

        self._apply_span_hints(cells, span_hints)

        irregularities = list(base_irregularities or [])
        if filler_cells > 0:
            irregularities.append("ragged_columns")

        structure_confidence = (
            explicit_cells / total_cells if total_cells > 0 else 0.0
        )

        return TableGrid(
            table_id=table_id,
            page_index=region.page_index,
            n_rows=n_rows,
            n_cols=n_cols,
            cells=cells,
            irregularities=irregularities,
            structure_confidence=structure_confidence,
            section_labels=[region.section_label]
            if region.section_label
            else None,
        )

    def _cluster_boxes(
        self,
        boxes: List[Dict[str, float]],
        key: str,
        threshold: float,
    ) -> List[Dict[str, float]]:
        """Cluster bounding boxes along a given axis."""

        if threshold <= 0:
            threshold = 1.0

        clusters: List[Dict[str, float]] = []
        for box in sorted(boxes, key=lambda b: b[key]):
            placed = False
            for cluster in clusters:
                if abs(box[key] - cluster["center"]) <= threshold:
                    cluster["boxes"].append(box)
                    count = len(cluster["boxes"])
                    cluster["center"] = (
                        cluster["center"] * (count - 1) + box[key]
                    ) / count
                    placed = True
                    break
            if not placed:
                clusters.append({"boxes": [box], "center": box[key]})

        return clusters

    def _build_grid_even_division(
        self,
        region: TableRegion,
        n_rows: int,
        n_cols: int,
        table_id: str,
        span_hints: Optional[Dict[Tuple[int, int], Tuple[int, int]]],
    ) -> TableGrid:
        """Build grid using even division (original behavior)."""
        width = region.bbox.x1 - region.bbox.x0
        height = region.bbox.y1 - region.bbox.y0
        cell_width = width / n_cols
        cell_height = height / n_rows

        cells: List[Cell] = []
        for r in range(n_rows):
            for c in range(n_cols):
                x0 = region.bbox.x0 + c * cell_width
                y0 = region.bbox.y0 + r * cell_height
                x1 = x0 + cell_width
                y1 = y0 + cell_height
                cell_bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
                cells.append(
                    Cell(
                        row_index=r,
                        col_index=c,
                        row_span=1,
                        col_span=1,
                        bbox=cell_bbox,
                    )
                )

        # Apply any span hints after constructing the base grid so that
        # simple tables (no hints) retain the original behavior.
        self._apply_span_hints(cells, span_hints)

        return TableGrid(
            table_id=table_id,
            page_index=region.page_index,
            n_rows=n_rows,
            n_cols=n_cols,
            cells=cells,
            irregularities=[],
            structure_confidence=1.0,
            section_labels=[region.section_label]
            if region.section_label
            else None,
        )


