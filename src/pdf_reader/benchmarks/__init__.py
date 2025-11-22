"""
Benchmarking suite for PDF table extraction.

This module provides tools for evaluating extraction accuracy against ground truth
annotations, computing metrics, and tracking performance over time.

Key components:
- metrics: Evaluation metrics (IoU, CER, WER, etc.)
- runner: Benchmark execution harness
- annotations: Ground truth annotation format and utilities

Usage:
    from pdf_reader.benchmarks import run_benchmark, compute_metrics
    
    # Run benchmark
    results = run_benchmark(
        dataset_dir="datasets/benchmarks",
        config=PipelineConfig(),
    )
    
    # View metrics
    print(f"Overall accuracy: {results.overall_f1:.2%}")
"""

from .metrics import (
    BenchmarkResult,
    CellMetrics,
    TableMetrics,
    compute_cell_iou,
    compute_cer,
    compute_wer,
)

__all__ = [
    "BenchmarkResult",
    "CellMetrics",
    "TableMetrics",
    "compute_cell_iou",
    "compute_cer",
    "compute_wer",
]


