"""Tests for parallel processing and concurrency features."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pdf_reader import PipelineConfig, PipelineRunner


def _create_multi_page_pdf(path: Path, num_pages: int = 5) -> None:
    """Create a multi-page PDF with tables on each page."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for page_num in range(num_pages):
        # Add some content to each page
        c.drawString(100, 750, f"Page {page_num + 1} Header")
        c.drawString(100, 730, "Col1 Col2 Col3")
        c.drawString(100, 710, f"Row1Col1 Row1Col2 Row1Col3")
        c.drawString(100, 690, f"Row2Col1 Row2Col2 Row2Col3")
        if page_num < num_pages - 1:
            c.showPage()
    c.save()


def test_sequential_processing_produces_deterministic_results(tmp_path):
    """Test that sequential processing produces deterministic, ordered results."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=4)

    cfg = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="sequential",
        extraction_preset="offline",
    )
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Verify worker type is recorded
    assert result.run_stats.worker_type == "sequential"
    assert result.run_stats.max_workers_used == 1

    # Verify pages are processed in order
    page_indices = [meta.page_index for meta in result.metadata]
    assert page_indices == sorted(page_indices)

    # Verify all pages were processed
    assert result.run_stats.pages_processed == 4


def test_thread_parallel_processing_produces_deterministic_results(tmp_path):
    """Test that parallel processing produces deterministic, ordered results."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=5)

    cfg = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="thread",
        max_workers=2,
        extraction_preset="offline",
    )
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Verify worker type is recorded
    assert result.run_stats.worker_type == "thread"
    assert result.run_stats.max_workers_used == 2

    # Verify pages are processed in order (results should be sorted by page_index)
    page_indices = [meta.page_index for meta in result.metadata]
    assert page_indices == sorted(page_indices), "Results should be deterministically ordered"

    # Verify all pages were processed
    assert result.run_stats.pages_processed == 5

    # Verify concurrency metrics are populated
    assert result.run_stats.work_units_scheduled == 5
    assert result.run_stats.work_units_completed == 5
    assert result.run_stats.queue_high_water_mark >= 0


def test_parallel_processing_with_custom_worker_count(tmp_path):
    """Test parallel processing with custom worker count."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=6)

    cfg = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="thread",
        max_workers=3,
        extraction_preset="offline",
    )
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    assert result.run_stats.worker_type == "thread"
    assert result.run_stats.max_workers_used == 3
    assert result.run_stats.pages_processed == 6


def test_parallel_processing_with_back_pressure(tmp_path):
    """Test that back-pressure limits are respected."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=8)

    cfg = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="thread",
        max_workers=2,
        page_batch_size=3,
        max_inflight_pages=3,
        extraction_preset="offline",
    )
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Verify queue high water mark doesn't exceed max_inflight_pages
    assert result.run_stats.queue_high_water_mark <= cfg.max_inflight_pages
    assert result.run_stats.pages_processed == 8


def test_sequential_and_parallel_produce_same_results(tmp_path):
    """Test that sequential and parallel processing produce equivalent results."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=4)

    # Run sequential
    cfg_seq = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="sequential",
    )
    runner = PipelineRunner()
    result_seq = runner.extract_tables(str(pdf_path), config=cfg_seq)

    # Run parallel
    cfg_par = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="thread",
        max_workers=2,
    )
    result_par = runner.extract_tables(str(pdf_path), config=cfg_par)

    # Both should process the same number of pages
    assert result_seq.run_stats.pages_processed == result_par.run_stats.pages_processed
    assert result_seq.run_stats.tables_detected == result_par.run_stats.tables_detected
    assert result_seq.run_stats.tables_extracted == result_par.run_stats.tables_extracted

    # Both should have the same number of tables
    assert len(result_seq.tables) == len(result_par.tables)

    # Both should have tables from the same pages (order may differ, but set should match)
    seq_pages = {meta.page_index for meta in result_seq.metadata}
    par_pages = {meta.page_index for meta in result_par.metadata}
    assert seq_pages == par_pages


def test_parallel_processing_metrics_are_populated(tmp_path):
    """Test that concurrency metrics are properly populated."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=5)

    cfg = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="thread",
        max_workers=2,
        extraction_preset="offline",
    )
    runner = PipelineRunner()
    result = runner.extract_tables(str(pdf_path), config=cfg)

    stats = result.run_stats

    # Verify concurrency metrics
    assert stats.worker_type == "thread"
    assert stats.max_workers_used == 2
    assert stats.work_units_scheduled == 5
    assert stats.work_units_completed == 5
    assert stats.queue_high_water_mark >= 0

    # Verify page duration metrics
    assert stats.average_page_duration_ms >= 0
    assert stats.max_page_duration_ms >= stats.min_page_duration_ms

    # Worker utilization should be between 0 and 1
    assert 0.0 <= stats.worker_utilization <= 1.0


def test_worker_type_validation():
    """Test that invalid worker types are rejected."""
    # Process and async should be rejected
    try:
        PipelineConfig(worker_type="process")
        assert False, "Should have raised ValueError for 'process' worker type"
    except ValueError:
        pass

    try:
        PipelineConfig(worker_type="async")
        assert False, "Should have raised ValueError for 'async' worker type"
    except ValueError:
        pass

    # Sequential and thread should be accepted
    cfg_seq = PipelineConfig(worker_type="sequential")
    assert cfg_seq.worker_type == "sequential"

    cfg_thread = PipelineConfig(worker_type="thread")
    assert cfg_thread.worker_type == "thread"


def test_max_workers_validation():
    """Test that max_workers validation works."""
    # Negative workers should be rejected
    try:
        PipelineConfig(max_workers=-1)
        assert False, "Should have raised ValueError for negative max_workers"
    except ValueError:
        pass

    # Zero workers should be rejected
    try:
        PipelineConfig(max_workers=0)
        assert False, "Should have raised ValueError for zero max_workers"
    except ValueError:
        pass

    # Positive workers should be accepted
    cfg = PipelineConfig(max_workers=4, extraction_preset="offline")
    assert cfg.max_workers == 4


def test_parallel_processing_handles_errors_gracefully(tmp_path):
    """Test that parallel processing handles worker errors gracefully."""
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=4)

    cfg = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="thread",
        max_workers=2,
        extraction_preset="offline",
    )
    runner = PipelineRunner()

    # Mock a worker to fail on one page
    original_process = runner._process_page_worker

    def mock_process_page_worker(page_index, document, config, logger, cancel_event):
        if page_index == 2:
            # Simulate a worker crash
            raise RuntimeError(f"Simulated worker failure on page {page_index}")
        return original_process(page_index, document, config, logger, cancel_event)

    runner._process_page_worker = mock_process_page_worker

    result = runner.extract_tables(str(pdf_path), config=cfg)

    # Should still process other pages
    assert result.run_stats.pages_processed == 4
    # Should have errors recorded
    assert len(result.run_stats.errors) > 0
    # Should have completed some work units
    assert result.run_stats.work_units_completed > 0


def test_parallel_processing_speedup_vs_sequential(tmp_path):
    """Test that parallel processing provides speed-up vs sequential baseline.
    
    This test verifies that parallel processing completes faster than sequential
    processing for multi-page PDFs. The actual speed-up depends on system resources,
    but we verify that parallel processing doesn't take significantly longer.
    """
    import time
    
    pdf_path = tmp_path / "multi_page.pdf"
    _create_multi_page_pdf(pdf_path, num_pages=6)

    # Run sequential
    cfg_seq = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="sequential",
    )
    runner = PipelineRunner()
    start_seq = time.time()
    result_seq = runner.extract_tables(str(pdf_path), config=cfg_seq)
    duration_seq = time.time() - start_seq

    # Run parallel
    cfg_par = PipelineConfig(
        input_path=pdf_path,
        page_indices=None,
        dpi=150,
        worker_type="thread",
        max_workers=3,
    )
    start_par = time.time()
    result_par = runner.extract_tables(str(pdf_path), config=cfg_par)
    duration_par = time.time() - start_par

    # Both should process the same pages and produce equivalent results
    assert result_seq.run_stats.pages_processed == result_par.run_stats.pages_processed
    assert result_seq.run_stats.tables_detected == result_par.run_stats.tables_detected
    
    # Parallel should not be significantly slower (allowing for overhead)
    # In ideal conditions, parallel should be faster, but we're lenient here
    # to account for system load and test environment variability
    assert duration_par <= duration_seq * 1.5, (
        f"Parallel processing took {duration_par:.2f}s vs sequential {duration_seq:.2f}s. "
        "This may indicate a performance regression or high system load."
    )
    
    # Verify metrics are populated for parallel run
    assert result_par.run_stats.worker_type == "thread"
    assert result_par.run_stats.max_workers_used == 3
    assert result_par.run_stats.work_units_scheduled == 6
    assert result_par.run_stats.work_units_completed == 6

