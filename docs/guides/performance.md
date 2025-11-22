# Performance Tuning Guide

This guide explains how to optimize the PDF table extraction pipeline for performance, including concurrency configuration, resource management, and troubleshooting tips.

## Overview

The pipeline supports configurable concurrency to improve performance when processing multi-page PDFs. By default, the pipeline uses thread-based parallelism with automatic worker count selection based on system resources.

## Quick Start

### Basic Configuration

For most use cases, the default configuration provides good performance:

```python
from pdf_reader import PipelineConfig, PipelineRunner

config = PipelineConfig(
    input_path="document.pdf",
    worker_type="thread",  # Default
    # max_workers is auto-detected based on CPU count
)
runner = PipelineRunner()
result = runner.extract_tables("document.pdf", config=config)
```

### CLI Usage

```bash
# Use default parallel processing
pdf-reader extract --input document.pdf

# Specify worker count
pdf-reader extract --input document.pdf --max-workers 4

# Use sequential processing (for debugging)
pdf-reader extract --input document.pdf --worker-type sequential
```

## Concurrency Configuration

### Worker Type

**`thread`** (default): Use thread pool for parallel processing.
- Best for: IO-bound workloads (PDF rendering, OCR, LLM API calls)
- Pros: Good performance, simple implementation, low overhead
- Cons: Limited by Python GIL for CPU-bound work

**`sequential`**: Process pages one at a time.
- Best for: Debugging, single-page PDFs, memory-constrained environments
- Pros: Simple, predictable, lower memory usage
- Cons: Slower for multi-page PDFs

### Worker Count

**Default**: `min(4, cpu_count())` with minimum of 1.

**Tuning Guidelines**:
- **2-4 workers**: Good for most use cases (2-10 pages)
- **4-8 workers**: For larger PDFs (10-50 pages) with good system resources
- **8+ workers**: Diminishing returns, may cause resource contention

**Example**:
```python
config = PipelineConfig(
    input_path="large_document.pdf",
    max_workers=6,  # Override default
)
```

### Back-Pressure Configuration

**`page_batch_size`** (default: 4): Number of pages to queue before applying back-pressure.

**`max_inflight_pages`** (default: `max(page_batch_size, max_workers)`): Hard limit on concurrently queued pages.

**Tuning Guidelines**:
- **Small values (2-4)**: Lower memory usage, more back-pressure
- **Large values (8-16)**: Higher memory usage, less back-pressure
- **Memory-constrained**: Reduce both values

**Example**:
```python
config = PipelineConfig(
    input_path="document.pdf",
    page_batch_size=2,  # More conservative
    max_inflight_pages=4,  # Hard limit
)
```

## Performance Optimization

### 1. Worker Count Tuning

**For IO-bound workloads** (OCR, LLM API calls):
- Start with `max_workers = 4`
- Increase if CPU/memory allows and you're not hitting rate limits
- Monitor worker utilization in `RunStats.worker_utilization`

**For CPU-bound workloads** (if using CPU-intensive OCR):
- Consider lower worker counts (2-4) to avoid GIL contention
- Future: Process pools may be supported if components become pickleable

### 2. Memory Management

**Reduce memory usage**:
- Lower `max_workers` to reduce concurrent page images
- Lower `max_inflight_pages` to reduce queue depth
- Process pages in batches using `page_indices`

**Example**:
```python
# Process pages in batches of 10
for batch_start in range(0, total_pages, 10):
    batch_end = min(batch_start + 10, total_pages)
    config.page_indices = list(range(batch_start, batch_end))
    result = runner.extract_tables("document.pdf", config=config)
```

### 3. Timeout Configuration

Set a timeout to prevent long-running jobs from hanging:

```python
config = PipelineConfig(
    input_path="document.pdf",
    run_timeout_seconds=300,  # 5 minutes
)
```

When timeout is exceeded, the pipeline:
- Cancels remaining work gracefully
- Returns partial results
- Sets `RunStats.abort_reason` with timeout information

### 4. DPI and Quality Trade-offs

Higher DPI improves quality but increases processing time and memory:

```python
# Fast processing, lower quality
config = PipelineConfig(dpi=150)

# Balanced (default)
config = PipelineConfig(dpi=200)

# High quality, slower processing
config = PipelineConfig(dpi=300)
```

## Monitoring and Metrics

### Key Metrics in `RunStats`

**Concurrency Metrics**:
- `worker_type`: Concurrency strategy used
- `max_workers_used`: Actual number of workers
- `queue_high_water_mark`: Maximum queue depth reached
- `work_units_scheduled`: Total work units submitted
- `work_units_completed`: Total work units completed
- `worker_utilization`: Worker efficiency (0.0-1.0)

**Performance Metrics**:
- `total_duration_ms`: Total execution time
- `average_page_duration_ms`: Average time per page
- `min_page_duration_ms`: Fastest page
- `max_page_duration_ms`: Slowest page

**Example**:
```python
result = runner.extract_tables("document.pdf", config=config)
stats = result.run_stats

print(f"Worker utilization: {stats.worker_utilization:.2%}")
print(f"Queue high water mark: {stats.queue_high_water_mark}")
print(f"Average page duration: {stats.average_page_duration_ms:.2f} ms")
```

### Logging

Enable structured logging to trace slow pages:

```python
config = PipelineConfig(
    input_path="document.pdf",
    log_level="DEBUG",  # See per-page processing logs
    log_format="json",  # Structured logs for analysis
)
```

Logs include:
- Page processing start/stop events
- Worker lifecycle events
- Queue depth information
- Error details

## Troubleshooting

### High Memory Usage

**Symptoms**: System runs out of memory, process killed.

**Solutions**:
1. Reduce `max_workers` (e.g., from 4 to 2)
2. Reduce `max_inflight_pages` (e.g., from 4 to 2)
3. Process pages in smaller batches
4. Lower DPI if quality allows

### Low Speed-up

**Symptoms**: Parallel processing is not significantly faster than sequential.

**Possible Causes**:
1. **CPU-bound workload**: GIL limits parallelism
   - Solution: Reduce worker count or wait for process pool support
2. **Rate limiting**: OCR/LLM APIs are rate-limiting
   - Solution: Reduce `max_workers` or add request throttling
3. **I/O bottleneck**: Disk or network I/O is the bottleneck
   - Solution: Check disk speed, network latency
4. **System load**: Other processes are using resources
   - Solution: Run on a less loaded system

**Diagnosis**:
```python
stats = result.run_stats
if stats.worker_utilization < 0.5:
    print("Low worker utilization - may indicate bottleneck")
```

### Non-Deterministic Results

**Symptoms**: Results vary between runs.

**Possible Causes**:
1. Race conditions in custom components
2. Non-deterministic OCR/LLM responses
3. Timing-dependent behavior

**Solutions**:
1. Use `worker_type="sequential"` for debugging
2. Verify custom components are thread-safe
3. Check for shared mutable state

### Worker Crashes

**Symptoms**: Some pages fail with worker errors.

**Solutions**:
1. Check error messages in `RunStats.errors`
2. Verify components are thread-safe
3. Check for resource exhaustion (memory, file handles)
4. Review logs for specific failure patterns

## Best Practices

1. **Start with defaults**: The default configuration works well for most cases.

2. **Monitor metrics**: Check `worker_utilization` and `queue_high_water_mark` to identify bottlenecks.

3. **Tune incrementally**: Make small changes and measure impact.

4. **Consider your workload**:
   - **Small PDFs (1-5 pages)**: Sequential may be sufficient
   - **Medium PDFs (5-20 pages)**: Default parallel (4 workers)
   - **Large PDFs (20+ pages)**: Increase workers if resources allow

5. **Test in production-like environment**: Performance characteristics may differ from development.

6. **Use timeouts**: Set `run_timeout_seconds` to prevent hanging jobs.

## Known Limitations

1. **Process pools not supported**: Components are not pickleable, so process-based parallelism is not available.

2. **GIL limitations**: CPU-bound workloads may not see significant speed-up due to Python's Global Interpreter Lock.

3. **OCR engine thread safety**: If integrating custom OCR engines, ensure they're thread-safe or use per-worker instances.

4. **LLM API rate limits**: Parallel processing may hit API rate limits. Consider:
   - Reducing `max_workers`
   - Implementing request queuing/throttling
   - Using API providers with higher rate limits

## Future Enhancements

Potential future improvements:
- Process pool support (if components become pickleable)
- Adaptive worker count based on system load
- Request batching for LLM APIs
- Per-table parallelism (finer-grained work units)

## References

- [Concurrency Design Documentation](concurrency-design.md) - Detailed design decisions
- [Configuration Guide](configuration.md) - Complete configuration options
- [Architecture Documentation](../architecture.md) - System architecture overview



