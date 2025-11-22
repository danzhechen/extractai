from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from . import PipelineConfig, PipelineRunner


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a minimal pdf-reading-project vertical slice on a PDF."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to input PDF file.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Rendering DPI for page images (default: 200).",
    )
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="Optional comma-separated list of page indices (0-based) to process, e.g. '0,1'.",
    )
    return parser


def _parse_page_indices(pages_arg: Optional[str]) -> Optional[list[int]]:
    if not pages_arg:
        return None
    return [int(p.strip()) for p in pages_arg.split(",") if p.strip()]


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    page_indices = _parse_page_indices(args.pages)

    cfg = PipelineConfig(
        input_path=input_path,
        page_indices=page_indices,
        dpi=args.dpi,
    )

    runner = PipelineRunner()
    result = runner.extract_tables(str(input_path), config=cfg)

    print(f"Pages processed: {result.run_stats.pages_processed}")
    print(f"Tables detected: {result.run_stats.tables_detected}")
    if result.run_stats.errors:
        print("Errors:")
        for err in result.run_stats.errors:
            print(f"  - {err}")

    for idx, table in enumerate(result.tables):
        print(f"\n=== Table {idx} ===")
        for row in table.rows:
            print(" | ".join(str(value) if value is not None else "" for value in row))


if __name__ == "__main__":
    main()




