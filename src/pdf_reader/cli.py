"""Command-line interface for PDF table extraction pipeline."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path
from typing import Optional, Sequence

from .config_loader import create_config
from .pipeline import PipelineRunner

# Global cancellation event for signal handling
_cancel_event: Optional[threading.Event] = None


def parse_page_indices(page_str: str) -> list[int]:
    """Parse page indices from a string.

    Supports:
    - Comma-separated: "0,2,4"
    - Range: "0-5"
    - Mixed: "0,2-5,10"

    Args:
        page_str: String representation of page indices.

    Returns:
        List of page indices.

    Raises:
        ValueError: If the format is invalid.
    """
    indices = []
    for part in page_str.split(","):
        part = part.strip()
        if "-" in part:
            # Range format: "0-5"
            try:
                start, end = part.split("-", 1)
                start_idx = int(start.strip())
                end_idx = int(end.strip())
                if start_idx > end_idx:
                    raise ValueError(f"Invalid range: {start_idx} > {end_idx}")
                indices.extend(range(start_idx, end_idx + 1))
            except ValueError as e:
                raise ValueError(f"Invalid page range format '{part}': {e}")
        else:
            # Single index
            try:
                indices.append(int(part))
            except ValueError:
                raise ValueError(f"Invalid page index '{part}': must be an integer")

    return indices


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Optional list of arguments (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Extract tables from PDF files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract tables using FREE Gemini 2.5 Pro (default)
  pdf-reader extract --input document.pdf

  # Use premium Gemini 3.0 Pro for best quality (PAID)
  pdf-reader extract --input document.pdf --preset premium

  # Offline mode (heuristics only, no API calls)
  pdf-reader extract --input document.pdf --preset offline

  # Extract from specific pages
  pdf-reader extract --input document.pdf --pages 0,2,4

  # Extract with custom DPI and debug artifacts
  pdf-reader extract --input document.pdf --dpi 300 --debug

  # Use a config file
  pdf-reader extract --input document.pdf --config config/my_config.yaml
        """,
    )

    # Required arguments
    parser.add_argument(
        "command",
        choices=["extract"],
        help="Command to execute (currently only 'extract' is supported)",
    )

    # Input/output
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Path to input PDF file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory for results (optional)",
    )

    # Page selection
    parser.add_argument(
        "-p",
        "--pages",
        type=str,
        help="Page indices to process (comma-separated or range, e.g., '0,2,4' or '0-5')",
    )

    # Processing options
    parser.add_argument(
        "--preset",
        type=str,
        choices=["smart", "premium", "offline"],
        help="Quick configuration preset:\n"
             "  'smart' (default): FREE Gemini 2.5 Pro, conservative escalation to 3.0\n"
             "  'premium': PAID Gemini 3.0 Pro always, best quality\n"
             "  'offline': Heuristics only, no API calls",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        help="Rendering DPI (default: 200)",
    )
    parser.add_argument(
        "--extraction-strategy",
        type=str,
        choices=["heuristic", "llm_end_to_end"],
        help="Extraction strategy: 'heuristic' or 'llm_end_to_end' (default: llm_end_to_end with FREE Gemini 2.5 Pro)",
    )
    parser.add_argument(
        "--default-rows",
        type=int,
        help="Default number of rows for grid detection (default: 2)",
    )
    parser.add_argument(
        "--default-cols",
        type=int,
        help="Default number of columns for grid detection (default: 3)",
    )

    # LLM fallback options
    parser.add_argument(
        "--ocr-confidence-threshold",
        type=float,
        help="OCR confidence threshold for LLM fallback (0.0-1.0, default: 0.5)",
    )
    parser.add_argument(
        "--llm-fallback-enabled",
        action="store_true",
        help="Enable LLM fallback for low-confidence cells",
    )
    parser.add_argument(
        "--llm-provider",
        type=str,
        help="LLM provider (e.g., 'openai')",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        help="LLM model name (e.g., 'gpt-4o')",
    )
    parser.add_argument(
        "--llm-api-key",
        type=str,
        help="LLM API key (can also be set via PDF_READER_LLM_API_KEY env var)",
    )
    parser.add_argument(
        "--llm-consistency-attempts",
        type=int,
        help="Number of LLM extraction attempts for consensus (1-5, default: 1)",
    )
    parser.add_argument(
        "--llm-consistency-threshold",
        type=float,
        help="Required agreement ratio for consensus (0.0-1.0, default: 0.8)",
    )
    parser.add_argument(
        "--llm-model-escalation",
        type=str,
        help="Fallback LLM model for failed extractions (e.g., 'gemini-3.0-pro')",
    )
    parser.add_argument(
        "--enable-auto-escalation",
        action="store_true",
        help="Auto-escalate to premium model on failures (may incur costs)",
    )

    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (optional)",
    )
    parser.add_argument(
        "--log-format",
        choices=["json", "human"],
        help="Log format (default: human)",
    )

    # Debug artifacts
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug artifacts (overlay images and HTML report)",
    )
    parser.add_argument(
        "--debug-output-dir",
        type=str,
        help="Directory for debug artifacts (default: debug_output)",
    )
    parser.add_argument(
        "--no-overlays",
        action="store_true",
        help="Disable overlay image generation (when --debug is enabled)",
    )
    parser.add_argument(
        "--no-html-report",
        action="store_true",
        help="Disable HTML report generation (when --debug is enabled)",
    )
    parser.add_argument(
        "--emit-manifest",
        action="store_true",
        help="Save run manifest to JSON file for reproducibility tracking",
    )
    parser.add_argument(
        "--manifest-output",
        type=str,
        help="Path for manifest output (default: debug_output_dir/run_manifest.json)",
    )

    # Concurrency options
    parser.add_argument(
        "--worker-type",
        choices=["sequential", "thread"],
        help="Concurrency strategy: 'sequential' (one page at a time) or 'thread' (parallel processing). Default: thread",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Maximum number of worker threads for parallel processing (default: auto-detect based on CPU count)",
    )
    parser.add_argument(
        "--page-batch-size",
        type=int,
        help="Number of pages to queue before applying back-pressure (default: 4)",
    )
    parser.add_argument(
        "--max-inflight-pages",
        type=int,
        help="Hard limit on concurrently queued pages (default: same as page-batch-size)",
    )
    parser.add_argument(
        "--run-timeout",
        type=float,
        help="Timeout in seconds for the entire run (optional)",
    )
    parser.add_argument(
        "--enable-irregular-detection",
        action="store_true",
        help="Enable heuristics for irregular (ragged/partially bordered) tables",
    )
    parser.add_argument(
        "--ragged-mode",
        choices=["strict", "ragged"],
        help="Normalization strategy for ragged tables (default: strict)",
    )
    parser.add_argument(
        "--ragged-fill-value",
        type=str,
        help="Filler token to use for missing cells when ragged mode is enabled",
    )
    parser.add_argument(
        "--section-detection",
        action="store_true",
        help="Enable detection of multi-panel/stacked tables",
    )

    # Config file
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to YAML/JSON config file",
    )

    return parser.parse_args(args)


def build_cli_config(args: argparse.Namespace) -> dict:
    """Build configuration dictionary from parsed CLI arguments.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Dictionary of configuration values from CLI arguments.
    """
    config = {}

    if args.input:
        config["input_path"] = args.input

    if args.pages:
        config["page_indices"] = parse_page_indices(args.pages)

    if args.dpi is not None:
        config["dpi"] = args.dpi

    if args.default_rows is not None:
        config["default_rows"] = args.default_rows

    if args.default_cols is not None:
        config["default_cols"] = args.default_cols

    if args.ocr_confidence_threshold is not None:
        config["ocr_confidence_threshold"] = args.ocr_confidence_threshold

    if args.llm_fallback_enabled:
        config["llm_fallback_enabled"] = True

    if args.llm_provider:
        config["llm_provider"] = args.llm_provider

    if args.llm_model:
        config["llm_model"] = args.llm_model

    if args.llm_api_key:
        config["llm_api_key"] = args.llm_api_key

    if args.log_level:
        config["log_level"] = args.log_level

    if args.log_file:
        config["log_file"] = str(args.log_file)

    if args.log_format:
        config["log_format"] = args.log_format

    if args.debug:
        config["enable_debug_artifacts"] = True

    if args.debug_output_dir:
        config["debug_output_dir"] = args.debug_output_dir

    if args.no_overlays:
        config["generate_overlays"] = False

    if args.no_html_report:
        config["generate_html_report"] = False

    # Concurrency settings
    if args.worker_type:
        config["worker_type"] = args.worker_type

    if args.max_workers is not None:
        config["max_workers"] = args.max_workers

    if args.page_batch_size is not None:
        config["page_batch_size"] = args.page_batch_size

    if args.max_inflight_pages is not None:
        config["max_inflight_pages"] = args.max_inflight_pages

    if args.run_timeout is not None:
        config["run_timeout_seconds"] = args.run_timeout

    if args.enable_irregular_detection:
        config["enable_irregular_structure_detection"] = True

    if args.ragged_mode:
        config["ragged_mode"] = args.ragged_mode

    if args.ragged_fill_value is not None:
        config["ragged_fill_value"] = args.ragged_fill_value

    if args.section_detection:
        config["enable_section_detection"] = True

    # Preset configuration
    if hasattr(args, 'preset') and args.preset:
        config["extraction_preset"] = args.preset

    return config


def _write_excel_output(result, output_path: Path) -> None:
    """Write extraction result to Excel file with confidence highlighting.
    
    Args:
        result: ExtractionResult from pipeline
        output_path: Path to output Excel file
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font
        from openpyxl.comments import Comment
    except ImportError:
        raise ImportError(
            "openpyxl is required for Excel output. "
            "Install it with: pip install openpyxl"
        )
    
    wb = Workbook()
    # Remove default sheet
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
    
    # Define color fills for confidence levels
    high_conf_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")  # Light green
    medium_conf_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")  # Light yellow
    low_conf_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")  # Light red
    
    # Write each table to a separate sheet
    for i, table_spec in enumerate(result.tables):
        # Get table metadata if available
        meta = result.metadata[i] if i < len(result.metadata) else None
        sheet_name = meta.table_id if meta and meta.table_id else f"Table_{i+1}"
        
        # Excel sheet names are limited to 31 characters
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:28] + "..."
        
        # Create sheet
        ws = wb.create_sheet(title=sheet_name)
        
        # Write header row
        header = [col.name for col in table_spec.columns]
        ws.append(header)
        
        # Check if we have meaningful confidence data
        # Only show confidence highlighting if:
        # 1. Cell confidences exist, AND
        # 2. There's actual variation (not all 1.0 - which means no real confidence tracking)
        cell_confidences = None
        has_meaningful_confidence = False
        
        if meta and hasattr(meta, 'cell_confidences') and meta.cell_confidences:
            cell_confidences = meta.cell_confidences
            # Check if confidences vary (if all are 1.0, it's just a placeholder)
            all_confidences = [c for row in cell_confidences for c in row]
            if all_confidences:
                # Consider it meaningful if we have variance or any value != 1.0
                unique_values = set(all_confidences)
                has_meaningful_confidence = len(unique_values) > 1 or 1.0 not in unique_values
        
        # Also check if we have consensus or position confidence
        has_consensus = (meta and hasattr(meta, 'consensus_confidence') and 
                        meta.consensus_confidence is not None and meta.consensus_confidence < 1.0)
        has_position = (meta and hasattr(meta, 'position_confidence') and 
                       meta.position_confidence is not None)
        
        # Enable highlighting only if we have real confidence data
        enable_highlighting = has_meaningful_confidence or has_consensus or has_position
        
        # Write data rows with optional confidence highlighting
        for row_idx, row in enumerate(table_spec.rows):
            ws.append(row)
            
            # Apply confidence-based highlighting only if available
            excel_row_idx = row_idx + 2
            
            if enable_highlighting and cell_confidences and row_idx < len(cell_confidences):
                for col_idx, cell_value in enumerate(row):
                    if col_idx < len(cell_confidences[row_idx]):
                        confidence = cell_confidences[row_idx][col_idx]
                        
                        # Get Excel cell (column is 1-indexed)
                        excel_col_idx = col_idx + 1
                        cell = ws.cell(row=excel_row_idx, column=excel_col_idx)
                        
                        # Apply color based on confidence
                        if confidence >= 0.85:
                            cell.fill = high_conf_fill  # Green: High confidence
                        elif confidence >= 0.70:
                            cell.fill = medium_conf_fill  # Yellow: Medium confidence
                        else:
                            cell.fill = low_conf_fill  # Red: Low confidence
                            
                            # Add comment for low confidence cells
                            comment_text = f"Low confidence: {confidence:.2f}\nVerify this value"
                            cell.comment = Comment(comment_text, "PDF Reader")
        
        # Add comprehensive metadata as comment in cell A1
        if meta:
            info_lines = [f"Table: {meta.table_id}", f"Page: {meta.page_index}"]
            
            # Add confidence info only if available
            if enable_highlighting:
                if hasattr(meta, 'consensus_confidence') and meta.consensus_confidence is not None:
                    info_lines.append(f"Consensus Confidence: {meta.consensus_confidence:.2f}")
                
                if hasattr(meta, 'position_confidence') and meta.position_confidence is not None:
                    info_lines.append(f"Position Confidence: {meta.position_confidence:.2f}")
                
                if hasattr(meta, 'average_confidence'):
                    info_lines.append(f"Overall Confidence: {meta.average_confidence:.2f}")
                
                if hasattr(meta, 'mismatched_cells') and meta.mismatched_cells:
                    info_lines.append(f"Low Confidence Cells: {len(meta.mismatched_cells)}")
            else:
                # Explain why confidence isn't available
                info_lines.append("")
                info_lines.append("⚠️ Confidence Scoring: Not Available")
                if not has_consensus:
                    info_lines.append("  • Reason: Single LLM attempt (no consensus)")
                    info_lines.append("  • To enable: Use --llm-consistency-attempts 3")
                if not has_position:
                    info_lines.append("  • Reason: Scanned PDF (no native text)")
                    info_lines.append("  • Position verification requires text-based PDFs")
            
            if hasattr(meta, 'irregularities') and meta.irregularities:
                info_lines.append(f"Notes: {', '.join(meta.irregularities)}")
            
            info = "\n".join(info_lines)
            ws['A1'].comment = Comment(info, "PDF Reader")
        
        # Add legend only if confidence highlighting is enabled
        if enable_highlighting:
            legend_row = len(table_spec.rows) + 3
            ws.cell(row=legend_row, column=1, value="Confidence Legend:")
            ws.cell(row=legend_row, column=1).font = Font(bold=True)
            
            ws.cell(row=legend_row + 1, column=1, value="High (≥0.85)").fill = high_conf_fill
            ws.cell(row=legend_row + 2, column=1, value="Medium (0.70-0.85)").fill = medium_conf_fill
            ws.cell(row=legend_row + 3, column=1, value="Low (<0.70)").fill = low_conf_fill
        else:
            # Add note that confidence scoring isn't available
            note_row = len(table_spec.rows) + 3
            ws.cell(row=note_row, column=1, value="ℹ️ Confidence Scoring: Not Available")
            ws.cell(row=note_row, column=1).font = Font(bold=True, color="0066CC")
            ws.cell(row=note_row + 1, column=1, value="Single LLM attempt used (no consensus verification)")
            ws.cell(row=note_row + 2, column=1, value="To enable: Use --llm-consistency-attempts 3 with text-based PDFs")
    
    # If no tables extracted, create a placeholder sheet
    if not result.tables:
        ws = wb.create_sheet(title="NoTablesFound")
        ws.append(["No tables were extracted from the PDF"])
    
    # Save workbook
    wb.save(output_path)


def _signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) by setting the global cancel event."""
    global _cancel_event
    if _cancel_event is not None:
        _cancel_event.set()
        print("\nCancellation requested, finishing current work...", file=sys.stderr)


def main(args: Optional[Sequence[str]] = None) -> int:
    """Main CLI entrypoint.

    Args:
        args: Optional list of command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    global _cancel_event
    
    try:
        parsed_args = parse_args(args)

        if parsed_args.command != "extract":
            print(f"Error: Unknown command '{parsed_args.command}'", file=sys.stderr)
            return 1

        # Validate input file exists
        if not parsed_args.input.exists():
            print(f"Error: Input file not found: {parsed_args.input}", file=sys.stderr)
            return 1

        # Build CLI config overrides
        cli_config = build_cli_config(parsed_args)

        # Create merged configuration
        config = create_config(
            config_file=parsed_args.config,
            cli_overrides=cli_config,
        )

        # Override input_path from CLI (required argument)
        config.input_path = parsed_args.input

        # Set up signal handling for graceful cancellation
        # Note: The PipelineRunner creates its own cancel_event internally,
        # but signal handling at the CLI level provides user feedback.
        # The timeout mechanism in PipelineRunner provides programmatic cancellation.
        original_handler = signal.signal(signal.SIGINT, _signal_handler)
        
        try:
            # Run the pipeline
            runner = PipelineRunner()
            result = runner.extract_tables(parsed_args.input, config=config)
        finally:
            # Restore original signal handler
            signal.signal(signal.SIGINT, original_handler)

        # Write output to Excel if specified
        if parsed_args.output:
            try:
                _write_excel_output(result, parsed_args.output)
                print(f"\nOutput written to: {parsed_args.output}")
            except Exception as e:
                print(f"\nWarning: Failed to write output file: {e}", file=sys.stderr)

        # Print summary
        stats = result.run_stats
        print("\n" + "=" * 60)
        print("Extraction Summary")
        print("=" * 60)
        print(f"Pages processed: {stats.pages_processed}")
        print(f"Tables detected: {stats.tables_detected}")
        print(f"Tables extracted: {stats.tables_extracted}")
        print(f"Tables failed: {stats.tables_failed}")
        print(f"Total cells extracted: {stats.total_cells_extracted}")
        print(f"Average OCR confidence: {stats.average_ocr_confidence:.2f}")
        if stats.llm_fallback_count > 0:
            print(f"LLM fallback calls: {stats.llm_fallback_count}")
        print(f"Total duration: {stats.total_duration_ms:.2f} ms")

        irregular_tables = [
            meta
            for meta in result.metadata
            if getattr(meta, "irregularities", None) and meta.status == "success"
        ]
        if irregular_tables:
            print("\nIrregular structure warnings:")
            for meta in irregular_tables[:5]:
                issues = ", ".join(meta.irregularities)
                confidence = getattr(meta, "structure_confidence", 0.0)
                print(
                    f"  - Table {meta.table_id}: {issues} (confidence {confidence:.2f})"
                )
            if len(irregular_tables) > 5:
                print(f"  ...and {len(irregular_tables) - 5} more tables")

        if stats.errors:
            print(f"\nErrors ({len(stats.errors)}):")
            for error in stats.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(stats.errors) > 5:
                print(f"  ... and {len(stats.errors) - 5} more errors")

        if config.enable_debug_artifacts:
            print(f"\nDebug artifacts saved to: {config.debug_output_dir}")

        # Save manifest if requested
        if parsed_args.emit_manifest and result.run_manifest:
            from .manifest import save_manifest
            
            if parsed_args.manifest_output:
                manifest_path = Path(parsed_args.manifest_output)
            else:
                manifest_path = Path(config.debug_output_dir) / "run_manifest.json"
            
            try:
                save_manifest(result.run_manifest, manifest_path)
                print(f"\nRun manifest saved to: {manifest_path}")
            except Exception as e:
                print(f"\nWarning: Failed to save manifest: {e}", file=sys.stderr)

        print("=" * 60)

        # Exit with error code if there were failures
        if stats.tables_failed > 0 or stats.pages_skipped > 0:
            return 1

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

