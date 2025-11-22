#!/usr/bin/env python3
"""
Quality gate checker for benchmark results.

This script checks benchmark results against defined thresholds and fails
if metrics regress beyond acceptable tolerance.

Usage:
    python tools/check_quality_gates.py \\
        --results benchmark_results/benchmark_results.json \\
        --thresholds .github/benchmark_thresholds.yaml
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


def check_quality_gates(results: dict, thresholds: dict) -> tuple[bool, list[str]]:
    """Check benchmark results against quality thresholds.
    
    Args:
        results: Benchmark results dict
        thresholds: Threshold configuration dict
        
    Returns:
        Tuple of (passed, failures) where passed is bool and failures is list of error messages
    """
    threshold_config = thresholds.get("thresholds", {})
    
    failures = []
    
    for metric_name, config in threshold_config.items():
        if metric_name not in results:
            print(f"⚠️  Warning: Metric '{metric_name}' not found in results")
            continue
        
        actual_value = results[metric_name]
        target = config["target"]
        tolerance = config["tolerance"]
        inverted = config.get("inverted", False)
        description = config.get("description", metric_name)
        
        # Compute min/max acceptable values
        if inverted:
            # For inverted metrics (lower is better), threshold is target + tolerance
            threshold = target + tolerance
            passed = actual_value <= threshold
            comparison = f"{actual_value:.2%} > {threshold:.2%}"
        else:
            # For normal metrics (higher is better), threshold is target - tolerance
            threshold = target - tolerance
            passed = actual_value >= threshold
            comparison = f"{actual_value:.2%} < {threshold:.2%}"
        
        # Check threshold
        if not passed:
            failures.append(
                f"❌ {metric_name}: {comparison} "
                f"(target: {target:.2%}, tolerance: ±{tolerance:.2%})"
            )
        else:
            print(f"✅ {metric_name}: {actual_value:.2%} (threshold: {threshold:.2%})")
    
    return len(failures) == 0, failures


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check benchmark results against quality gates"
    )
    parser.add_argument(
        "--results",
        type=Path,
        required=True,
        help="Path to benchmark results JSON file",
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        required=True,
        help="Path to thresholds YAML file",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any threshold violation (default: fail only on major regressions)",
    )
    
    args = parser.parse_args()
    
    # Load results
    if not args.results.exists():
        print(f"❌ Results file not found: {args.results}")
        sys.exit(1)
    
    with open(args.results) as f:
        results = json.load(f)
    
    # Load thresholds
    if not args.thresholds.exists():
        print(f"❌ Thresholds file not found: {args.thresholds}")
        sys.exit(1)
    
    with open(args.thresholds) as f:
        thresholds = yaml.safe_load(f)
    
    # Check quality gates
    print("\n" + "=" * 60)
    print("QUALITY GATE CHECK")
    print("=" * 60 + "\n")
    
    passed, failures = check_quality_gates(results, thresholds)
    
    if passed:
        print("\n" + "=" * 60)
        print("✅ ALL QUALITY GATES PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ QUALITY GATES FAILED")
        print("=" * 60)
        print("\nFailures:")
        for failure in failures:
            print(f"  {failure}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()


