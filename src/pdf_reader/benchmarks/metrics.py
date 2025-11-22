"""
Evaluation metrics for benchmarking table extraction accuracy.

This module implements various metrics for comparing extracted tables against
ground truth annotations:

- Structural metrics: IoU, grid shape accuracy, span correctness
- Text metrics: CER, WER, exact match rate
- Detection metrics: Precision, recall, F1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..models import BoundingBox, Cell, TableGrid


@dataclass
class CellMetrics:
    """Metrics for a single cell comparison.
    
    Attributes:
        iou: Intersection over Union for bounding box (0.0-1.0)
        text_match: Whether text exactly matches (True/False)
        cer: Character Error Rate for text (0.0-1.0, lower is better)
        wer: Word Error Rate for text (0.0-1.0, lower is better)
        span_match: Whether row_span and col_span match (True/False)
    """
    
    iou: float = 0.0
    text_match: bool = False
    cer: float = 1.0
    wer: float = 1.0
    span_match: bool = False


@dataclass
class TableMetrics:
    """Metrics for a single table comparison.
    
    Attributes:
        table_id: Identifier for the table
        grid_shape_match: Whether n_rows and n_cols match ground truth
        n_rows_predicted: Number of rows in predicted table
        n_rows_ground_truth: Number of rows in ground truth
        n_cols_predicted: Number of columns in predicted table
        n_cols_ground_truth: Number of columns in ground truth
        cell_metrics: List of metrics for each matched cell
        avg_cell_iou: Average IoU across all cells
        avg_cer: Average CER across all cells with text
        avg_wer: Average WER across all cells with text
        exact_match_rate: Percentage of cells with exact text match
        span_accuracy: Percentage of cells with correct spans
    """
    
    table_id: str
    grid_shape_match: bool = False
    n_rows_predicted: int = 0
    n_rows_ground_truth: int = 0
    n_cols_predicted: int = 0
    n_cols_ground_truth: int = 0
    cell_metrics: List[CellMetrics] = field(default_factory=list)
    avg_cell_iou: float = 0.0
    avg_cer: float = 1.0
    avg_wer: float = 1.0
    exact_match_rate: float = 0.0
    span_accuracy: float = 0.0


@dataclass
class BenchmarkResult:
    """Overall benchmark results across entire dataset.
    
    Attributes:
        table_metrics: Metrics for each table in dataset
        
        # Detection metrics
        tables_detected: Number of tables detected
        tables_ground_truth: Number of tables in ground truth
        table_detection_precision: Precision for table detection
        table_detection_recall: Recall for table detection
        table_detection_f1: F1 score for table detection
        
        # Aggregated structural metrics
        avg_grid_shape_accuracy: Percentage of tables with correct grid shape
        avg_cell_iou: Average IoU across all cells
        avg_span_accuracy: Percentage of cells with correct spans
        
        # Aggregated text metrics
        avg_cer: Average CER across all cells
        avg_wer: Average WER across all cells
        exact_match_rate: Percentage of cells with exact text match
        
        # Overall score
        structural_f1: Harmonic mean of structural metrics
        text_f1: Harmonic mean of text metrics
        overall_f1: Harmonic mean of structural and text F1
        
        # Confidence intervals (optional)
        ci_lower: Lower bound of 95% confidence interval for overall_f1
        ci_upper: Upper bound of 95% confidence interval for overall_f1
    """
    
    table_metrics: List[TableMetrics] = field(default_factory=list)
    
    # Detection metrics
    tables_detected: int = 0
    tables_ground_truth: int = 0
    table_detection_precision: float = 0.0
    table_detection_recall: float = 0.0
    table_detection_f1: float = 0.0
    
    # Aggregated structural metrics
    avg_grid_shape_accuracy: float = 0.0
    avg_cell_iou: float = 0.0
    avg_span_accuracy: float = 0.0
    
    # Aggregated text metrics
    avg_cer: float = 1.0
    avg_wer: float = 1.0
    exact_match_rate: float = 0.0
    
    # Overall scores
    structural_f1: float = 0.0
    text_f1: float = 0.0
    overall_f1: float = 0.0
    
    # Confidence intervals
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


def compute_bbox_intersection(bbox1: BoundingBox, bbox2: BoundingBox) -> float:
    """Compute intersection area of two bounding boxes.
    
    Args:
        bbox1: First bounding box
        bbox2: Second bounding box
        
    Returns:
        Intersection area (0.0-1.0 in normalized coordinates)
    """
    # Compute intersection rectangle
    x_left = max(bbox1.x0, bbox2.x0)
    y_top = max(bbox1.y0, bbox2.y0)
    x_right = min(bbox1.x1, bbox2.x1)
    y_bottom = min(bbox1.y1, bbox2.y1)
    
    # Check if boxes intersect
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    # Compute intersection area
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    return intersection_area


def compute_bbox_union(bbox1: BoundingBox, bbox2: BoundingBox) -> float:
    """Compute union area of two bounding boxes.
    
    Args:
        bbox1: First bounding box
        bbox2: Second bounding box
        
    Returns:
        Union area (0.0-1.0 in normalized coordinates)
    """
    area1 = (bbox1.x1 - bbox1.x0) * (bbox1.y1 - bbox1.y0)
    area2 = (bbox2.x1 - bbox2.x0) * (bbox2.y1 - bbox2.y0)
    intersection = compute_bbox_intersection(bbox1, bbox2)
    
    return area1 + area2 - intersection


def compute_cell_iou(cell1: Cell, cell2: Cell) -> float:
    """Compute Intersection over Union for cell bounding boxes.
    
    Args:
        cell1: First cell (predicted)
        cell2: Second cell (ground truth)
        
    Returns:
        IoU score (0.0-1.0), or 0.0 if either cell has no bbox
    """
    if cell1.bbox is None or cell2.bbox is None:
        return 0.0
    
    intersection = compute_bbox_intersection(cell1.bbox, cell2.bbox)
    union = compute_bbox_union(cell1.bbox, cell2.bbox)
    
    if union == 0.0:
        return 0.0
    
    return intersection / union


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein (edit) distance between two strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Minimum number of single-character edits required
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def compute_cer(predicted: str, ground_truth: str) -> float:
    """Compute Character Error Rate using Levenshtein distance.
    
    Args:
        predicted: Predicted text
        ground_truth: Ground truth text
        
    Returns:
        CER (0.0-1.0, lower is better), or 0.0 if ground_truth is empty
    """
    if not ground_truth:
        return 0.0 if not predicted else 1.0
    
    distance = levenshtein_distance(predicted, ground_truth)
    return distance / len(ground_truth)


def compute_wer(predicted: str, ground_truth: str) -> float:
    """Compute Word Error Rate using Levenshtein distance on words.
    
    Args:
        predicted: Predicted text
        ground_truth: Ground truth text
        
    Returns:
        WER (0.0-1.0, lower is better), or 0.0 if ground_truth has no words
    """
    predicted_words = predicted.split()
    ground_truth_words = ground_truth.split()
    
    if not ground_truth_words:
        return 0.0 if not predicted_words else 1.0
    
    # Use levenshtein distance on word sequences
    # For simplicity, convert to space-separated string and compute CER
    # (proper WER would use word-level edit distance)
    distance = levenshtein_distance(
        " ".join(predicted_words),
        " ".join(ground_truth_words)
    )
    
    return distance / len(" ".join(ground_truth_words))


def compare_cells(predicted: Cell, ground_truth: Cell) -> CellMetrics:
    """Compare predicted cell against ground truth.
    
    Args:
        predicted: Predicted cell
        ground_truth: Ground truth cell
        
    Returns:
        CellMetrics with comparison results
    """
    metrics = CellMetrics()
    
    # Compute IoU for bounding boxes
    metrics.iou = compute_cell_iou(predicted, ground_truth)
    
    # Compare text
    pred_text = predicted.text or ""
    gt_text = ground_truth.text or ""
    
    metrics.text_match = (pred_text == gt_text)
    metrics.cer = compute_cer(pred_text, gt_text)
    metrics.wer = compute_wer(pred_text, gt_text)
    
    # Compare spans
    metrics.span_match = (
        predicted.row_span == ground_truth.row_span and
        predicted.col_span == ground_truth.col_span
    )
    
    return metrics


def compare_tables(predicted: TableGrid, ground_truth: TableGrid) -> TableMetrics:
    """Compare predicted table against ground truth.
    
    Args:
        predicted: Predicted table grid
        ground_truth: Ground truth table grid
        
    Returns:
        TableMetrics with comparison results
    """
    metrics = TableMetrics(table_id=predicted.table_id)
    
    # Compare grid shape
    metrics.n_rows_predicted = predicted.n_rows
    metrics.n_rows_ground_truth = ground_truth.n_rows
    metrics.n_cols_predicted = predicted.n_cols
    metrics.n_cols_ground_truth = ground_truth.n_cols
    
    metrics.grid_shape_match = (
        predicted.n_rows == ground_truth.n_rows and
        predicted.n_cols == ground_truth.n_cols
    )
    
    # Match cells by grid position
    # Build lookup dict for ground truth cells
    gt_cells_by_pos = {
        (cell.row_index, cell.col_index): cell
        for cell in ground_truth.cells
    }
    
    # Compare each predicted cell with corresponding ground truth cell
    for pred_cell in predicted.cells:
        pos = (pred_cell.row_index, pred_cell.col_index)
        gt_cell = gt_cells_by_pos.get(pos)
        
        if gt_cell:
            cell_metrics = compare_cells(pred_cell, gt_cell)
            metrics.cell_metrics.append(cell_metrics)
    
    # Compute aggregate metrics
    if metrics.cell_metrics:
        metrics.avg_cell_iou = sum(m.iou for m in metrics.cell_metrics) / len(metrics.cell_metrics)
        metrics.exact_match_rate = sum(m.text_match for m in metrics.cell_metrics) / len(metrics.cell_metrics)
        metrics.span_accuracy = sum(m.span_match for m in metrics.cell_metrics) / len(metrics.cell_metrics)
        
        # CER/WER only for cells with text
        cells_with_text = [m for m in metrics.cell_metrics if m.cer < 1.0 or m.wer < 1.0]
        if cells_with_text:
            metrics.avg_cer = sum(m.cer for m in cells_with_text) / len(cells_with_text)
            metrics.avg_wer = sum(m.wer for m in cells_with_text) / len(cells_with_text)
    
    return metrics


def aggregate_benchmark_results(table_metrics: List[TableMetrics], n_tables_ground_truth: int) -> BenchmarkResult:
    """Aggregate metrics across all tables in benchmark.
    
    Args:
        table_metrics: List of metrics for each table
        n_tables_ground_truth: Total number of tables in ground truth
        
    Returns:
        BenchmarkResult with aggregated metrics
    """
    result = BenchmarkResult(table_metrics=table_metrics)
    
    # Detection metrics
    result.tables_detected = len(table_metrics)
    result.tables_ground_truth = n_tables_ground_truth
    
    if result.tables_detected > 0:
        result.table_detection_precision = min(1.0, n_tables_ground_truth / result.tables_detected)
    
    if n_tables_ground_truth > 0:
        result.table_detection_recall = result.tables_detected / n_tables_ground_truth
    
    if result.table_detection_precision + result.table_detection_recall > 0:
        result.table_detection_f1 = (
            2 * result.table_detection_precision * result.table_detection_recall /
            (result.table_detection_precision + result.table_detection_recall)
        )
    
    # Aggregate structural metrics
    if table_metrics:
        result.avg_grid_shape_accuracy = sum(m.grid_shape_match for m in table_metrics) / len(table_metrics)
        result.avg_cell_iou = sum(m.avg_cell_iou for m in table_metrics) / len(table_metrics)
        result.avg_span_accuracy = sum(m.span_accuracy for m in table_metrics) / len(table_metrics)
        
        # Aggregate text metrics
        result.avg_cer = sum(m.avg_cer for m in table_metrics) / len(table_metrics)
        result.avg_wer = sum(m.avg_wer for m in table_metrics) / len(table_metrics)
        result.exact_match_rate = sum(m.exact_match_rate for m in table_metrics) / len(table_metrics)
    
    # Compute overall scores
    # Structural F1: combine IoU and span accuracy
    if result.avg_cell_iou + result.avg_span_accuracy > 0:
        result.structural_f1 = (
            2 * result.avg_cell_iou * result.avg_span_accuracy /
            (result.avg_cell_iou + result.avg_span_accuracy)
        )
    
    # Text F1: use (1 - CER) as proxy for accuracy
    text_accuracy = 1.0 - result.avg_cer
    if text_accuracy + result.exact_match_rate > 0:
        result.text_f1 = (
            2 * text_accuracy * result.exact_match_rate /
            (text_accuracy + result.exact_match_rate)
        )
    
    # Overall F1: combine structural and text F1
    if result.structural_f1 + result.text_f1 > 0:
        result.overall_f1 = (
            2 * result.structural_f1 * result.text_f1 /
            (result.structural_f1 + result.text_f1)
        )
    
    return result


def compute_confidence_interval(results: BenchmarkResult, confidence: float = 0.95) -> tuple[float, float]:
    """Compute confidence interval for overall F1 score.
    
    Uses bootstrap method to estimate confidence interval.
    
    Args:
        results: Benchmark results
        confidence: Confidence level (default: 0.95 for 95% CI)
        
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    import random
    
    if not results.table_metrics:
        return (0.0, 0.0)
    
    # Bootstrap resampling
    n_bootstrap = 1000
    bootstrap_f1_scores = []
    
    for _ in range(n_bootstrap):
        # Resample table metrics with replacement
        sample = random.choices(results.table_metrics, k=len(results.table_metrics))
        
        # Compute F1 for this sample
        sample_result = aggregate_benchmark_results(sample, results.tables_ground_truth)
        bootstrap_f1_scores.append(sample_result.overall_f1)
    
    # Compute percentiles for confidence interval
    bootstrap_f1_scores.sort()
    alpha = 1.0 - confidence
    lower_idx = int(alpha / 2 * n_bootstrap)
    upper_idx = int((1.0 - alpha / 2) * n_bootstrap)
    
    return (bootstrap_f1_scores[lower_idx], bootstrap_f1_scores[upper_idx])


