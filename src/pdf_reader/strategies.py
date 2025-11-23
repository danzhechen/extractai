from __future__ import annotations

import base64
import io
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from PIL import Image

from .debug_artifacts import draw_table_overlay
from .detection import GridStructureDetector, TableRegionDetector
from .detection.line_detection import LineDetectionConfig
from .extraction import CellTextExtractor, TableAssembler
from .ingestion import PageImage
from .logging_config import log_with_context
from .models import (
    BoundingBox,
    Cell,
    ColumnSpec,
    TableDataFrameSpec,
    TableGrid,
    TableMetadata,
    TableRegion,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .pipeline import PipelineConfig, PageProcessingResult


class PageExtractionStrategy(ABC):
    """Abstract base class for page extraction strategies."""

    @abstractmethod
    def process_page(
        self,
        page_index: int,
        page_image: PageImage,
        config: "PipelineConfig",
        logger: logging.Logger,
        cancel_event: threading.Event,
        page_obj: Optional[Any] = None,  # pdfplumber page object for OCR token extraction
    ) -> "PageProcessingResult":
        """Process a single page and return structured results.
        
        Args:
            page_index: Zero-based page index
            page_image: PIL Image of the page
            config: Pipeline configuration
            logger: Logger instance
            cancel_event: Threading event for cancellation
            page_obj: Optional pdfplumber page object for OCR token extraction
        """
        pass


class HeuristicExtractionStrategy(PageExtractionStrategy):
    """Standard heuristic extraction strategy (Detect -> Grid -> OCR)."""

    def __init__(
        self,
        region_detector: TableRegionDetector,
        grid_detector: GridStructureDetector,
        text_extractor: CellTextExtractor,
        assembler: TableAssembler,
    ):
        self.region_detector = region_detector
        self.grid_detector = grid_detector
        self.text_extractor = text_extractor
        self.assembler = assembler

    def process_page(
        self,
        page_index: int,
        page_image: PageImage,
        config: "PipelineConfig",
        logger: logging.Logger,
        cancel_event: threading.Event,
        page_obj: Optional[Any] = None,
    ) -> "PageProcessingResult":
        from .pipeline import PageProcessingResult

        page_start = time.time()
        page_result = PageProcessingResult(page_index=page_index)

        # Configure grid detector with line detection + irregular settings
        line_config = LineDetectionConfig(
            enable_line_detection=config.enable_line_detection,
            min_line_length=config.line_detection_min_length,
            gap_tolerance=config.line_detection_gap_tolerance,
            morph_iterations=config.line_detection_morph_iterations,
            min_line_separation=config.line_detection_min_separation,
        )
        
        local_grid_detector = GridStructureDetector(
            line_detection_config=line_config,
            enable_irregular_detection=config.enable_irregular_structure_detection,
            ragged_mode=config.ragged_mode,
            filler_token=config.ragged_fill_value,
        )

        if cancel_event.is_set():
            page_result.errors.append(
                f"Page {page_index}: cancelled before processing"
            )
            page_result.page_skipped = True
            return page_result

        log_with_context(logger, logging.DEBUG, "Processing page (Heuristic)", page_index=page_index)
        try:
            local_region_detector = self.region_detector
            if isinstance(self.region_detector, TableRegionDetector):
                # Create a fresh instance to avoid side effects
                local_region_detector = TableRegionDetector(
                    enable_multi_panel_detection=(
                        config.enable_irregular_structure_detection or config.enable_section_detection
                    ),
                    min_region_area_ratio=self.region_detector.min_region_area_ratio,
                    detection_kernel_size=self.region_detector.detection_kernel_size
                )
            else:
                local_region_detector = self.region_detector

            regions = local_region_detector.detect(page_image, page_index=page_index)
            
            log_with_context(
                logger,
                logging.DEBUG,
                "Table regions detected",
                page_index=page_index,
                region_count=len(regions),
            )
        except Exception as exc:
            page_result.page_skipped = True
            error_msg = f"Page {page_index}: Table detection failed: {exc}"
            page_result.errors.append(error_msg)
            log_with_context(
                logger,
                logging.WARNING,
                "Table detection failed",
                page_index=page_index,
                error=str(exc),
            )
            page_result.page_duration_ms = (time.time() - page_start) * 1000
            return page_result

        if not regions:
            log_with_context(
                logger, logging.DEBUG, "No tables found on page", page_index=page_index
            )
            page_result.page_duration_ms = (time.time() - page_start) * 1000
            return page_result

        page_grids: List[TableGrid] = []
        
        local_extractor = self.text_extractor
        if config.llm_fallback_enabled:
            from .llm_extraction import OpenAIExtractionService
            
            llm_service = None
            if config.llm_provider == "openai" or (config.llm_provider is None and config.llm_api_key):
                 if config.llm_api_key:
                    model = config.llm_model or "gpt-4o"
                    llm_service = OpenAIExtractionService(api_key=config.llm_api_key, model=model)
            
            local_extractor = CellTextExtractor(
                placeholder_source=self.text_extractor.placeholder_source,
                ocr_confidence_threshold=config.ocr_confidence_threshold,
                llm_fallback_enabled=config.llm_fallback_enabled,
                llm_service=llm_service,
            )

        for idx, region in enumerate(regions):
            if cancel_event.is_set():
                page_result.errors.append(
                    f"Page {page_index}: cancelled during table processing"
                )
                page_result.page_skipped = True
                break

            table_id = f"p{page_index}_t{idx}"
            table_start = time.time()
            log_with_context(
                logger,
                logging.DEBUG,
                "Extracting table",
                table_id=table_id,
                page_index=page_index,
            )

            try:
                grid = local_grid_detector.build_grid(
                    region=region,
                    n_rows=config.default_rows,
                    n_cols=config.default_cols,
                    table_id=table_id,
                    page_image=page_image,
                )
                local_extractor.fill_cell_text(grid, page_image=page_image)
                spec = self.assembler.to_dataframe_spec(
                    grid, filler_value=config.ragged_fill_value
                )

                cell_count = len(grid.cells)
                cells_with_text = sum(1 for cell in grid.cells if cell.text)
                confidences = [
                    c.text_confidence for c in grid.cells if c.text_confidence is not None
                ]
                average_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0.0
                )
                llm_fallback_count = sum(
                    1 for c in grid.cells if c.text_source == "llm_fallback"
                )
                extraction_duration = (time.time() - table_start) * 1000

                metadata = TableMetadata(
                    table_id=grid.table_id,
                    page_index=grid.page_index,
                    region=region,
                    grid_shape=(grid.n_rows, grid.n_cols),
                    status="success",
                    cell_count=cell_count,
                    cells_with_text=cells_with_text,
                    average_confidence=average_confidence,
                    extraction_duration_ms=extraction_duration,
                    structure_confidence=grid.structure_confidence,
                    irregularities=list(grid.irregularities),
                    section_labels=grid.section_labels,
                )

                page_result.tables.append(spec)
                page_result.metadata.append(metadata)
                page_result.tables_detected += 1
                page_result.tables_extracted += 1
                page_result.cells_with_text += cells_with_text
                page_result.total_cells += cell_count
                page_result.llm_fallback_count += llm_fallback_count
                page_result.confidence_sum += sum(confidences)
                page_result.confidence_count += len(confidences)
                page_grids.append(grid)

                log_with_context(
                    logger,
                    logging.INFO,
                    "Table extracted successfully",
                    table_id=table_id,
                    cell_count=cell_count,
                    cells_with_text=cells_with_text,
                    average_confidence=average_confidence,
                    llm_fallback_count=llm_fallback_count,
                    extraction_duration_ms=extraction_duration,
                )
            except Exception as exc:
                page_result.tables_failed += 1
                error_msg = f"Table {table_id} extraction failed: {exc}"
                page_result.errors.append(error_msg)
                log_with_context(
                    logger,
                    logging.ERROR,
                    "Table extraction failed",
                    table_id=table_id,
                    error=str(exc),
                )
                failed_metadata = TableMetadata(
                    table_id=table_id,
                    page_index=page_index,
                    region=region,
                    grid_shape=(0, 0),
                    status="extraction_failed",
                    error_message=str(exc),
                )
                page_result.metadata.append(failed_metadata)

        if (
            config.enable_debug_artifacts
            and config.generate_overlays
            and regions
            and page_grids
        ):
            try:
                output_dir = Path(config.debug_output_dir)
                overlay_path = output_dir / f"page_{page_index}_overlay.png"
                draw_table_overlay(page_image, regions, page_grids, overlay_path)
                page_result.overlay_path = overlay_path
                log_with_context(
                    logger,
                    logging.DEBUG,
                    "Generated overlay image",
                    page_index=page_index,
                    overlay_path=str(overlay_path),
                )
            except Exception as exc:
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Failed to generate overlay image",
                    page_index=page_index,
                    error=str(exc),
                )

        page_result.page_duration_ms = (time.time() - page_start) * 1000
        log_with_context(
            logger,
            logging.DEBUG,
            "Page processing completed",
            page_index=page_index,
            duration_ms=page_result.page_duration_ms,
            tables_extracted=page_result.tables_extracted,
        )
        return page_result


class GeminiEndToEndStrategy(PageExtractionStrategy):
    """End-to-End LLM extraction strategy using Gemini (or compatible API)."""

    def process_page(
        self,
        page_index: int,
        page_image: PageImage,
        config: "PipelineConfig",
        logger: logging.Logger,
        cancel_event: threading.Event,
        page_obj: Optional[Any] = None,
    ) -> "PageProcessingResult":
        from .pipeline import PageProcessingResult

        page_start = time.time()
        page_result = PageProcessingResult(page_index=page_index)

        if not config.llm_api_key:
            page_result.errors.append("LLM API key required for end-to-end extraction")
            page_result.page_skipped = True
            return page_result

        log_with_context(
            logger,
            logging.INFO,
            "Starting LLM extraction",
            page_index=page_index,
            primary_model=config.llm_model,
            attempts=config.llm_consistency_attempts,
        )

        try:
            prompt = self._get_prompt()
            attempts = config.llm_consistency_attempts
            raw_results: List[Dict[str, Any]] = []
            model_used = config.llm_model
            primary_failed = False

            # Try primary model (e.g., gemini-2.5-pro - FREE)
            for i in range(attempts):
                if cancel_event.is_set():
                    break
                
                log_with_context(logger, logging.DEBUG, f"LLM Attempt {i+1}/{attempts} with {model_used}", page_index=page_index)
                
                # Count this attempt
                page_result.llm_calls_primary += 1
                
                try:
                    response_text, tokens_in, tokens_out = self._call_llm_with_tracking(page_image, prompt, config, model_override=None)
                    parsed_json = self._parse_response(response_text)
                    raw_results.append(parsed_json)
                    
                    # Track token usage
                    page_result.llm_tokens_input += tokens_in
                    page_result.llm_tokens_output += tokens_out
                    
                    log_with_context(logger, logging.DEBUG, f"Attempt {i+1} succeeded", page_index=page_index, tables_found=len(parsed_json.get("tables", [])))
                    break  # Success! No need to retry
                except Exception as e:
                    error_str = str(e)
                    error_type = type(e).__name__
                    
                    # Check if error is retryable (500, 503, 429, timeout, or "internal error")
                    is_retryable = (
                        "500" in error_str or 
                        "503" in error_str or 
                        "429" in error_str or
                        "internal error" in error_str.lower() or
                        "timeout" in error_str.lower() or
                        "deadline exceeded" in error_str.lower()
                    )
                    
                    log_with_context(logger, logging.WARNING, f"Attempt {i+1} failed: {e}", page_index=page_index, error_type=error_type, retryable=is_retryable)
                    primary_failed = True
                    
                    # If retryable and not last attempt, wait before retrying
                    if is_retryable and i < attempts - 1:
                        wait_time = min(2 ** i, 10)  # Exponential backoff: 1s, 2s, 4s, max 10s
                        log_with_context(logger, logging.INFO, f"Retrying in {wait_time}s (exponential backoff)", page_index=page_index)
                        time.sleep(wait_time)
                    elif not is_retryable:
                        # Non-retryable error (e.g., 400, 401, 403) - don't retry
                        log_with_context(logger, logging.ERROR, f"Non-retryable error, stopping attempts: {e}", page_index=page_index)
                        break

            # Escalation logic: If primary model failed and escalation is enabled
            if not raw_results and config.enable_auto_escalation and config.llm_model_escalation:
                log_with_context(
                    logger,
                    logging.INFO,
                    "Primary model failed, escalating to premium model",
                    page_index=page_index,
                    escalation_model=config.llm_model_escalation,
                )
                
                # Try escalation model (e.g., gemini-3.0-pro - PAID)
                for i in range(attempts):
                    if cancel_event.is_set():
                        break
                    
                    log_with_context(logger, logging.DEBUG, f"Escalation attempt {i+1}/{attempts}", page_index=page_index)
                    
                    # Count this escalation attempt
                    page_result.llm_calls_escalation += 1
                    
                    try:
                        response_text, tokens_in, tokens_out = self._call_llm_with_tracking(
                            page_image, prompt, config, model_override=config.llm_model_escalation
                        )
                        parsed_json = self._parse_response(response_text)
                        raw_results.append(parsed_json)
                        
                        # Track token usage
                        page_result.llm_tokens_input += tokens_in
                        page_result.llm_tokens_output += tokens_out
                        model_used = config.llm_model_escalation
                        
                        log_with_context(logger, logging.INFO, "Escalation succeeded", page_index=page_index)
                        break  # Success! No need to retry
                    except Exception as e:
                        error_str = str(e)
                        error_type = type(e).__name__
                        
                        # Check if error is retryable
                        is_retryable = (
                            "500" in error_str or 
                            "503" in error_str or 
                            "429" in error_str or
                            "internal error" in error_str.lower() or
                            "timeout" in error_str.lower() or
                            "deadline exceeded" in error_str.lower()
                        )
                        
                        log_with_context(logger, logging.WARNING, f"Escalation attempt {i+1} failed: {e}", page_index=page_index, error_type=error_type, retryable=is_retryable)
                        
                        # If retryable and not last attempt, wait before retrying
                        if is_retryable and i < attempts - 1:
                            wait_time = min(2 ** i, 10)  # Exponential backoff: 1s, 2s, 4s, max 10s
                            log_with_context(logger, logging.INFO, f"Retrying escalation in {wait_time}s (exponential backoff)", page_index=page_index)
                            time.sleep(wait_time)
                        elif not is_retryable:
                            # Non-retryable error - don't retry
                            log_with_context(logger, logging.ERROR, f"Non-retryable error in escalation, stopping: {e}", page_index=page_index)
                            break

            if not raw_results:
                raise RuntimeError("All LLM attempts (primary + escalation) failed to return valid JSON")
            
            page_result.model_used = model_used

            # Consensus Logic
            final_tables = self._consensus_vote(raw_results, config.llm_consistency_threshold)
            log_with_context(logger, logging.DEBUG, f"Consensus produced {len(final_tables)} tables", page_index=page_index)

            # Position Verification (if enabled)
            if config.enable_position_verification:
                try:
                    from .position_verifier import PositionVerifier
                    
                    verifier = PositionVerifier(
                        ocr_confidence_threshold=config.ocr_confidence_threshold,
                        fuzzy_match_threshold=0.8
                    )
                    
                    # Extract OCR tokens from page image (use pdfplumber page if available)
                    ocr_tokens = verifier.extract_ocr_tokens(page_image, page_obj=page_obj)
                    log_with_context(logger, logging.DEBUG, f"Extracted {len(ocr_tokens)} OCR tokens for verification", page_index=page_index)
                    
                    # Verify each table
                    for table_data in final_tables:
                        # Note: We don't have precise table bounding boxes from LLM extraction,
                        # so we estimate based on image dimensions
                        n_tables = len(final_tables)
                        img_width, img_height = page_image.size
                        
                        # Simple heuristic: distribute tables vertically
                        table_height = img_height / n_tables
                        table_idx = final_tables.index(table_data)
                        estimated_bbox = BoundingBox(
                            x0=0,
                            y0=table_idx * table_height,
                            x1=img_width,
                            y1=(table_idx + 1) * table_height
                        )
                        
                        # Note: Position verification requires TableDataFrameSpec, which we create in _convert_to_spec.
                        # For now, we'll store OCR tokens and verification will happen post-conversion.
                        # Store in table_data for use in _convert_to_spec
                        table_data["_ocr_tokens"] = ocr_tokens
                        table_data["_estimated_bbox"] = estimated_bbox
                        
                except ImportError as e:
                    log_with_context(logger, logging.WARNING, f"Position verification skipped: {e}", page_index=page_index)
                except Exception as e:
                    log_with_context(logger, logging.WARNING, f"Position verification failed: {e}", page_index=page_index)

            # Convert to Pipeline Spec (with position verification if data available)
            for table_data in final_tables:
                try:
                    spec, meta = self._convert_to_spec(table_data, page_index, config)
                    page_result.tables.append(spec)
                    page_result.metadata.append(meta)
                    page_result.tables_extracted += 1
                    page_result.tables_detected += 1  # Implicitly detected if extracted
                except Exception as e:
                    log_with_context(logger, logging.ERROR, f"Failed to convert table to spec: {e}", page_index=page_index, table_data=table_data)
                    raise

        except Exception as exc:
            page_result.page_skipped = True
            error_msg = f"Page {page_index}: Gemini extraction failed: {exc}"
            page_result.errors.append(error_msg)
            log_with_context(
                logger,
                logging.ERROR,
                "Gemini extraction failed",
                page_index=page_index,
                error=str(exc),
            )

        page_result.page_duration_ms = (time.time() - page_start) * 1000
        return page_result

    def _get_prompt(self) -> str:
        return """
You are a precise data extraction engine. Extract ALL tables from this page image into a valid JSON object.

OUTPUT FORMAT (Strict JSON):
{
  "tables": [
    {
      "table_id": "table_1",
      "columns": ["Header1", "Header2", ...],
      "rows": [
        ["row1_col1", "row1_col2", ...],
        ["row2_col1", "row2_col2", ...]
      ]
    }
  ]
}

RULES:
1. Extract text exactly as it appears.
2. If a cell is empty, use an empty string "".
3. If a cell spans multiple columns, repeat the value or leave subsequent cells empty (standardize on repetition if ambiguous).
4. Return ONLY valid JSON. No markdown blocks (```json), no commentary.
"""

    def _call_llm(self, image: PageImage, prompt: str, config: "PipelineConfig") -> str:
        """Call the LLM API. Supports Google GenAI or OpenAI based on config."""
        text, _, _ = self._call_llm_with_tracking(image, prompt, config)
        return text

    def _call_llm_with_tracking(
        self, 
        image: PageImage, 
        prompt: str, 
        config: "PipelineConfig",
        model_override: Optional[str] = None
    ) -> tuple[str, int, int]:
        """Call LLM API with token tracking.
        
        Returns:
            (response_text, input_tokens, output_tokens)
        """
        # Convert image to bytes once
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        # Use override model if provided (for escalation)
        effective_model = model_override or config.llm_model

        if config.llm_provider == "google" or "gemini" in (effective_model or "").lower():
            return self._call_google_genai_with_tracking(img_bytes, prompt, config, effective_model)
        else:
            # Default to OpenAI-style for everything else
            return self._call_openai_style_with_tracking(img_bytes, prompt, config, effective_model)

    def _call_google_genai(self, img_bytes: bytes, prompt: str, config: "PipelineConfig") -> str:
        """Legacy method without token tracking."""
        text, _, _ = self._call_google_genai_with_tracking(img_bytes, prompt, config, config.llm_model)
        return text

    def _call_google_genai_with_tracking(
        self, 
        img_bytes: bytes, 
        prompt: str, 
        config: "PipelineConfig",
        model_name: Optional[str] = None
    ) -> tuple[str, int, int]:
        """Call Google GenAI with token tracking.
        
        Returns:
            (response_text, input_tokens, output_tokens)
        """
        try:
            import google.generativeai as genai
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

        genai.configure(api_key=config.llm_api_key)
        
        # Use provided model or default to gemini-2.5-pro (FREE!)
        model_name = model_name or config.llm_model or "gemini-2.5-pro"
        model = genai.GenerativeModel(model_name)
        
        # Image part
        image_part = {"mime_type": "image/png", "data": img_bytes}
        
        # Safety settings - permissive for document data
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        response = model.generate_content(
            [prompt, image_part],
            safety_settings=safety_settings,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                temperature=0.1  # Low temp for factual extraction
            )
        )
        
        # Extract token usage from response metadata (if available)
        input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0
        output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0
        
        # Fallback estimate if API doesn't provide tokens
        if input_tokens == 0:
            input_tokens = len(prompt) // 4 + 1000  # Rough estimate: prompt + image tokens
        if output_tokens == 0:
            output_tokens = len(response.text) // 4  # Rough estimate
        
        return response.text, input_tokens, output_tokens

    def _call_openai_style(self, img_bytes: bytes, prompt: str, config: "PipelineConfig") -> str:
        """Legacy method without token tracking."""
        text, _, _ = self._call_openai_style_with_tracking(img_bytes, prompt, config, config.llm_model)
        return text

    def _call_openai_style_with_tracking(
        self, 
        img_bytes: bytes, 
        prompt: str, 
        config: "PipelineConfig",
        model_name: Optional[str] = None
    ) -> tuple[str, int, int]:
        """Call OpenAI-compatible API with token tracking.
        
        Returns:
            (response_text, input_tokens, output_tokens)
        """
        try:
            import openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        client = openai.OpenAI(api_key=config.llm_api_key)
        model = model_name or config.llm_model or "gpt-4o"
        
        b64_image = base64.b64encode(img_bytes).decode('utf-8')
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                    ]
                }
            ],
            max_tokens=4000,
            temperature=0.1
        )
        
        # Extract token usage from response
        input_tokens = getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0
        output_tokens = getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0
        
        return response.choices[0].message.content or "", input_tokens, output_tokens

    @staticmethod
    def estimate_cost(tokens_input: int, tokens_output: int, model_name: str) -> float:
        """Estimate cost in USD based on token usage and model.
        
        Pricing (as of Nov 2025):
        - gemini-2.5-pro: FREE (subsidized by Google)
        - gemini-3.0-pro: ~$1.25/1M input, ~$5.00/1M output (estimate)
        - gpt-4o: $2.50/1M input, $10.00/1M output
        - gemini-1.5-flash: $0.075/1M input, $0.30/1M output
        """
        model_lower = model_name.lower()
        
        # FREE models
        if "2.5-pro" in model_lower or "2.5" in model_lower:
            return 0.0  # FREE!
        
        # Gemini 3.0 Pro (paid, estimate)
        if "3.0-pro" in model_lower or "3-pro" in model_lower:
            cost_per_1m_in = 1.25
            cost_per_1m_out = 5.00
        # GPT-4o
        elif "gpt-4o" in model_lower:
            cost_per_1m_in = 2.50
            cost_per_1m_out = 10.00
        # Gemini Flash (cheap)
        elif "flash" in model_lower:
            cost_per_1m_in = 0.075
            cost_per_1m_out = 0.30
        # Default conservative estimate
        else:
            cost_per_1m_in = 1.0
            cost_per_1m_out = 3.0
        
        cost = (tokens_input / 1_000_000) * cost_per_1m_in + \
               (tokens_output / 1_000_000) * cost_per_1m_out
        return cost

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse strict JSON from LLM response, handling markdown code blocks."""
        clean_text = text.strip()
        
        # Strip markdown code blocks if present
        if "```" in clean_text:
            # Find the start of JSON (after ```json or ```)
            start_idx = clean_text.find("```")
            if start_idx >= 0:
                # Skip past the opening ```
                after_start = clean_text[start_idx + 3:]
                # Find the next newline (skip optional language tag like "json")
                newline_idx = after_start.find("\n")
                if newline_idx >= 0:
                    clean_text = after_start[newline_idx + 1:]
                else:
                    clean_text = after_start
            
            # Remove closing ```
            end_idx = clean_text.rfind("```")
            if end_idx >= 0:
                clean_text = clean_text[:end_idx].rstrip()
        
        return json.loads(clean_text)

    def _consensus_vote(self, results: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """
        Merge multiple LLM results into a single consistent output with confidence tracking.
        Logic:
        1. Group tables by structure (row/col counts).
        2. Select the most common structure.
        3. For that structure, vote on cell contents across matching results.
        4. Track agreement ratio for confidence scoring.
        
        Returns:
            List of consensus tables, each with added "cell_confidences" field
        """
        if not results:
            return []
        
        if len(results) == 1:
            # Single result - assign perfect confidence
            tables = results[0].get("tables", [])
            for table in tables:
                n_rows = len(table.get("rows", []))
                n_cols = len(table.get("columns", []))
                table["cell_confidences"] = [[1.0 for _ in range(n_cols)] for _ in range(n_rows)]
            return tables

        # Flatten all detected tables from all runs
        # We need to align tables. For now, assume table order matches (simple case).
        # A more robust approach would match by content similarity.
        
        # Let's assume the first result defines the "expected" number of tables
        base_tables = results[0].get("tables", [])
        num_tables = len(base_tables)
        
        final_tables = []
        
        for t_idx in range(num_tables):
            # Gather candidates for this table index from all runs
            candidates = []
            for res in results:
                tables = res.get("tables", [])
                if t_idx < len(tables):
                    candidates.append(tables[t_idx])
            
            if not candidates:
                continue

            # Vote on dimensions (rows x cols)
            dims = [(len(c.get("rows", [])), len(c.get("columns", []))) for c in candidates]
            most_common_dim = Counter(dims).most_common(1)[0][0]
            target_rows, target_cols = most_common_dim
            
            # Filter candidates that match the consensus dimensions
            valid_candidates = [
                c for c in candidates 
                if len(c.get("rows", [])) == target_rows and len(c.get("columns", [])) == target_cols
            ]
            
            # If no majority (highly unlikely if we filter strictly), fallback to first
            if not valid_candidates:
                table = candidates[0]
                n_rows = len(table.get("rows", []))
                n_cols = len(table.get("columns", []))
                table["cell_confidences"] = [[0.5 for _ in range(n_cols)] for _ in range(n_rows)]
                final_tables.append(table)
                continue

            # Construct consensus table
            consensus_table = {
                "table_id": valid_candidates[0].get("table_id", f"table_{t_idx}"),
                "columns": [],
                "rows": [],
                "cell_confidences": []  # Track per-cell confidence
            }
            
            n_candidates = len(valid_candidates)
            
            # Vote on Columns
            for c_idx in range(target_cols):
                col_values = [c["columns"][c_idx] for c in valid_candidates]
                consensus_col = Counter(col_values).most_common(1)[0][0]
                consensus_table["columns"].append(consensus_col)
            
            # Vote on Rows (Cells) with confidence tracking
            for r_idx in range(target_rows):
                row_cells = []
                row_confidences = []
                
                for c_idx in range(target_cols):
                    # Gather value for this cell from all valid candidates
                    cell_values = []
                    for c in valid_candidates:
                        row = c["rows"][r_idx]
                        # Safety check for ragged rows in candidate (should be covered by dim check but safe > sorry)
                        if c_idx < len(row):
                            cell_values.append(str(row[c_idx]))  # Convert to string for comparison
                        else:
                            cell_values.append("")
                    
                    # Majority vote with confidence calculation
                    value_counts = Counter(cell_values)
                    best_val, count = value_counts.most_common(1)[0][0], value_counts.most_common(1)[0][1]
                    
                    # Confidence = agreement ratio (e.g., 3/3 = 1.0, 2/3 = 0.67)
                    confidence = count / n_candidates
                    
                    row_cells.append(best_val)
                    row_confidences.append(confidence)
                
                consensus_table["rows"].append(row_cells)
                consensus_table["cell_confidences"].append(row_confidences)
            
            final_tables.append(consensus_table)

        return final_tables

    def _convert_to_spec(self, table_data: Dict[str, Any], page_index: int, config: "PipelineConfig" = None) -> Tuple[TableDataFrameSpec, TableMetadata]:
        """Convert JSON dict to internal pipeline models with consensus and position confidence."""
        rows = table_data.get("rows", [])
        col_names = table_data.get("columns", [])
        cell_confidences = table_data.get("cell_confidences", None)
        
        # Position verification data (if available)
        ocr_tokens = table_data.get("_ocr_tokens", None)
        estimated_bbox = table_data.get("_estimated_bbox", None)
        
        # Create ColumnSpecs
        columns = [ColumnSpec(name=str(name)) for name in col_names]
        
        # Create TableDataFrameSpec
        spec = TableDataFrameSpec(
            rows=rows,
            columns=columns,
            table_metadata_id=table_data.get("table_id", "unknown")
        )
        
        # Calculate consensus confidence from cell confidences
        if cell_confidences:
            # Average confidence across all cells
            total_confidence = sum(sum(row) for row in cell_confidences)
            total_cells = sum(len(row) for row in cell_confidences)
            consensus_confidence = total_confidence / total_cells if total_cells > 0 else 1.0
            
            # Count low-confidence cells (< 0.7) for reporting
            low_conf_cells = []
            for r_idx, row in enumerate(cell_confidences):
                for c_idx, conf in enumerate(row):
                    if conf < 0.7:
                        low_conf_cells.append((r_idx, c_idx))
        else:
            consensus_confidence = 1.0
            low_conf_cells = []
        
        # Run position verification if OCR tokens are available
        position_confidence = None
        position_cell_confidences = None
        position_mismatched_cells = []
        
        if ocr_tokens and estimated_bbox and config and config.enable_position_verification:
            try:
                from .position_verifier import PositionVerifier
                
                verifier = PositionVerifier(
                    ocr_confidence_threshold=config.ocr_confidence_threshold,
                    fuzzy_match_threshold=0.8
                )
                
                # Verify table position
                position_cell_confidences, position_mismatched_cells, position_confidence = verifier.verify_table(
                    spec, estimated_bbox, ocr_tokens
                )
                
                # Combine consensus and position confidences if both available
                if cell_confidences and position_cell_confidences:
                    # Average the two confidence sources
                    combined_confidences = []
                    for r_idx in range(len(cell_confidences)):
                        row_conf = []
                        for c_idx in range(len(cell_confidences[r_idx])):
                            consensus = cell_confidences[r_idx][c_idx]
                            position = position_cell_confidences[r_idx][c_idx]
                            combined = (consensus + position) / 2.0
                            row_conf.append(combined)
                        combined_confidences.append(row_conf)
                    
                    cell_confidences = combined_confidences
                    consensus_confidence = (consensus_confidence + position_confidence) / 2.0
                    
                    # Merge mismatched cells lists
                    all_mismatched = set(low_conf_cells + position_mismatched_cells)
                    low_conf_cells = list(all_mismatched)
                elif position_cell_confidences:
                    # Only position confidence available
                    cell_confidences = position_cell_confidences
                    consensus_confidence = position_confidence
                    low_conf_cells = position_mismatched_cells
                    
            except Exception as e:
                # Position verification failed, continue with consensus only
                import logging
                logging.warning(f"Position verification failed: {e}")
        
        # Create Metadata with bbox estimate
        bbox = estimated_bbox if estimated_bbox else BoundingBox(0.0, 0.0, 1.0, 1.0)
        region = TableRegion(page_index=page_index, bbox=bbox, confidence=1.0)
        
        irregularities = ["llm_extracted"]
        if low_conf_cells:
            irregularities.append(f"low_confidence_{len(low_conf_cells)}_cells")
        if position_confidence and position_confidence < 0.7:
            irregularities.append(f"low_position_conf_{position_confidence:.2f}")
        
        meta = TableMetadata(
            table_id=table_data.get("table_id", "unknown"),
            page_index=page_index,
            region=region,
            grid_shape=(len(rows), len(col_names)),
            status="success",
            cell_count=len(rows) * len(col_names),
            cells_with_text=sum(1 for r in rows for c in r if c),
            average_confidence=consensus_confidence,
            irregularities=irregularities,
            # Consensus tracking
            consensus_confidence=consensus_confidence,
            position_confidence=position_confidence,
            cell_confidences=cell_confidences,
            mismatched_cells=low_conf_cells if low_conf_cells else None
        )
        
        return spec, meta
