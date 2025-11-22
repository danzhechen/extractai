# Benchmarking Guide

This guide explains how to use the benchmark suite to evaluate PDF table extraction accuracy, track performance over time, and ensure quality standards.

## Overview

The benchmark suite provides:

- **Curated Dataset**: 15+ tables across 5+ PDFs with diverse characteristics
- **Ground Truth Annotations**: Manually verified table structures and content
- **Comprehensive Metrics**: Structural accuracy, text accuracy, detection performance
- **Quality Gates**: Automated CI checks to prevent regressions
- **Trend Tracking**: Historical performance analysis

## Quick Start

```bash
# Run smoke tests (3-5 tables, fast)
python tools/run_benchmarks.py --dataset datasets/benchmarks --subset smoke

# Run full benchmark suite
python tools/run_benchmarks.py --dataset datasets/benchmarks

# Compare against baseline
python tools/run_benchmarks.py --dataset datasets/benchmarks \\
    --baseline runs/baseline/benchmark_results.json
```

## Dataset Structure

```
datasets/benchmarks/
├── README.md              # Dataset documentation
├── pdfs/                  # PDF files
│   ├── simple_table.pdf
│   ├── merged_cells.pdf
│   └── ...
├── annotations/           # Ground truth annotations
│   ├── simple_table.json
│   ├── merged_cells.json
│   └── ...
└── LICENSE.md            # Dataset license information
```

See [datasets/benchmarks/README.md](../../datasets/benchmarks/README.md) for full dataset documentation.

---

## Metrics Explained

### Overall Metrics

- **Overall F1**: Harmonic mean of structural and text F1 scores (primary metric)
- **Structural F1**: Accuracy of table structure detection
- **Text F1**: Accuracy of text extraction

### Detection Metrics

- **Precision**: Percentage of detected tables that are correct
- **Recall**: Percentage of ground truth tables that are detected
- **F1**: Harmonic mean of precision and recall

### Structural Metrics

- **Grid Shape Accuracy**: Percentage of tables with correct row/column counts
- **Cell IoU**: Average Intersection over Union for cell bounding boxes (0-1, higher is better)
- **Span Accuracy**: Percentage of cells with correct rowspan/colspan

### Text Metrics

- **Character Error Rate (CER)**: Edit distance normalized by text length (0-1, lower is better)
- **Word Error Rate (WER)**: Word-level edit distance (0-1, lower is better)
- **Exact Match Rate**: Percentage of cells with perfect text match

---

## Running Benchmarks

### Basic Usage

```bash
# Run all benchmarks
python tools/run_benchmarks.py --dataset datasets/benchmarks

# Run specific subset
python tools/run_benchmarks.py --dataset datasets/benchmarks --subset smoke

# Use custom pipeline config
python tools/run_benchmarks.py --dataset datasets/benchmarks \\
    --config configs/high_quality.yaml

# Save results to custom directory
python tools/run_benchmarks.py --dataset datasets/benchmarks \\
    --output benchmark_results/$(date +%Y%m%d)
```

### Comparing Against Baseline

```bash
# First run: establish baseline
python tools/run_benchmarks.py --dataset datasets/benchmarks \\
    --output runs/baseline

# Later run: compare against baseline
python tools/run_benchmarks.py --dataset datasets/benchmarks \\
    --baseline runs/baseline/benchmark_results.json
```

The tool will exit with error code 1 if metrics regress by more than 5%.

### Parallel Processing

```bash
# Enable parallel processing (faster on multi-core systems)
python tools/run_benchmarks.py --dataset datasets/benchmarks --parallel
```

---

## Understanding Results

### Output Files

After running benchmarks, the output directory contains:

```
benchmark_results/
├── benchmark_results.json      # Detailed metrics in JSON format
├── benchmark_summary.md        # Human-readable summary
├── benchmark_report.html       # Interactive HTML report
└── manifest.json               # Run manifest for reproducibility
```

### Interpreting Metrics

**Good Performance**:
- Overall F1 ≥ 87%
- Structural F1 ≥ 90%
- Text F1 ≥ 85%
- Cell IoU ≥ 0.85

**Needs Improvement**:
- Overall F1 < 80%
- Detection recall < 90%
- CER > 20%

**Example Output**:

```
=============================================================
BENCHMARK RESULTS
=============================================================
Overall F1: 92.5%
Structural F1: 94.2%
Text F1: 90.8%
Tables Detected: 15 / 15
=============================================================
```

---

## Quality Gates

Quality gates ensure that code changes don't degrade extraction accuracy.

### Thresholds

Defined in `.github/benchmark_thresholds.yaml`:

| Metric | Target | Tolerance | Minimum |
|--------|--------|-----------|---------|
| Overall F1 | 87% | ±5% | 82% |
| Structural F1 | 90% | ±5% | 85% |
| Text F1 | 85% | ±5% | 80% |
| Detection Recall | 95% | ±5% | 90% |

### Checking Quality Gates

```bash
# Check results against thresholds
python tools/check_quality_gates.py \\
    --results benchmark_results/benchmark_results.json \\
    --thresholds .github/benchmark_thresholds.yaml
```

Exit codes:
- `0`: All quality gates passed
- `1`: One or more gates failed

### CI Integration

Benchmarks run automatically:
- **Pull Requests**: Smoke tests only
- **Weekly Schedule**: Full benchmark suite (Sundays at 2 AM)
- **Manual Trigger**: Via GitHub Actions UI

---

## Adding New Test Cases

### 1. Prepare PDF

Choose a PDF that:
- Has clear redistribution rights (synthetic, public domain, or CC0)
- Represents a specific challenge or table type
- Is not already covered by existing test cases

```bash
# Save to datasets directory
cp your_test.pdf datasets/benchmarks/pdfs/
```

### 2. Create Annotation

#### Option A: Manual Annotation

Create `datasets/benchmarks/annotations/your_test.json`:

```json
{
  "pdf_file": "your_test.pdf",
  "page_index": 0,
  "metadata": {
    "source": "Synthetic",
    "annotator": "Your Name",
    "date": "2025-11-21"
  },
  "tables": [
    {
      "table_id": "table_0",
      "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.9, "y1": 0.8},
      "n_rows": 3,
      "n_cols": 2,
      "cells": [
        {
          "row": 0,
          "col": 0,
          "rowspan": 1,
          "colspan": 1,
          "text": "Header 1",
          "bbox": {"x0": 0.1, "y0": 0.2, "x1": 0.5, "y1": 0.3}
        }
      ]
    }
  ]
}
```

#### Option B: Annotation Tool (Future)

```bash
python tools/annotate_table.py --input datasets/benchmarks/pdfs/your_test.pdf
```

### 3. Validate Annotation

```bash
python tools/validate_annotation.py datasets/benchmarks/annotations/your_test.json
```

### 4. Test Extraction

```bash
python tools/run_benchmarks.py --dataset datasets/benchmarks --subset your_test
```

### 5. Submit Pull Request

- Include both PDF and annotation
- Update `datasets/benchmarks/README.md` with test case description
- Add license information to `datasets/benchmarks/LICENSE.md`

---

## Troubleshooting

### Flaky Results

**Problem**: Metrics vary between runs.

**Causes**:
- Non-deterministic processing (parallel workers, LLM calls)
- Minor version changes in dependencies

**Solutions**:
- Use `--config` to fix all random seeds
- Run benchmarks multiple times and average results
- Check for dependency updates in CI logs

### Performance Issues

**Problem**: Benchmarks take too long.

**Solutions**:
- Use `--subset smoke` for fast validation
- Enable `--parallel` for multi-core systems
- Reduce DPI in pipeline config
- Disable debug artifacts

### Metric Discrepancies

**Problem**: Metric doesn't match expectations.

**Debugging**:
1. Check annotation validity: `python tools/validate_annotation.py`
2. Inspect extraction results vs. ground truth
3. Review metric calculation logic in `src/pdf_reader/benchmarks/metrics.py`
4. Enable debug artifacts to visualize detection/extraction

---

## Best Practices

### When to Run Benchmarks

- **Before major releases**: Full suite
- **After significant changes**: Full suite
- **During development**: Smoke tests
- **Pull requests**: Smoke tests (automatic)
- **Weekly**: Full suite (automatic)

### Maintaining Quality

1. **Set Realistic Targets**: Based on actual performance, not aspirational goals
2. **Update Baselines**: After intentional changes that affect metrics
3. **Monitor Trends**: Track metrics over time, not just absolute values
4. **Investigate Regressions**: Don't just bump thresholds

### Contributing

When adding new benchmark cases:
1. Ensure high annotation quality (peer review)
2. Add diverse cases (don't duplicate existing coverage)
3. Document special cases or edge conditions
4. Test that pipeline can process without errors

---

## Advanced Topics

### Custom Metrics

To add new metrics:

1. Implement metric function in `src/pdf_reader/benchmarks/metrics.py`
2. Add to `BenchmarkResult` dataclass
3. Compute in `aggregate_benchmark_results()`
4. Add threshold to `.github/benchmark_thresholds.yaml`

Example:

```python
def compute_custom_metric(predicted: TableGrid, ground_truth: TableGrid) -> float:
    # Your metric logic here
    return score

# Add to BenchmarkResult
@dataclass
class BenchmarkResult:
    # ...
    custom_metric: float = 0.0
```

### Benchmark Subsets

Define custom subsets in `.github/benchmark_thresholds.yaml`:

```yaml
subsets:
  my_subset:
    description: "My custom subset"
    pdfs: ["file1.pdf", "file2.pdf"]
    timeout: 60
```

Use with:

```bash
python tools/run_benchmarks.py --subset my_subset
```

### Trend Analysis

Track metrics over time:

```bash
# Save results with timestamp
python tools/run_benchmarks.py --output runs/benchmarks/$(date +%Y%m%d)

# Generate trend chart (future)
python tools/generate_trends.py --results runs/benchmarks/
```

---

## FAQ

**Q: Why did my PR fail benchmarks?**

A: Check the benchmark results in the PR comment. If metrics regressed by >5%, you may need to optimize your changes or update baselines if the change was intentional.

**Q: How accurate are the benchmarks?**

A: Benchmark accuracy depends on annotation quality. All annotations are manually verified, but some edge cases may have ambiguous ground truth.

**Q: Can I run benchmarks locally before pushing?**

A: Yes! Run `python tools/run_benchmarks.py --subset smoke` before pushing to catch regressions early.

**Q: How long do benchmarks take?**

A: Smoke tests: <30s, Full suite: 2-5 minutes (depends on hardware and config).

**Q: What if I disagree with an annotation?**

A: Open an issue with your reasoning. Annotations can be updated if errors are found.

---

**Last Updated**: 2025-11-21

**Related Documentation**:
- [Dataset README](../../datasets/benchmarks/README.md)
- [Metrics Reference](../api-reference.md#benchmarks)
- [CI/CD Guide](../guides/ci-cd.md)


