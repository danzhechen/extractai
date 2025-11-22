#!/usr/bin/env python3
"""Tool to compare two run manifests and identify differences.

This tool helps track changes between pipeline runs for reproducibility analysis.

Usage:
    python tools/compare_manifests.py manifest1.json manifest2.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf_reader.manifest import load_manifest, compare_manifests


def print_differences(differences: dict) -> None:
    """Print manifest differences in a human-readable format."""
    if not differences:
        print("✅ Manifests are identical (excluding run_id and timestamp)")
        return
    
    print("⚠️  Differences found:\n")
    
    # Git differences
    if "git_commit" in differences:
        print("Git Commit:")
        print(f"  Manifest 1: {differences['git_commit']['manifest1']}")
        print(f"  Manifest 2: {differences['git_commit']['manifest2']}")
        print()
    
    # Config differences
    if "config_digest" in differences:
        print("Configuration Digest:")
        print(f"  Manifest 1: {differences['config_digest']['manifest1']}")
        print(f"  Manifest 2: {differences['config_digest']['manifest2']}")
        print("  ⚠️  Configuration has changed between runs")
        print()
    
    # Package version differences
    if "package_versions" in differences:
        print("Package Versions:")
        for pkg, versions in differences["package_versions"].items():
            print(f"  {pkg}:")
            print(f"    Manifest 1: {versions['manifest1']}")
            print(f"    Manifest 2: {versions['manifest2']}")
        print()
    
    # Component version differences
    if "components" in differences:
        print("Component Versions:")
        for comp, versions in differences["components"].items():
            print(f"  {comp}:")
            print(f"    Manifest 1: {versions['manifest1']}")
            print(f"    Manifest 2: {versions['manifest2']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Compare two run manifests for reproducibility analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two manifests
  python tools/compare_manifests.py run1/manifest.json run2/manifest.json
  
  # Compare with detailed output
  python tools/compare_manifests.py manifest1.json manifest2.json --verbose
        """,
    )
    
    parser.add_argument(
        "manifest1",
        type=Path,
        help="Path to first manifest file",
    )
    parser.add_argument(
        "manifest2",
        type=Path,
        help="Path to second manifest file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed manifest information",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output differences as JSON",
    )
    
    args = parser.parse_args()
    
    # Validate input files
    if not args.manifest1.exists():
        print(f"Error: Manifest file not found: {args.manifest1}", file=sys.stderr)
        return 1
    
    if not args.manifest2.exists():
        print(f"Error: Manifest file not found: {args.manifest2}", file=sys.stderr)
        return 1
    
    # Load manifests
    try:
        manifest1 = load_manifest(args.manifest1)
        manifest2 = load_manifest(args.manifest2)
    except Exception as e:
        print(f"Error loading manifests: {e}", file=sys.stderr)
        return 1
    
    # Show manifest info if verbose
    if args.verbose:
        print("=" * 60)
        print("Manifest 1:")
        print(f"  Run ID: {manifest1.run_id}")
        print(f"  Timestamp: {manifest1.timestamp}")
        print(f"  Git Commit: {manifest1.git_commit}")
        print(f"  Git Branch: {manifest1.git_branch}")
        print(f"  Git Dirty: {manifest1.git_dirty}")
        print(f"  Config Digest: {manifest1.config_digest}")
        print()
        
        print("Manifest 2:")
        print(f"  Run ID: {manifest2.run_id}")
        print(f"  Timestamp: {manifest2.timestamp}")
        print(f"  Git Commit: {manifest2.git_commit}")
        print(f"  Git Branch: {manifest2.git_branch}")
        print(f"  Git Dirty: {manifest2.git_dirty}")
        print(f"  Config Digest: {manifest2.config_digest}")
        print()
        print("=" * 60)
        print()
    
    # Compare manifests
    differences = compare_manifests(manifest1, manifest2)
    
    # Output results
    if args.json:
        print(json.dumps(differences, indent=2))
    else:
        print_differences(differences)
    
    # Exit with code 1 if differences found
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())


