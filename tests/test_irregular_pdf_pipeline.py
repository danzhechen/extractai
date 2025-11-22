"""End-to-end tests for irregular PDF fixtures (Story 3.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional, cast

import pytest

from pdf_reader import PipelineConfig, PipelineRunner

from tests.fixtures.irregular_pdf_factory import (
    create_multi_panel_pdf,
    create_partial_borders_pdf,
    create_ragged_schedule_pdf,
)

PdfFactory = Callable[[Path], Path]


@pytest.mark.parametrize(
    "fixture_fn,config_overrides,expectations",
    [
        (
            create_partial_borders_pdf,
            {
                "enable_irregular_structure_detection": True,
                "worker_type": "sequential",
                "default_rows": 5,
                "default_cols": 3,
                "dpi": 220,
            },
            {"irregularity": "partial_borders"},
        ),
        (
            create_ragged_schedule_pdf,
            {
                "enable_irregular_structure_detection": True,
                "worker_type": "sequential",
                "ragged_mode": "ragged",
                "ragged_fill_value": "__MISSING__",
                "default_rows": 6,
                "default_cols": 3,
                "dpi": 220,
            },
            {"irregularity": "ragged_columns", "expect_filler": "__MISSING__"},
        ),
        (
            create_multi_panel_pdf,
            {
                "enable_irregular_structure_detection": True,
                "enable_section_detection": True,
                "worker_type": "sequential",
                "default_rows": 4,
                "default_cols": 3,
                "dpi": 220,
            },
            {"expect_sections": True, "min_tables": 2},
        ),
    ],
)
def test_irregular_pdf_pipeline(
    tmp_path: Path,
    fixture_fn: PdfFactory,
    config_overrides: Dict[str, object],
    expectations: Dict[str, object],
) -> None:
    """Verify that irregular PDFs trigger the expected heuristics and metadata."""

    pdf_path = fixture_fn(tmp_path)
    runner = PipelineRunner()

    overrides = dict(config_overrides)
    cfg_kwargs = {
        "input_path": pdf_path,
        "page_indices": None,
        "dpi": overrides.pop("dpi", 200),
    }
    cfg_kwargs.update(overrides)
    config = PipelineConfig(**cfg_kwargs),
    extraction_preset="offline",

    result = runner.extract_tables(str(pdf_path), config=config)
    assert result.metadata, "expected at least one table to be detected"

    if "irregularity" in expectations:
        irregularity = expectations["irregularity"]
        assert any(
            irregularity in (meta.irregularities or [])
            for meta in result.metadata
        ), f"expected irregularity '{irregularity}' in metadata"

    filler_value = cast(Optional[str], expectations.get("expect_filler"))
    if filler_value:
        assert any(
            filler_value in (cell or "")  # rows may contain None
            for table in result.tables
            for row in table.rows
            for cell in row
        ), f"expected filler value '{filler_value}' in assembled table rows"

    if expectations.get("expect_sections"):
        assert any(
            meta.section_labels for meta in result.metadata
        ), "expected section labels for multi-panel detection"

    if "min_tables" in expectations:
        assert len(result.metadata) >= expectations["min_tables"]


