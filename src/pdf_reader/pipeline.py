from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional, Sequence, Union

from .debug_artifacts import draw_table_overlay, generate_html_report
from .detection import GridStructureDetector, TableRegionDetector
from .detection.line_detection import LineDetectionConfig
from .extraction import CellTextExtractor, TableAssembler
from .ingestion import PdfIngestionError, PdfIngestionService, PageImage
from .llm_extraction import LLMExtractionService, MockLLMExtractionService, OpenAIExtractionService
from .logging_config import LogFormat, get_logger, log_with_context, setup_logging
from .models import ExtractionResult, PdfDocument, RunStats, TableDataFrameSpec, TableMetadata, TableRegion, TableGrid
from .strategies import HeuristicExtractionStrategy, GeminiEndToEndStrategy, PageExtractionStrategy
from .manifest import create_run_manifest, ComponentVersion


PdfInput = Union[str, Path, bytes]


@dataclass
class PipelineConfig:
    """Configuration for the end-to-end table extraction pipeline.

    This configuration class consolidates all pipeline settings including input/output,
    processing parameters, LLM fallback, logging, and debug artifacts.

    Configuration can be loaded from multiple sources (CLI, config files, environment
    variables) with a clear priority order. See `config_loader.create_config()` for details.

    Attributes:
        input_path: Path to input PDF file. Can be set via CLI or config file.
        page_indices: List of page indices to process (0-based). None processes all pages.
        dpi: Rendering DPI for page images. Higher values improve quality but slow processing.
            Default: 200.
        extraction_preset: Quick configuration preset. Default: "smart".
            - "smart": FREE Gemini 2.5 Pro with conservative 3.0 escalation (recommended)
            - "premium": Always use paid Gemini 3.0 Pro for best quality
            - "offline": Heuristics only, no API calls
        extraction_strategy: Strategy to use for extraction ("heuristic" or "llm_end_to_end").
            Default: "llm_end_to_end" (uses FREE Gemini 2.5 Pro).
        default_rows: Default number of rows for grid detection. Default: 2.
        default_cols: Default number of columns for grid detection. Default: 3.
        ocr_confidence_threshold: Confidence threshold (0.0-1.0) below which LLM fallback
            is triggered. Default: 0.5.
        llm_fallback_enabled: Enable LLM fallback for low-confidence cells. Default: False.
        llm_provider: LLM provider name (e.g., "google", "openai"). Default: "google".
        llm_model: Primary LLM model name. Default: "gemini-2.5-pro" (FREE).
        llm_model_escalation: Fallback model for failed extractions. Default: "gemini-3.0-pro" (PAID).
        llm_api_key: API key for LLM provider. Recommended to set via environment variable
            (PDF_READER_LLM_API_KEY) for security. Default: None.
        enable_auto_escalation: Auto-escalate to premium model on failures. Default: False
            (conservative to avoid unexpected costs).
        llm_consistency_attempts: Number of times to run LLM extraction for consensus (1-5).
            Default: 1.
        llm_consistency_threshold: Required agreement ratio (0.0-1.0) to accept result.
            Default: 0.8.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: "INFO".
        log_file: Optional path to log file. If None, logs go to console. Default: None.
        log_format: Log format ("json" or "human"). Default: "human".
        enable_debug_artifacts: Enable debug visualization (overlay images and HTML report).
            Default: False.
        debug_output_dir: Directory for debug artifacts. Default: "debug_output".
        generate_overlays: Generate overlay images when debug enabled. Default: True.
        generate_html_report: Generate HTML report when debug enabled. Default: True.
        worker_type: Concurrency strategy ("sequential", "thread", "process", "async").
            Default: "thread".
        max_workers: Maximum number of workers to use for concurrent page processing.
            Defaults to a heuristic based on CPU count when None.
        page_batch_size: Number of rendered pages that may be queued before applying
            back-pressure. Default: 4.
        max_inflight_pages: Hard ceiling for concurrently queued pages. Defaults to
            page_batch_size when None.
        run_timeout_seconds: Optional timeout for the entire run. When exceeded, the run
            aborts gracefully and returns partial results.
        enable_irregular_structure_detection: Enable heuristics for partially bordered
            or ragged tables. Default: False.
        ragged_mode: Normalization strategy for ragged tables ("strict" pads aggressively,
            "ragged" keeps filler markers). Default: "strict".
        ragged_fill_value: Optional filler token for missing cells when ragged mode is enabled.
        enable_section_detection: Enable detection of multi-panel/stacked tables. Default: False.
        # Line detection configuration
        enable_line_detection: bool = True
        line_detection_min_length: int = 40
        line_detection_gap_tolerance: int = 5
        line_detection_morph_iterations: int = 2
        line_detection_min_separation: int = 5

    Example:
        >>> config = PipelineConfig(
        ...     input_path="document.pdf",
        ...     dpi=300,
        ...     enable_debug_artifacts=True,
        ... )
        >>> runner = PipelineRunner()
        >>> result = runner.extract_tables("document.pdf", config=config)
    """

    input_path: Optional[Path] = None
    page_indices: Optional[Sequence[int]] = None  # None = all pages
    dpi: int = 200
    # Extraction preset (quick config)
    extraction_preset: Literal["smart", "premium", "offline"] = "smart"
    # Extraction strategy
    extraction_strategy: Literal["heuristic", "llm_end_to_end"] = "llm_end_to_end"
    default_rows: int = 2
    default_cols: int = 3
    # LLM configuration (FREE Gemini 2.5 Pro by default!)
    ocr_confidence_threshold: float = 0.5
    llm_fallback_enabled: bool = False
    llm_provider: Optional[str] = "google"  # Default to Google for Gemini
    llm_model: Optional[str] = "gemini-2.5-pro"  # FREE tier model
    llm_model_escalation: Optional[str] = "gemini-3.0-pro"  # PAID escalation model
    llm_api_key: Optional[str] = None  # API key for LLM provider
    enable_auto_escalation: Optional[bool] = None  # Conservative: don't auto-spend money (None = use preset default)
    llm_consistency_attempts: int = 1
    llm_consistency_threshold: float = 0.8
    # Position verification configuration (disabled by default for scanned PDFs)
    enable_position_verification: bool = False  # Verify extracted values against OCR for position accuracy
    position_verification_threshold: float = 0.7  # Minimum confidence to accept without warning
    position_search_radius: float = 50.0  # Pixels to search for OCR matches
    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_format: LogFormat = "human"
    # Debug artifacts configuration
    enable_debug_artifacts: bool = False
    debug_output_dir: str = "debug_output"
    generate_overlays: bool = True
    generate_html_report: bool = True
    # Concurrency configuration
    worker_type: Literal["sequential", "thread", "process", "async"] = "thread"
    max_workers: Optional[int] = None
    page_batch_size: int = 4
    max_inflight_pages: Optional[int] = None
    run_timeout_seconds: Optional[float] = None
    # Irregular structure configuration
    enable_irregular_structure_detection: bool = False
    ragged_mode: Literal["strict", "ragged"] = "strict"
    ragged_fill_value: Optional[str] = None
    enable_section_detection: bool = False
    # Line detection configuration
    enable_line_detection: bool = True
    line_detection_min_length: int = 40
    line_detection_gap_tolerance: int = 5
    line_detection_morph_iterations: int = 2
    line_detection_min_separation: int = 5

    def __post_init__(self) -> None:
        """Validate configuration values and apply preset defaults."""
        # Apply preset configurations first
        self._apply_preset()
        
        worker_value = (self.worker_type or "thread").lower()
        object.__setattr__(self, "worker_type", worker_value)
        if not (0.0 <= self.ocr_confidence_threshold <= 1.0):
            raise ValueError(
                f"ocr_confidence_threshold must be between 0.0 and 1.0, got {self.ocr_confidence_threshold}"
            )
        if self.max_workers is not None and self.max_workers <= 0:
            raise ValueError("max_workers must be positive when provided")
        if self.page_batch_size <= 0:
            raise ValueError("page_batch_size must be positive")
        if self.max_inflight_pages is not None and self.max_inflight_pages <= 0:
            raise ValueError("max_inflight_pages must be positive when provided")
        if self.run_timeout_seconds is not None and self.run_timeout_seconds <= 0:
            raise ValueError("run_timeout_seconds must be positive when provided")
        if self.line_detection_min_separation < 0:
            raise ValueError("line_detection_min_separation must be non-negative")
        if self.llm_consistency_attempts < 1:
            raise ValueError("llm_consistency_attempts must be at least 1")
        if not (0.0 <= self.llm_consistency_threshold <= 1.0):
            raise ValueError(
                f"llm_consistency_threshold must be between 0.0 and 1.0, got {self.llm_consistency_threshold}"
            )

        valid_presets = {"smart", "premium", "offline"}
        if self.extraction_preset not in valid_presets:
            raise ValueError(
                f"extraction_preset must be one of {sorted(valid_presets)}, got {self.extraction_preset}"
            )
        
        valid_ragged_modes = {"strict", "ragged"}
        if self.ragged_mode not in valid_ragged_modes:
            raise ValueError(
                f"ragged_mode must be one of {sorted(valid_ragged_modes)}, got {self.ragged_mode}"
            )
        
        valid_strategies = {"heuristic", "llm_end_to_end"}
        if self.extraction_strategy not in valid_strategies:
            raise ValueError(
                 f"extraction_strategy must be one of {sorted(valid_strategies)}, got {self.extraction_strategy}"
            )

        valid_worker_types = {"sequential", "thread", "process", "async"}
        if worker_value not in valid_worker_types:
            raise ValueError(
                f"worker_type must be one of {sorted(valid_worker_types)}, got {worker_value}"
            )
        if worker_value in {"process", "async"}:
            raise ValueError(
                "worker_type 'process' or 'async' is not supported because core detectors "
                "and page images are not pickleable for cross-process execution. "
                "Use 'thread' or 'sequential'."
            )
        # Create debug output directory if artifacts are enabled
        if self.enable_debug_artifacts:
            output_path = Path(self.debug_output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

    def _apply_preset(self) -> None:
        """Apply preset configurations to set sensible defaults.
        
        Presets:
        - "smart": FREE Gemini 2.5 Pro, no auto-escalation (default)
        - "premium": PAID Gemini 3.0 Pro always, best quality
        - "offline": Heuristics only, no API calls
        """
        if self.extraction_preset == "smart":
            # Smart preset: FREE Gemini 2.5 Pro, conservative escalation
            object.__setattr__(self, "extraction_strategy", "llm_end_to_end")
            if self.llm_provider is None:
                object.__setattr__(self, "llm_provider", "google")
            if self.llm_model is None:
                object.__setattr__(self, "llm_model", "gemini-2.5-pro")
            if self.llm_model_escalation is None:
                object.__setattr__(self, "llm_model_escalation", "gemini-3.0-pro")
            # Conservative: don't auto-escalate without user consent (only if not explicitly set)
            if self.enable_auto_escalation is None:
                object.__setattr__(self, "enable_auto_escalation", False)
            
        elif self.extraction_preset == "premium":
            # Premium preset: PAID Gemini 3.0 Pro always
            object.__setattr__(self, "extraction_strategy", "llm_end_to_end")
            if self.llm_provider is None:
                object.__setattr__(self, "llm_provider", "google")
            # Always set model to 3.0 Pro for premium (override default)
            object.__setattr__(self, "llm_model", "gemini-3.0-pro")
            # No escalation needed, already using best model
            object.__setattr__(self, "llm_model_escalation", None)
            if self.enable_auto_escalation is None:
                object.__setattr__(self, "enable_auto_escalation", False)
            
        elif self.extraction_preset == "offline":
            # Offline preset: Heuristics only, no API calls
            object.__setattr__(self, "extraction_strategy", "heuristic")
            object.__setattr__(self, "llm_fallback_enabled", False)
            if self.enable_auto_escalation is None:
                object.__setattr__(self, "enable_auto_escalation", False)
        
        # Final fallback: if still None, default to False (conservative)
        if self.enable_auto_escalation is None:
            object.__setattr__(self, "enable_auto_escalation", False)


@dataclass
class PageProcessingResult:
    """Structured result for a single page processed by a worker."""

    page_index: int
    tables: List[TableDataFrameSpec] = field(default_factory=list)
    metadata: List[TableMetadata] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    tables_detected: int = 0
    tables_extracted: int = 0
    tables_failed: int = 0
    cells_with_text: int = 0
    total_cells: int = 0
    llm_fallback_count: int = 0
    confidence_sum: float = 0.0
    confidence_count: int = 0
    page_duration_ms: float = 0.0
    overlay_path: Optional[Path] = None
    page_skipped: bool = False
    # Cost tracking (per-page)
    llm_calls_primary: int = 0
    llm_calls_escalation: int = 0
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    model_used: Optional[str] = None


@dataclass
class PipelineRunner:
    """End-to-end orchestrator for PDF table extraction.

    This class coordinates all pipeline components to extract tables from PDF documents.
    It handles multi-page processing, error recovery, logging, metrics collection, and
    debug artifact generation.

    Components can be customized by replacing the default instances:
    - `ingestion`: PDF loading and page rendering
    - `region_detector`: Table region detection
    - `grid_detector`: Grid structure construction
    - `text_extractor`: Cell text extraction (OCR + optional LLM fallback)
    - `assembler`: Table assembly into dataframe-ready format

    Attributes:
        ingestion: Service for loading PDFs and rendering pages.
        region_detector: Detector for finding table regions on pages.
        grid_detector: Detector for building grid structures from regions.
        text_extractor: Extractor for populating cell text content.
        assembler: Assembler for converting grids to dataframe specs.

    Example:
        >>> runner = PipelineRunner()
        >>> config = PipelineConfig(input_path="document.pdf")
        >>> result = runner.extract_tables("document.pdf", config=config)
        >>> print(f"Extracted {result.run_stats.tables_extracted} tables")
    """

    ingestion: PdfIngestionService = field(default_factory=PdfIngestionService)
    region_detector: TableRegionDetector = field(default_factory=TableRegionDetector)
    grid_detector: GridStructureDetector = field(default_factory=GridStructureDetector)
    text_extractor: CellTextExtractor = field(default_factory=CellTextExtractor)
    assembler: TableAssembler = field(default_factory=TableAssembler)

    def _create_llm_service(self, config: PipelineConfig) -> Optional[LLMExtractionService]:
        """Create LLM extraction service from config if enabled."""
        if not config.llm_fallback_enabled:
            return None

        if config.llm_provider == "openai" or (config.llm_provider is None and config.llm_api_key):
            if not config.llm_api_key:
                raise ValueError("llm_api_key required when llm_fallback_enabled=True")
            model = config.llm_model or "gpt-4o"
            return OpenAIExtractionService(api_key=config.llm_api_key, model=model)

        return None

    def _resolve_worker_settings(
        self, config: PipelineConfig
    ) -> tuple[str, int, int]:
        """Determine worker type, worker count, and inflight queue size."""
        worker_type = config.worker_type
        cpu_default = os.cpu_count() or 4
        default_workers = max(1, min(4, cpu_default))
        requested_workers = config.max_workers or default_workers

        if worker_type == "sequential":
            requested_workers = 1
        elif requested_workers <= 1:
            worker_type = "sequential"
            requested_workers = 1

        max_inflight = config.max_inflight_pages or max(
            config.page_batch_size, requested_workers
        )
        return worker_type, requested_workers, max_inflight

    def _process_page(
        self,
        page_index: int,
        page_image: PageImage,
        config: PipelineConfig,
        logger: logging.Logger,
        cancel_event: threading.Event,
        page_obj: Optional[Any] = None,
    ) -> PageProcessingResult:
        """Process a single page and return structured results.
        
        Args:
            page_index: Zero-based page index
            page_image: PIL Image of the page
            config: Pipeline configuration
            logger: Logger instance
            cancel_event: Threading event for cancellation
            page_obj: Optional pdfplumber page object for OCR token extraction
        """
        
        strategy: PageExtractionStrategy
        
        if config.extraction_strategy == "heuristic":
            strategy = HeuristicExtractionStrategy(
                region_detector=self.region_detector,
                grid_detector=self.grid_detector,
                text_extractor=self.text_extractor,
                assembler=self.assembler
            )
        elif config.extraction_strategy == "llm_end_to_end":
            strategy = GeminiEndToEndStrategy()
        else:
            raise ValueError(f"Unknown extraction strategy: {config.extraction_strategy}")
            
        return strategy.process_page(
            page_index=page_index,
            page_image=page_image,
            config=config,
            logger=logger,
            cancel_event=cancel_event,
            page_obj=page_obj
        )

    def _process_pages_sequential(
        self,
        page_indices: List[int],
        document: PdfDocument,
        config: PipelineConfig,
        logger: logging.Logger,
        cancel_event: threading.Event,
    ) -> List[PageProcessingResult]:
        """Process pages sequentially (one at a time).
        
        Args:
            page_indices: List of page indices to process.
            document: Loaded PDF document.
            config: Pipeline configuration.
            logger: Logger instance.
            cancel_event: Threading event for cancellation.
            
        Returns:
            List of PageProcessingResult objects, one per page.
        """
        results: List[PageProcessingResult] = []
        
        for page_index in page_indices:
            if cancel_event.is_set():
                logger.warning("Cancellation requested, stopping page processing")
                break
                
            try:
                page_image = self.ingestion.render_page(page_index, dpi=config.dpi)
                
                # Get pdfplumber page object for position verification
                page_obj = None
                if self.ingestion._pdf is not None:
                    page_obj = self.ingestion._pdf.pages[page_index]
                    
            except PdfIngestionError as exc:
                error_result = PageProcessingResult(page_index=page_index, page_skipped=True)
                error_result.errors.append(f"Page {page_index}: {exc}")
                results.append(error_result)
                continue
            except Exception as exc:
                error_result = PageProcessingResult(page_index=page_index, page_skipped=True)
                error_result.errors.append(f"Page {page_index}: Unexpected error during rendering: {exc}")
                results.append(error_result)
                continue
            
            # Process the page using the existing _process_page method
            page_result = self._process_page(
                page_index, page_image, config, logger, cancel_event, page_obj
            )
            results.append(page_result)
        
        return results

    def _process_pages_parallel(
        self,
        page_indices: List[int],
        document: PdfDocument,
        config: PipelineConfig,
        logger: logging.Logger,
        cancel_event: threading.Event,
        num_workers: int,
        max_inflight: int,
        stats: RunStats,
    ) -> List[PageProcessingResult]:
        """Process pages in parallel using a thread pool.
        
        This method uses ThreadPoolExecutor to process multiple pages concurrently.
        Results are collected and sorted by page_index to ensure deterministic ordering.
        
        Args:
            page_indices: List of page indices to process.
            document: Loaded PDF document.
            config: Pipeline configuration.
            logger: Logger instance.
            cancel_event: Threading event for cancellation.
            num_workers: Number of worker threads.
            max_inflight: Maximum number of pages to queue before applying back-pressure.
            stats: RunStats object to update with concurrency metrics.
            
        Returns:
            List of PageProcessingResult objects, one per page (sorted by page_index).
        """
        results: List[PageProcessingResult] = []
        futures: Dict[Future[PageProcessingResult], int] = {}
        
        # Track queue depth for metrics
        queue_high_water_mark = 0
        work_units_scheduled = 0
        work_units_completed = 0
        
        log_with_context(
            logger,
            logging.INFO,
            "Starting parallel page processing",
            num_workers=num_workers,
            max_inflight=max_inflight,
            total_pages=len(page_indices),
        )
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit initial batch of work
            for page_index in page_indices:
                if cancel_event.is_set():
                    break
                    
                # Apply back-pressure: wait if queue is too full
                while len(futures) >= max_inflight and not cancel_event.is_set():
                    # Wait for at least one future to complete
                    done, not_done = wait(futures.keys(), return_when=FIRST_COMPLETED, timeout=0.1)
                    for future in done:
                        try:
                            result = future.result()
                            results.append(result)
                            work_units_completed += 1
                        except Exception as exc:
                            # Worker crashed - create error result
                            page_idx = futures.pop(future, -1)
                            error_result = PageProcessingResult(page_index=page_idx, page_skipped=True)
                            error_result.errors.append(f"Worker error: {exc}")
                            results.append(error_result)
                            work_units_completed += 1
                            log_with_context(
                                logger,
                                logging.ERROR,
                                "Worker failed",
                                page_index=page_idx,
                                error=str(exc),
                            )
                        del futures[future]
                
                if cancel_event.is_set():
                    break
                
                # Submit work for this page
                future = executor.submit(self._process_page_worker, page_index, document, config, logger, cancel_event)
                futures[future] = page_index
                work_units_scheduled += 1
                queue_high_water_mark = max(queue_high_water_mark, len(futures))
                
                log_with_context(
                    logger,
                    logging.DEBUG,
                    "Submitted page for processing",
                    page_index=page_index,
                    queue_depth=len(futures),
                )
            
            # Wait for all remaining futures to complete
            while futures and not cancel_event.is_set():
                done, not_done = wait(futures.keys(), return_when=FIRST_COMPLETED, timeout=1.0)
                for future in done:
                    try:
                        result = future.result()
                        results.append(result)
                        work_units_completed += 1
                    except Exception as exc:
                        page_idx = futures.pop(future, -1)
                        error_result = PageProcessingResult(page_index=page_idx, page_skipped=True)
                        error_result.errors.append(f"Worker error: {exc}")
                        results.append(error_result)
                        work_units_completed += 1
                        log_with_context(
                            logger,
                            logging.ERROR,
                            "Worker failed",
                            page_index=page_idx,
                            error=str(exc),
                        )
                    del futures[future]
        
        # Update concurrency metrics
        stats.queue_high_water_mark = queue_high_water_mark
        stats.work_units_scheduled = work_units_scheduled
        stats.work_units_completed = work_units_completed
        
        log_with_context(
            logger,
            logging.INFO,
            "Parallel processing completed",
            pages_processed=len(results),
            queue_high_water_mark=queue_high_water_mark,
            work_units_scheduled=work_units_scheduled,
            work_units_completed=work_units_completed,
        )
        
        return results

    def _process_page_worker(
        self,
        page_index: int,
        document: PdfDocument,
        config: PipelineConfig,
        logger: logging.Logger,
        cancel_event: threading.Event,
    ) -> PageProcessingResult:
        """Worker function for processing a single page in parallel execution.
        
        This method is called by the thread pool executor. It handles page rendering
        and delegates to _process_page for the actual processing.
        
        Args:
            page_index: Index of the page to process.
            document: Loaded PDF document (not used directly, but needed for type signature).
            config: Pipeline configuration.
            logger: Logger instance.
            cancel_event: Threading event for cancellation.
            
        Returns:
            PageProcessingResult for the processed page.
        """
        log_with_context(
            logger,
            logging.DEBUG,
            "Worker starting page processing",
            page_index=page_index,
            thread_id=threading.current_thread().ident,
        )
        
        try:
            page_image = self.ingestion.render_page(page_index, dpi=config.dpi)
        except PdfIngestionError as exc:
            error_result = PageProcessingResult(page_index=page_index, page_skipped=True)
            error_result.errors.append(f"Page {page_index}: {exc}")
            return error_result
        except Exception as exc:
            error_result = PageProcessingResult(page_index=page_index, page_skipped=True)
            error_result.errors.append(f"Page {page_index}: Unexpected error during rendering: {exc}")
            return error_result
        
        # Process the page
        result = self._process_page(page_index, page_image, config, logger, cancel_event)
        
        log_with_context(
            logger,
            logging.DEBUG,
            "Worker completed page processing",
            page_index=page_index,
            thread_id=threading.current_thread().ident,
            duration_ms=result.page_duration_ms,
        )
        
        return result

    def extract_tables(
        self,
        pdf_input: PdfInput,
        config: Optional[PipelineConfig] = None,
    ) -> ExtractionResult:
        """Run the full pipeline on the given PDF input with configurable concurrency.

        This method supports sequential, thread-based, and (future) process-based execution.
        Pages are processed in parallel when worker_type is "thread", with deterministic
        output ordering preserved by sorting results by page_index.

        Args:
            pdf_input: PDF file path, Path object, or bytes.
            config: Optional pipeline configuration. If None, uses defaults.

        Returns:
            ExtractionResult containing extracted tables, metadata, and run statistics.
        """
        cfg = config or PipelineConfig(
            input_path=Path(pdf_input) if isinstance(pdf_input, (str, Path)) else None
        )

        # Set up logging
        setup_logging(
            log_level=cfg.log_level,
            log_file=cfg.log_file,
            log_format=cfg.log_format,
        )
        logger = get_logger("PipelineRunner")

        # Start timing
        start_time = time.time()

        # Log pipeline start
        input_path_str = str(cfg.input_path) if cfg.input_path else "bytes"
        log_with_context(
            logger,
            logging.INFO,
            "Starting table extraction pipeline",
            input_path=input_path_str,
            dpi=cfg.dpi,
            page_indices=cfg.page_indices,
            worker_type=cfg.worker_type,
            extraction_strategy=cfg.extraction_strategy,
        )

        result = ExtractionResult()
        stats = RunStats(run_id=str(uuid.uuid4()))

        # Create cancellation event for cooperative cancellation
        cancel_event = threading.Event()
        
        # Set up timeout if configured
        timeout_timer: Optional[threading.Timer] = None
        if cfg.run_timeout_seconds is not None:
            def timeout_handler():
                logger.warning(
                    f"Run timeout ({cfg.run_timeout_seconds}s) exceeded, cancelling processing"
                )
                cancel_event.set()
                stats.abort_reason = f"Timeout after {cfg.run_timeout_seconds} seconds"
            
            timeout_timer = threading.Timer(cfg.run_timeout_seconds, timeout_handler)
            timeout_timer.start()
            log_with_context(
                logger,
                logging.INFO,
                "Timeout configured",
                timeout_seconds=cfg.run_timeout_seconds,
            )

        try:
            document = self.ingestion.load_pdf(pdf_input)
            log_with_context(
                logger, logging.INFO, "PDF loaded successfully", page_count=document.page_count
            )
        except PdfIngestionError as exc:
            log_with_context(logger, logging.ERROR, "Failed to load PDF", error=str(exc))
            stats.errors.append(str(exc))
            result.run_stats = stats
            return result

        # Determine which pages to process
        if cfg.page_indices is None:
            page_indices = list(range(document.page_count))
        else:
            page_indices = list(cfg.page_indices)
            # Validate page indices are within bounds
            for idx in page_indices:
                if idx < 0 or idx >= document.page_count:
                    stats.errors.append(
                        f"Page index {idx} out of range "
                        f"(valid: 0..{document.page_count - 1})"
                    )
            # Filter out invalid indices
            page_indices = [idx for idx in page_indices if 0 <= idx < document.page_count]

        stats.pages_processed = len(page_indices)
        log_with_context(
            logger,
            logging.INFO,
            "Processing pages",
            pages_to_process=len(page_indices),
            total_pages=document.page_count,
        )

        # Resolve worker settings
        worker_type, num_workers, max_inflight = self._resolve_worker_settings(cfg)
        stats.worker_type = worker_type
        stats.max_workers_used = num_workers

        # Track metrics for computation
        all_confidences: List[float] = []
        total_cells = 0

        # Track data for debug artifacts
        debug_data: List[tuple[int, Image.Image, List[TableRegion], List[TableGrid]]] = []
        overlay_image_paths: List[Path] = []

        # Process pages based on worker type
        if worker_type == "sequential":
            # Sequential processing (original implementation path)
            page_results = self._process_pages_sequential(
                page_indices, document, cfg, logger, cancel_event
            )
        elif worker_type == "thread":
            # Thread-based parallel processing
            page_results = self._process_pages_parallel(
                page_indices, document, cfg, logger, cancel_event, num_workers, max_inflight, stats
            )
        else:
            # Should not reach here due to validation, but defensive fallback
            log_with_context(
                logger,
                logging.WARNING,
                "Unsupported worker type, falling back to sequential",
                worker_type=worker_type,
            )
            page_results = self._process_pages_sequential(
                page_indices, document, cfg, logger, cancel_event
            )

        # Sort results by page_index to ensure deterministic ordering
        page_results.sort(key=lambda r: r.page_index)

        # Aggregate results from all pages
        for page_result in page_results:
            # Aggregate page-level metrics
            stats.pages_skipped += 1 if page_result.page_skipped else 0
            stats.tables_detected += page_result.tables_detected
            stats.tables_extracted += page_result.tables_extracted
            stats.tables_failed += page_result.tables_failed
            stats.total_cells_extracted += page_result.cells_with_text
            total_cells += page_result.total_cells
            stats.llm_fallback_count += page_result.llm_fallback_count
            # Track confidence sum and count for average calculation
            if page_result.confidence_count > 0:
                # We'll compute average from sum/count at the end
                # For now, just track that we have confidences
                pass
            stats.errors.extend(page_result.errors)
            
            # Aggregate cost tracking
            stats.llm_calls_primary += page_result.llm_calls_primary
            stats.llm_calls_escalation += page_result.llm_calls_escalation
            stats.llm_tokens_input += page_result.llm_tokens_input
            stats.llm_tokens_output += page_result.llm_tokens_output
            if page_result.model_used and page_result.model_used not in stats.models_used:
                stats.models_used.append(page_result.model_used)

            # Add tables and metadata from this page
            for table_spec, table_meta in zip(page_result.tables, page_result.metadata):
                result.add_table(table_spec, table_meta)

            # Track overlay paths for HTML report
            if page_result.overlay_path:
                overlay_image_paths.append(page_result.overlay_path)

            # Track page durations for metrics
            if page_result.page_duration_ms > 0:
                if stats.max_page_duration_ms == 0:
                    stats.min_page_duration_ms = page_result.page_duration_ms
                stats.max_page_duration_ms = max(
                    stats.max_page_duration_ms, page_result.page_duration_ms
                )
                stats.min_page_duration_ms = min(
                    stats.min_page_duration_ms, page_result.page_duration_ms
                )

        # Compute final run-level metrics
        total_duration = (time.time() - start_time) * 1000
        stats.total_duration_ms = total_duration
        
        # Calculate average confidence from page results
        total_confidence_sum = sum(
            r.confidence_sum for r in page_results if r.confidence_count > 0
        )
        total_confidence_count = sum(
            r.confidence_count for r in page_results if r.confidence_count > 0
        )
        stats.average_ocr_confidence = (
            total_confidence_sum / total_confidence_count if total_confidence_count > 0 else 0.0
        )
        
        # Calculate estimated cost (if LLM was used)
        if stats.llm_tokens_input > 0 or stats.llm_tokens_output > 0:
            # Import here to avoid circular dependency
            from .strategies import GeminiEndToEndStrategy
            
            # Calculate cost based on which models were used
            # Use the most expensive model for conservative estimate
            primary_model = cfg.llm_model or "gemini-2.5-pro"
            escalation_model = cfg.llm_model_escalation or "gemini-3.0-pro"
            
            # Estimate assuming primary model for most calls, escalation for remainder
            if stats.llm_calls_escalation > 0:
                # Mixed usage: calculate separately
                # Rough split: assume tokens are proportional to calls
                total_calls = stats.llm_calls_primary + stats.llm_calls_escalation
                primary_fraction = stats.llm_calls_primary / total_calls if total_calls > 0 else 1.0
                
                primary_tokens_in = int(stats.llm_tokens_input * primary_fraction)
                primary_tokens_out = int(stats.llm_tokens_output * primary_fraction)
                escalation_tokens_in = stats.llm_tokens_input - primary_tokens_in
                escalation_tokens_out = stats.llm_tokens_output - primary_tokens_out
                
                cost_primary = GeminiEndToEndStrategy.estimate_cost(
                    primary_tokens_in, primary_tokens_out, primary_model
                )
                cost_escalation = GeminiEndToEndStrategy.estimate_cost(
                    escalation_tokens_in, escalation_tokens_out, escalation_model
                )
                stats.estimated_cost_usd = cost_primary + cost_escalation
            else:
                # Only primary model used
                stats.estimated_cost_usd = GeminiEndToEndStrategy.estimate_cost(
                    stats.llm_tokens_input, stats.llm_tokens_output, primary_model
                )
        
        # Calculate average page duration
        page_durations = [r.page_duration_ms for r in page_results if r.page_duration_ms > 0]
        if page_durations:
            stats.average_page_duration_ms = sum(page_durations) / len(page_durations)
        
        # Calculate worker utilization (for parallel execution)
        if worker_type == "thread" and num_workers > 1 and total_duration > 0:
            # Utilization = (sum of all page durations) / (total time * num_workers)
            total_work_time = sum(page_durations)
            stats.worker_utilization = min(
                1.0, total_work_time / (total_duration * num_workers) if num_workers > 0 else 0.0
            )

        # Cancel timeout timer if still running
        if timeout_timer is not None:
            timeout_timer.cancel()
        
        # If we were cancelled due to timeout, log it
        if cancel_event.is_set() and stats.abort_reason:
            log_with_context(
                logger,
                logging.WARNING,
                "Pipeline aborted",
                reason=stats.abort_reason,
            )

        result.run_stats = stats

        # Log pipeline summary
        log_with_context(
            logger,
            logging.INFO,
            "Pipeline execution completed",
            pages_processed=stats.pages_processed,
            pages_skipped=stats.pages_skipped,
            tables_detected=stats.tables_detected,
            tables_extracted=stats.tables_extracted,
            tables_failed=stats.tables_failed,
            total_cells_extracted=stats.total_cells_extracted,
            llm_fallback_count=stats.llm_fallback_count,
            average_ocr_confidence=stats.average_ocr_confidence,
            total_duration_ms=total_duration,
            error_count=len(stats.errors),
        )

        # Generate HTML report if debug artifacts are enabled
        if cfg.enable_debug_artifacts and cfg.generate_html_report:
            try:
                output_dir = Path(cfg.debug_output_dir)
                report_path = output_dir / "extraction_report.html"
                config_summary = {
                    "DPI": cfg.dpi,
                    "Page Indices": cfg.page_indices if cfg.page_indices else "All pages",
                    "Default Rows": cfg.default_rows,
                    "Default Cols": cfg.default_cols,
                    "LLM Fallback": cfg.llm_fallback_enabled,
                }
                generate_html_report(
                    result,
                    input_path_str,
                    config_summary,
                    report_path,
                    overlay_image_paths if cfg.generate_overlays else None,
                )
                log_with_context(
                    logger,
                    logging.INFO,
                    "Generated HTML report",
                    report_path=str(report_path),
                )
            except Exception as exc:
                # Log error but don't fail the pipeline
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Failed to generate HTML report",
                    error=str(exc),
                )

        # Generate run manifest for reproducibility
        try:
            components = []
            
            # Add detector component
            components.append(ComponentVersion(
                name="TableRegionDetector",
                version="1.0",
                type="detector",
                metadata={"method": "morphological_operations"}
            ))
            
            # Add grid detector component
            components.append(ComponentVersion(
                name="GridStructureDetector",
                version="1.0",
                type="detector",
                metadata={
                    "line_detection_enabled": cfg.enable_line_detection,
                    "irregular_detection_enabled": cfg.enable_irregular_structure_detection,
                }
            ))
            
            # Add extraction strategy component
            components.append(ComponentVersion(
                name=f"{cfg.extraction_strategy}_strategy",
                version="1.0",
                type="extraction_strategy",
                metadata={"strategy": cfg.extraction_strategy}
            ))
            
            # Add LLM component if used
            if cfg.llm_fallback_enabled or cfg.extraction_strategy == "llm_end_to_end":
                components.append(ComponentVersion(
                    name="LLMExtractionService",
                    version="1.0",
                    type="llm_provider",
                    metadata={
                        "provider": cfg.llm_provider or "unknown",
                        "model": cfg.llm_model or "unknown",
                        "fallback_enabled": cfg.llm_fallback_enabled,
                    }
                ))
            
            result.run_manifest = create_run_manifest(
                run_id=stats.run_id,
                config=cfg,
                components=components,
            )
            
            log_with_context(
                logger,
                logging.DEBUG,
                "Generated run manifest",
                run_id=stats.run_id,
                config_digest=result.run_manifest.config_digest,
            )
        except Exception as exc:
            # Log error but don't fail the pipeline
            log_with_context(
                logger,
                logging.WARNING,
                "Failed to generate run manifest",
                error=str(exc),
            )

        return result
