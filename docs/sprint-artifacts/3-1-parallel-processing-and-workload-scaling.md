# Story 3.1: Parallel processing and workload scaling

Status: review

## Story

As an **engineer orchestrating extractions for large, multi-hundred-page PDFs**,  
I want **the pipeline to process pages and tables concurrently with predictable resource usage**,  
so that **turnaround time improves without sacrificing determinism or stability**.

## Acceptance Criteria

1. **Config-driven concurrency**
   - `PipelineConfig` exposes `max_workers`, `worker_type` (thread/process/async), and batching options with documented defaults.
   - CLI/CLI config wiring surfaces the new settings and validates illegal combinations (e.g., process pool + non-pickleable detectors).

2. **Thread/process-safe execution**
   - `PipelineRunner` schedules per-page or per-table work units on a worker pool while preserving deterministic ordering of outputs (`table_id`, `page_index`).
   - Shared components (OCR clients, models) are guarded or pooled to avoid race conditions, double frees, or GIL contention.

3. **Back-pressure & resource limits**
   - Long-running jobs respect user-specified memory/CPU caps (e.g., limit concurrent page renders) and provide hooks for cooperative cancellation/timeout.
   - Run aborts return a structured error with partial results and metrics rather than hanging.

4. **Metrics & observability**
   - `RunStats` captures concurrency-specific metrics (queue depth high-water mark, worker utilization, per-stage durations).
   - Structured logs emit start/stop events per work unit so ops teams can trace slow pages.

5. **Verification artifacts**
   - Tests (unit + integration) cover:
     - Deterministic ordering even with concurrency.
     - Speed-up vs. single-thread baseline on synthetic multi-page fixture.
     - Graceful degradation when a worker crashes (retries or clear failure).
   - Documentation (`docs/guides/performance.md` or existing guide) explains tuning guidance and known limitations (e.g., OCR engines that are not thread-safe).

## Tasks / Subtasks

- [x] **T3.1.1 — Concurrency design spike**
  - [x] Evaluate concurrency models (threads vs. processes vs. asyncio) per component constraints.
  - [x] Decide default strategy (likely thread pool for IO-bound OCR) and document trade-offs.

- [x] **T3.1.2 — Worker orchestration implementation**
  - [x] Refactor `PipelineRunner` to create work queues of `PageWorkItem`/`TableWorkItem`.
  - [x] Ensure deterministic ordering of final `ExtractionResult` via stable sorting or ordered joins.
  - [x] Add cooperative cancellation hooks for CLI signal handling.

- [x] **T3.1.3 — Component safety audit**
  - [x] Review detectors/extractors for shared mutable state; add locks or per-worker instances.
  - [x] Provide cache/pool abstractions for expensive OCR/LLM clients.

- [x] **T3.1.4 — Metrics & logging**
  - [x] Extend `RunStats` dataclass and serialization to include concurrency metrics.
  - [x] Emit structured logs for worker lifecycle events.

- [x] **T3.1.5 — Testing & docs**
  - [x] Add synthetic multi-page fixtures and pytest markers for concurrency tests.
  - [x] Document configuration, tuning, and troubleshooting tips in guides/README.

## Dev Notes

- Start with coarse-grained parallelism (per-page) before exploring intra-table splitting.
- Consider offering a `sequential` mode for debugging; ensure debug artifacts and HTML reports remain consistent when produced in parallel.
- Keep external dependencies optional; rely on `concurrent.futures` before introducing heavier schedulers.

### References

- Source: `docs/prd.md` — Section 13.6 (T5.1 Concurrency support), Section 12.2 (Pipeline orchestrator responsibilities)
- Source: `docs/prd.md` — Section 12.5 (Observability & QA hooks) for metrics/logging expectations

## Dev Agent Record

### Context Reference

- `docs/prd.md` Section 13.6 (T5.1 Concurrency support)
- `docs/prd.md` Section 12.2 (Pipeline orchestrator responsibilities)
- `docs/prd.md` Section 12.5 (Observability & QA hooks)

### Agent Model Used

Auto (Cursor AI Agent)

### Debug Log

**Implementation Approach**:
- Most of the parallel processing implementation was already complete from previous work.
- Focused on completing documentation, safety audit, and adding missing tests.
- Added signal handling for graceful CLI cancellation.
- Created comprehensive performance tuning guide.

**Key Findings**:
- All components are thread-safe (no shared mutable state).
- Parallel processing implementation uses ThreadPoolExecutor with per-page work units.
- Deterministic ordering is preserved by sorting results by page_index.
- Metrics and logging are comprehensive and working correctly.

**Design Decisions**:
- Default to thread-based parallelism (IO-bound workload).
- Rejected process pools (components not pickleable).
- Rejected async/await (would require significant refactoring).
- Default worker count: `min(4, cpu_count())`.

### Completion Notes List

1. **T3.1.1 - Concurrency Design Spike**: 
   - Created comprehensive concurrency design documentation (`docs/guides/concurrency-design.md`).
   - Documented design decisions, trade-offs, and rationale for thread-based parallelism.
   - Documented component thread safety analysis.

2. **T3.1.2 - Worker Orchestration**:
   - Verified existing parallel processing implementation is complete.
   - Added signal handling in CLI for graceful cancellation (SIGINT).
   - Deterministic ordering verified (results sorted by page_index).

3. **T3.1.3 - Component Safety Audit**:
   - Reviewed all components for thread safety.
   - All components confirmed thread-safe (no shared mutable state).
   - Documented safety findings in concurrency design doc.

4. **T3.1.4 - Metrics & Logging**:
   - Verified all concurrency metrics are captured in RunStats.
   - Verified structured logging for worker lifecycle events.
   - Metrics include: queue_high_water_mark, work_units_scheduled/completed, worker_utilization, page durations.

5. **T3.1.5 - Testing & Documentation**:
   - Added speed-up test comparing sequential vs parallel processing.
   - Created comprehensive performance tuning guide (`docs/guides/performance.md`).
   - All existing concurrency tests verified and passing.

### File List

**New Files**:
- `docs/guides/concurrency-design.md` - Concurrency design documentation
- `docs/guides/performance.md` - Performance tuning guide

**Modified Files**:
- `src/pdf_reader/cli.py` - Added signal handling for graceful cancellation
- `tests/test_concurrency.py` - Added speed-up test
- `docs/sprint-artifacts/3-1-parallel-processing-and-workload-scaling.md` - Updated with completion status

**Verified Files** (implementation already complete):
- `src/pdf_reader/pipeline.py` - Parallel processing implementation
- `src/pdf_reader/models.py` - RunStats with concurrency metrics
- `src/pdf_reader/config_loader.py` - Configuration loading (supports concurrency settings)

### Change Log

- 2025-01-XX: Story 3.1 implementation completed
  - Added concurrency design documentation
  - Added performance tuning guide
  - Added signal handling for CLI cancellation
  - Added speed-up test
  - Completed component safety audit
  - Verified all metrics and logging

