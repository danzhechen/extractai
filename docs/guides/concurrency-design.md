# Concurrency Design and Architecture

This document describes the concurrency design decisions, trade-offs, and implementation details for the PDF table extraction pipeline.

## Overview

The pipeline supports configurable concurrency strategies to improve performance when processing multi-page PDFs. The default strategy uses thread-based parallelism with per-page work units, providing a good balance between performance and resource usage.

## Design Decisions

### 1. Concurrency Model Selection

**Decision**: Use thread-based parallelism (`ThreadPoolExecutor`) as the default strategy.

**Rationale**:
- **IO-bound workload**: PDF rendering and OCR operations are primarily IO-bound, making threads suitable for parallelization.
- **Shared state**: Components (detectors, extractors) are designed to be stateless or have minimal shared state, making thread safety straightforward.
- **Python GIL**: While the Global Interpreter Lock (GIL) limits CPU-bound parallelism, our workload is IO-bound, so threads provide good performance.
- **Simplicity**: Thread-based parallelism is simpler to implement and debug than process-based parallelism.

**Alternatives Considered**:
- **Process-based parallelism**: Rejected because:
  - Core detectors and page images are not easily pickleable for cross-process execution.
  - Process overhead is higher for fine-grained work units (per-page).
  - Would require significant refactoring to make components process-safe.
- **Async/await**: Rejected because:
  - Would require rewriting all components to be async-compatible.
  - Adds complexity without clear benefits for this use case.
  - Most OCR libraries are synchronous.

### 2. Work Unit Granularity

**Decision**: Use per-page work units (coarse-grained parallelism).

**Rationale**:
- **Natural boundaries**: Pages are natural boundaries in PDF processing.
- **Good load balancing**: Pages typically have similar processing times.
- **Simpler error handling**: Page-level errors are easier to isolate and handle.
- **Future extensibility**: Can be extended to per-table parallelism if needed.

**Trade-offs**:
- **Pros**: Simple, good for most use cases, easy to reason about.
- **Cons**: If a single page has many large tables, it may take longer than other pages, causing some load imbalance.

### 3. Default Worker Count

**Decision**: Default to `min(4, cpu_count())` workers, with a minimum of 1.

**Rationale**:
- **Balanced resource usage**: Prevents over-subscription while utilizing available cores.
- **Memory considerations**: Each worker holds a page image in memory, so limiting workers helps control memory usage.
- **Diminishing returns**: Beyond 4-8 workers, additional parallelism provides diminishing returns for IO-bound workloads.

**Configuration**: Users can override via `max_workers` config option.

### 4. Back-Pressure and Resource Limits

**Decision**: Implement bounded queue with `max_inflight_pages` to prevent memory exhaustion.

**Rationale**:
- **Memory safety**: Large PDFs can consume significant memory if all pages are queued simultaneously.
- **Predictable behavior**: Bounded queues provide predictable resource usage.
- **Graceful degradation**: When queue is full, the pipeline waits for workers to complete rather than failing.

**Default**: `max_inflight_pages` defaults to `max(page_batch_size, max_workers)`, typically 4.

### 5. Deterministic Ordering

**Decision**: Sort results by `page_index` after parallel processing to ensure deterministic output ordering.

**Rationale**:
- **Reproducibility**: Deterministic ordering makes results reproducible and easier to test.
- **User expectations**: Users expect tables to be returned in page order.
- **Simple implementation**: Sorting is cheap compared to the processing time.

**Implementation**: Results are collected and sorted by `page_index` before aggregation.

### 6. Sequential Mode

**Decision**: Provide a `sequential` worker type for debugging and single-threaded execution.

**Rationale**:
- **Debugging**: Sequential mode makes debugging easier by eliminating concurrency-related issues.
- **Compatibility**: Some environments may require single-threaded execution.
- **Baseline**: Provides a baseline for performance comparisons.

## Component Thread Safety

### Thread-Safe Components

The following components are designed to be thread-safe:

1. **TableRegionDetector**: 
   - **Status**: Stateless, thread-safe.
   - **Analysis**: The `detect` method only uses input parameters and returns new objects. No shared mutable state.

2. **GridStructureDetector**: 
   - **Status**: Thread-safe (immutable configuration only).
   - **Analysis**: Only contains `line_detection_config` which is immutable. All methods operate on input parameters and return new objects. Line detection functions are stateless.

3. **CellTextExtractor**: 
   - **Status**: Thread-safe when used correctly.
   - **Analysis**: 
     - Stateless except for `llm_service` reference.
     - When LLM fallback is enabled, each worker creates its own `CellTextExtractor` instance in `_process_page` (line 293-301 in pipeline.py).
     - When LLM fallback is disabled, `self.text_extractor` is shared, but `fill_cell_text` only modifies cells in the provided grid (per-page), so no shared mutable state contention.
     - The `_extract_with_ocr` method is stateless (currently placeholder).
     - The `_extract_with_llm` method uses `llm_service` which is thread-safe (see below).

4. **TableAssembler**: 
   - **Status**: Stateless, thread-safe.
   - **Analysis**: The `to_dataframe_spec` method only reads from the input grid and creates new objects. No shared state.

5. **LLM Services** (OpenAI, Mock): 
   - **Status**: Thread-safe.
   - **Analysis**: 
     - `OpenAIExtractionService` creates a new `openai.OpenAI` client per call in `extract_text_from_image`, so there's no shared connection pool or mutable state.
     - `MockLLMExtractionService` is stateless (only reads from `mock_responses` dict which is not modified during execution).
     - No shared connection pools or mutable state.

6. **PdfIngestionService**:
   - **Status**: Thread-safe for read operations.
   - **Analysis**: Uses `pdfplumber` which is thread-safe for reading PDFs. `render_page` creates new image objects, so no shared mutable state.

### Shared Components

The `PipelineRunner` instance is shared across threads, but:
- Component instances (`region_detector`, `grid_detector`, `text_extractor`, `assembler`) are designed to be stateless or have minimal shared state.
- Each worker processes a different page, so there's no contention for page-specific data.
- The `ingestion` service (`PdfIngestionService`) is shared, but `render_page` is thread-safe (uses pdfplumber which is thread-safe for read operations).

### Safety Audit Summary

**All components are thread-safe** for the current implementation:
- No shared mutable state between workers.
- Each worker processes independent pages with independent data structures.
- Components are either stateless or use immutable configuration.
- LLM services create new clients per call, avoiding connection pool contention.

**Future Considerations**:
- If integrating a custom OCR engine, ensure it's thread-safe or use per-worker instances.
- If adding connection pooling for LLM services, ensure the pool is thread-safe.
- If adding caching, ensure cache implementations are thread-safe (e.g., use `threading.local` or thread-safe cache libraries).

## Configuration Options

### Worker Type

- **`sequential`**: Process pages one at a time (single-threaded).
- **`thread`**: Use thread pool for parallel processing (default).
- **`process`**: Not supported (components not pickleable).
- **`async`**: Not supported (components not async-compatible).

### Worker Count

- **`max_workers`**: Maximum number of worker threads (default: `min(4, cpu_count())`).
- **`page_batch_size`**: Number of pages to queue before applying back-pressure (default: 4).
- **`max_inflight_pages`**: Hard limit on concurrently queued pages (default: `max(page_batch_size, max_workers)`).

### Timeout

- **`run_timeout_seconds`**: Optional timeout for the entire run. When exceeded, processing is cancelled gracefully and partial results are returned.

## Performance Characteristics

### Expected Speed-up

For multi-page PDFs with IO-bound processing:
- **2-4 pages**: ~1.5-2x speed-up with 2 workers.
- **5-10 pages**: ~2-3x speed-up with 4 workers.
- **10+ pages**: ~3-4x speed-up with 4-8 workers (diminishing returns beyond this).

Actual speed-up depends on:
- Page complexity (number of tables, cell count).
- OCR/LLM API latency (if using external services).
- System resources (CPU, memory, I/O bandwidth).

### Resource Usage

- **Memory**: Each worker holds one page image in memory (~5-20MB per page depending on DPI).
- **CPU**: Primarily IO-bound, so CPU usage is moderate.
- **Network**: If using LLM fallback, network usage scales with worker count.

## Known Limitations

1. **Process-based parallelism not supported**: Components are not pickleable, so process pools cannot be used.

2. **OCR engine thread safety**: If integrating a custom OCR engine, ensure it's thread-safe. Some OCR engines may require per-worker instances or locking.

3. **LLM API rate limits**: When using LLM fallback with parallel processing, be aware of API rate limits. Consider:
   - Reducing `max_workers` if hitting rate limits.
   - Implementing request queuing/throttling in the LLM service.

4. **Debug artifacts**: Debug artifacts (overlay images, HTML reports) are generated per-page and may have slightly different ordering in parallel mode, but final results are sorted deterministically.

## Future Enhancements

Potential future improvements:
1. **Per-table parallelism**: Process multiple tables on the same page in parallel.
2. **Adaptive worker count**: Adjust worker count based on system load.
3. **Request batching**: Batch LLM requests to improve throughput.
4. **Process pool support**: If components become pickleable, add process pool support for CPU-bound workloads.

## Troubleshooting

### High Memory Usage

- Reduce `max_workers` to limit concurrent page processing.
- Reduce `max_inflight_pages` to limit queue depth.
- Process pages in smaller batches using `page_indices`.

### Low Speed-up

- Check if workload is CPU-bound (may need process pool if components become pickleable).
- Verify OCR/LLM services are not rate-limiting.
- Check system I/O bandwidth.

### Non-Deterministic Results

- Ensure `worker_type` is not `process` or `async` (not supported).
- Verify results are sorted by `page_index` (should be automatic).
- Check for race conditions in custom components.

