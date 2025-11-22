#!/usr/bin/env python3
"""
Benchmark runner for PDF table extraction.

This script runs the extraction pipeline on a benchmark dataset and compares
results against ground truth annotations.

Usage:
    python tools/run_benchmarks.py --dataset datasets/benchmarks
    python tools/run_benchmarks.py --dataset datasets/benchmarks --subset smoke
    python tools/run_benchmarks.py --dataset datasets/benchmarks --baseline runs/baseline/results.json
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf_reader.benchmarks.annotations import annotation_to_table_grid, load_annotation
from pdf_reader.benchmarks.metrics import (
    BenchmarkResult,
    aggregate_benchmark_results,
    compare_tables,
    compute_confidence_interval,
)
from pdf_reader.manifest import create_run_manifest
from pdf_reader.models import TableGrid
from pdf_reader.pipeline import PipelineConfig, PipelineRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_benchmark_dataset(dataset_dir: Path, subset: Optional[str] = None) -> List[tuple[Path, Path]]:
    """Load benchmark dataset PDF and annotation pairs.
    
    Args:
        dataset_dir: Path to benchmark dataset directory
        subset: Optional subset name ('smoke' or 'full')
        
    Returns:
        List of (pdf_path, annotation_path) tuples
        
    Raises:
        FileNotFoundError: If dataset directory doesn't exist
    """
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    
    pdfs_dir = dataset_dir / "pdfs"
    annotations_dir = dataset_dir / "annotations"
    
    if not pdfs_dir.exists() or not annotations_dir.exists():
        raise FileNotFoundError(
            f"Dataset must have 'pdfs/' and 'annotations/' subdirectories"
        )
    
    # Find all annotations
    annotation_files = sorted(annotations_dir.glob("*.json"))
    
    # Filter by subset if specified
    if subset == "smoke":
        # Take first 3-5 files for quick testing
        annotation_files = annotation_files[:5]
        logger.info(f"Running smoke subset: {len(annotation_files)} files")
    elif subset:
        # Filter by specific file pattern
        annotation_files = [f for f in annotation_files if subset in f.stem]
        logger.info(f"Running subset '{subset}': {len(annotation_files)} files")
    
    # Build PDF-annotation pairs
    pairs = []
    for annotation_file in annotation_files:
        # Find corresponding PDF
        pdf_file = pdfs_dir / f"{annotation_file.stem}.pdf"
        if not pdf_file.exists():
            logger.warning(f"PDF not found for annotation: {annotation_file}")
            continue
        
        pairs.append((pdf_file, annotation_file))
    
    if not pairs:
        raise ValueError(f"No valid PDF-annotation pairs found in {dataset_dir}")
    
    logger.info(f"Loaded {len(pairs)} PDF-annotation pairs")
    return pairs


def run_extraction_on_pdf(pdf_path: Path, config: PipelineConfig) -> List[TableGrid]:
    """Run extraction pipeline on a single PDF.
    
    Args:
        pdf_path: Path to PDF file
        config: Pipeline configuration
        
    Returns:
        List of extracted TableGrid objects
    """
    runner = PipelineRunner()
    result = runner.extract_tables(pdf_input=str(pdf_path), config=config)
    
    # Convert TableDataFrameSpec back to TableGrid for comparison
    # (TableGrid is what we compare against ground truth)
    extracted_tables = []
    
    for table_spec in result.tables:
        # Find corresponding TableGrid in result metadata
        # For now, we'll use the detection/extraction path to get grids
        # This is a simplification; in practice we'd track grids through pipeline
        logger.warning("TableGrid reconstruction from TableDataFrameSpec not fully implemented")
    
    return extracted_tables


def compare_extracted_vs_ground_truth(
    extracted_tables: List[TableGrid],
    ground_truth_tables: List[TableGrid],
) -> List:
    """Compare extracted tables against ground truth.
    
    Args:
        extracted_tables: Tables extracted by pipeline
        ground_truth_tables: Ground truth table annotations
        
    Returns:
        List of TableMetrics for each matched table
    """
    from pdf_reader.benchmarks.metrics import compare_tables
    
    table_metrics = []
    
    # Match tables by table_id (assuming same naming convention)
    gt_by_id = {t.table_id: t for t in ground_truth_tables}
    
    for extracted in extracted_tables:
        gt_table = gt_by_id.get(extracted.table_id)
        if gt_table:
            metrics = compare_tables(extracted, gt_table)
            table_metrics.append(metrics)
        else:
            logger.warning(f"No ground truth found for table: {extracted.table_id}")
    
    return table_metrics


def generate_report(result: BenchmarkResult, output_dir: Path) -> None:
    """Generate benchmark report files.
    
    Args:
        result: Benchmark results
        output_dir: Directory to save reports
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. JSON results
    json_path = output_dir / "benchmark_results.json"
    with open(json_path, "w") as f:
        json.dump(
            {
                "tables_detected": result.tables_detected,
                "tables_ground_truth": result.tables_ground_truth,
                "detection_precision": result.table_detection_precision,
                "detection_recall": result.table_detection_recall,
                "detection_f1": result.table_detection_f1,
                "avg_grid_shape_accuracy": result.avg_grid_shape_accuracy,
                "avg_cell_iou": result.avg_cell_iou,
                "avg_span_accuracy": result.avg_span_accuracy,
                "avg_cer": result.avg_cer,
                "avg_wer": result.avg_wer,
                "exact_match_rate": result.exact_match_rate,
                "structural_f1": result.structural_f1,
                "text_f1": result.text_f1,
                "overall_f1": result.overall_f1,
                "ci_lower": result.ci_lower,
                "ci_upper": result.ci_upper,
            },
            f,
            indent=2,
        )
    logger.info(f"Saved JSON results to {json_path}")
    
    # 2. Markdown summary
    md_path = output_dir / "benchmark_summary.md"
    with open(md_path, "w") as f:
        f.write("# Benchmark Results\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Overall Metrics\n\n")
        f.write(f"- **Overall F1**: {result.overall_f1:.2%}\n")
        f.write(f"- **Structural F1**: {result.structural_f1:.2%}\n")
        f.write(f"- **Text F1**: {result.text_f1:.2%}\n\n")
        
        f.write("## Detection Metrics\n\n")
        f.write(f"- **Tables Detected**: {result.tables_detected} / {result.tables_ground_truth}\n")
        f.write(f"- **Precision**: {result.table_detection_precision:.2%}\n")
        f.write(f"- **Recall**: {result.table_detection_recall:.2%}\n")
        f.write(f"- **F1**: {result.table_detection_f1:.2%}\n\n")
        
        f.write("## Structural Metrics\n\n")
        f.write(f"- **Grid Shape Accuracy**: {result.avg_grid_shape_accuracy:.2%}\n")
        f.write(f"- **Cell IoU**: {result.avg_cell_iou:.2%}\n")
        f.write(f"- **Span Accuracy**: {result.avg_span_accuracy:.2%}\n\n")
        
        f.write("## Text Metrics\n\n")
        f.write(f"- **Character Error Rate**: {result.avg_cer:.2%}\n")
        f.write(f"- **Word Error Rate**: {result.avg_wer:.2%}\n")
        f.write(f"- **Exact Match Rate**: {result.exact_match_rate:.2%}\n\n")
        
        if result.ci_lower and result.ci_upper:
            f.write("## Confidence Interval\n\n")
            f.write(f"- **95% CI**: [{result.ci_lower:.2%}, {result.ci_upper:.2%}]\n\n")
    
    logger.info(f"Saved Markdown summary to {md_path}")
    
    # 3. HTML report (simplified)
    html_path = output_dir / "benchmark_report.html"
    with open(html_path, "w") as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .metric { margin: 20px 0; }
        .metric-name { font-weight: bold; }
        .metric-value { font-size: 24px; color: #0066cc; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Benchmark Results</h1>
""")
        f.write(f"<p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        f.write(f'<div class="metric"><span class="metric-name">Overall F1:</span> ')
        f.write(f'<span class="metric-value">{result.overall_f1:.2%}</span></div>')
        
        f.write("<h2>Summary</h2><table>")
        f.write("<tr><th>Metric</th><th>Value</th></tr>")
        f.write(f"<tr><td>Structural F1</td><td>{result.structural_f1:.2%}</td></tr>")
        f.write(f"<tr><td>Text F1</td><td>{result.text_f1:.2%}</td></tr>")
        f.write(f"<tr><td>Tables Detected</td><td>{result.tables_detected} / {result.tables_ground_truth}</td></tr>")
        f.write(f"<tr><td>Grid Shape Accuracy</td><td>{result.avg_grid_shape_accuracy:.2%}</td></tr>")
        f.write(f"<tr><td>Cell IoU</td><td>{result.avg_cell_iou:.2%}</td></tr>")
        f.write(f"<tr><td>Exact Match Rate</td><td>{result.exact_match_rate:.2%}</td></tr>")
        f.write("</table>")
        
        f.write("</body></html>")
    
    logger.info(f"Saved HTML report to {html_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run benchmark suite for PDF table extraction"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets/benchmarks"),
        help="Path to benchmark dataset directory",
    )
    parser.add_argument(
        "--subset",
        type=str,
        help="Subset to run (smoke/full/filename pattern)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to pipeline config file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/benchmarks") / datetime.now().strftime("%Y%m%d_%H%M%S"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Path to baseline results JSON for comparison",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing",
    )
    
    args = parser.parse_args()
    
    # Load dataset
    logger.info(f"Loading benchmark dataset from {args.dataset}")
    pairs = load_benchmark_dataset(args.dataset, subset=args.subset)
    
    # Load pipeline config
    if args.config:
        import yaml
        with open(args.config) as f:
            config_dict = yaml.safe_load(f)
        config = PipelineConfig(**config_dict)
    else:
        config = PipelineConfig(
            dpi=200,
            enable_debug_artifacts=False,
        )
    
    # Run benchmarks
    all_table_metrics = []
    total_ground_truth_tables = 0
    
    for pdf_path, annotation_path in pairs:
        logger.info(f"Processing {pdf_path.name}...")
        
        # Load ground truth
        annotation = load_annotation(annotation_path)
        ground_truth_tables = [
            annotation_to_table_grid(table)
            for table in annotation.tables
        ]
        total_ground_truth_tables += len(ground_truth_tables)
        
        # Run extraction
        try:
            extracted_tables = run_extraction_on_pdf(pdf_path, config)
            
            # Compare
            table_metrics = compare_extracted_vs_ground_truth(
                extracted_tables,
                ground_truth_tables,
            )
            
            all_table_metrics.extend(table_metrics)
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}", exc_info=True)
            continue
    
    # Aggregate results
    logger.info("Aggregating results...")
    result = aggregate_benchmark_results(all_table_metrics, total_ground_truth_tables)
    
    # Compute confidence interval
    result.ci_lower, result.ci_upper = compute_confidence_interval(result)
    
    # Generate reports
    logger.info(f"Generating reports in {args.output}")
    generate_report(result, args.output)
    
    # Print summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Overall F1: {result.overall_f1:.2%}")
    print(f"Structural F1: {result.structural_f1:.2%}")
    print(f"Text F1: {result.text_f1:.2%}")
    print(f"Tables Detected: {result.tables_detected} / {result.tables_ground_truth}")
    print("=" * 60)
    
    # Compare against baseline if provided
    if args.baseline:
        logger.info(f"Comparing against baseline: {args.baseline}")
        with open(args.baseline) as f:
            baseline = json.load(f)
        
        delta = result.overall_f1 - baseline["overall_f1"]
        print(f"\nBaseline comparison:")
        print(f"  Overall F1 delta: {delta:+.2%}")
        
        if delta < -0.05:
            print("  ⚠️  WARNING: Significant regression detected!")
            sys.exit(1)
    
    logger.info("Benchmark complete!")


if __name__ == "__main__":
    main()


