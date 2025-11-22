#!/usr/bin/env python3
"""
Example: End-to-End Table Extraction with Gemini

This script demonstrates using the Gemini (or GPT-4o) end-to-end extraction strategy
instead of the traditional heuristic pipeline.

The LLM strategy bypasses region detection, grid construction, and OCR, instead
asking a vision LLM to directly extract tables from page images.

Usage:
    # Using Gemini (requires GOOGLE_API_KEY or --llm-api-key)
    python examples/gemini_extraction.py document.pdf --llm-provider google --llm-model gemini-1.5-flash
    
    # Using GPT-4o (requires OPENAI_API_KEY or --llm-api-key)
    python examples/gemini_extraction.py document.pdf --llm-provider openai --llm-model gpt-4o
    
    # With consistency checking (runs extraction 3 times and votes)
    python examples/gemini_extraction.py document.pdf --llm-consistency-attempts 3
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf_reader import PipelineConfig, PipelineRunner


def main():
    parser = argparse.ArgumentParser(
        description="Extract tables using Gemini/GPT-4o end-to-end strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "input_pdf",
        type=Path,
        help="Path to input PDF file",
    )
    parser.add_argument(
        "--llm-provider",
        type=str,
        default="google",
        choices=["google", "openai"],
        help="LLM provider (default: google)",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        help="LLM model name (default: gemini-1.5-flash for google, gpt-4o for openai)",
    )
    parser.add_argument(
        "--llm-api-key",
        type=str,
        help="LLM API key (or set GOOGLE_API_KEY / OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--llm-consistency-attempts",
        type=int,
        default=1,
        help="Number of extraction attempts for consensus (default: 1)",
    )
    parser.add_argument(
        "--llm-consistency-threshold",
        type=float,
        default=0.8,
        help="Required agreement ratio for consensus (default: 0.8)",
    )
    parser.add_argument(
        "--pages",
        type=str,
        help="Page indices to process (e.g., '0,2,4' or '0-5')",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Rendering DPI (default: 200)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug artifacts",
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not args.input_pdf.exists():
        print(f"Error: Input file not found: {args.input_pdf}", file=sys.stderr)
        sys.exit(1)
    
    # Get API key from args or environment
    api_key = args.llm_api_key
    if not api_key:
        if args.llm_provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
        else:
            api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print(
            f"Error: API key required. Set {args.llm_provider.upper()}_API_KEY env var "
            f"or use --llm-api-key",
            file=sys.stderr,
        )
        sys.exit(1)
    
    # Set default model if not specified
    if not args.llm_model:
        if args.llm_provider == "google":
            args.llm_model = "gemini-1.5-flash"
        else:
            args.llm_model = "gpt-4o"
    
    # Parse page indices if provided
    page_indices = None
    if args.pages:
        page_indices = []
        for part in args.pages.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                page_indices.extend(range(start, end + 1))
            else:
                page_indices.append(int(part))
    
    # Create configuration
    config = PipelineConfig(
        input_path=args.input_pdf,
        page_indices=page_indices,
        dpi=args.dpi,
        extraction_strategy="llm_end_to_end",
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_api_key=api_key,
        llm_consistency_attempts=args.llm_consistency_attempts,
        llm_consistency_threshold=args.llm_consistency_threshold,
        log_level="INFO",
        enable_debug_artifacts=args.debug,
    )
    
    print(f"Extracting tables from: {args.input_pdf}")
    print(f"Strategy: LLM End-to-End ({args.llm_provider} / {args.llm_model})")
    print(f"Consistency attempts: {args.llm_consistency_attempts}")
    if args.llm_consistency_attempts > 1:
        print(f"Consistency threshold: {args.llm_consistency_threshold}")
    print()
    
    # Run extraction
    runner = PipelineRunner()
    result = runner.extract_tables(str(args.input_pdf), config=config)
    
    # Print results
    print("=" * 60)
    print("EXTRACTION RESULTS")
    print("=" * 60)
    print(f"Pages processed: {result.run_stats.pages_processed}")
    print(f"Tables detected: {result.run_stats.tables_detected}")
    print(f"Tables extracted: {result.run_stats.tables_extracted}")
    print(f"Tables failed: {result.run_stats.tables_failed}")
    print(f"Total duration: {result.run_stats.total_duration_ms / 1000:.2f}s")
    print()
    
    if result.run_stats.errors:
        print("ERRORS:")
        for error in result.run_stats.errors:
            print(f"  - {error}")
        print()
    
    # Print table summaries
    for i, (table, metadata) in enumerate(zip(result.tables, result.metadata)):
        print(f"Table {i+1}: {metadata.table_id}")
        print(f"  Page: {metadata.page_index}")
        print(f"  Shape: {metadata.grid_shape[0]} rows × {metadata.grid_shape[1]} cols")
        print(f"  Status: {metadata.status}")
        if "llm_extracted" in metadata.irregularities:
            print(f"  Source: LLM End-to-End Extraction")
        print()
        
        # Print first few rows as preview
        print("  Preview (first 3 rows):")
        for row_idx, row in enumerate(table.rows[:3]):
            print(f"    Row {row_idx}: {row}")
        if len(table.rows) > 3:
            print(f"    ... ({len(table.rows) - 3} more rows)")
        print()
    
    if args.debug:
        print(f"Debug artifacts saved to: {config.debug_output_dir}/")
    
    print("Extraction complete!")


if __name__ == "__main__":
    main()


