"""Configuration loading and merging for PDF table extraction pipeline.

This module provides utilities for loading configuration from multiple sources:
- YAML/JSON config files
- Environment variables
- Command-line arguments (handled by CLI module)
- Programmatic defaults
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .pipeline import PipelineConfig


def load_config_from_file(file_path: Path) -> Dict[str, Any]:
    """Load configuration from a YAML or JSON file.

    Args:
        file_path: Path to the config file.

    Returns:
        Dictionary of configuration values.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is invalid or unsupported.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with open(file_path, "r") as f:
        if file_path.suffix.lower() in (".yaml", ".yml"):
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in config file: {e}")
        elif file_path.suffix.lower() == ".json":
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in config file: {e}")
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")


def load_config_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables.

    Environment variable naming convention: `PDF_READER_{SETTING_NAME}`
    Examples:
        - `PDF_READER_DPI` -> `dpi`
        - `PDF_READER_LOG_LEVEL` -> `log_level`
        - `PDF_READER_LLM_API_KEY` -> `llm_api_key`

    Returns:
        Dictionary of configuration values from environment variables.
    """
    config = {}
    env_prefix = "PDF_READER_"

    # Map environment variable names to config field names
    env_mappings = {
        "INPUT_PATH": "input_path",
        "DPI": "dpi",
        "EXTRACTION_STRATEGY": "extraction_strategy",
        "DEFAULT_ROWS": "default_rows",
        "DEFAULT_COLS": "default_cols",
        "OCR_CONFIDENCE_THRESHOLD": "ocr_confidence_threshold",
        "LLM_FALLBACK_ENABLED": "llm_fallback_enabled",
        "LLM_PROVIDER": "llm_provider",
        "LLM_MODEL": "llm_model",
        "LLM_API_KEY": "llm_api_key",
        "LLM_CONSISTENCY_ATTEMPTS": "llm_consistency_attempts",
        "LLM_CONSISTENCY_THRESHOLD": "llm_consistency_threshold",
        "LOG_LEVEL": "log_level",
        "LOG_FILE": "log_file",
        "LOG_FORMAT": "log_format",
        "ENABLE_DEBUG_ARTIFACTS": "enable_debug_artifacts",
        "DEBUG_OUTPUT_DIR": "debug_output_dir",
        "GENERATE_OVERLAYS": "generate_overlays",
        "GENERATE_HTML_REPORT": "generate_html_report",
        "WORKER_TYPE": "worker_type",
        "ENABLE_LINE_DETECTION": "enable_line_detection",
        "LINE_DETECTION_MIN_LENGTH": "line_detection_min_length",
        "LINE_DETECTION_GAP_TOLERANCE": "line_detection_gap_tolerance",
        "LINE_DETECTION_MORPH_ITERATIONS": "line_detection_morph_iterations",
        "LINE_DETECTION_MIN_SEPARATION": "line_detection_min_separation",
        "MAX_WORKERS": "max_workers",
        "PAGE_BATCH_SIZE": "page_batch_size",
        "MAX_INFLIGHT_PAGES": "max_inflight_pages",
        "RUN_TIMEOUT_SECONDS": "run_timeout_seconds",
    }

    for env_key, config_key in env_mappings.items():
        env_var = env_prefix + env_key
        value = os.getenv(env_var)
        if value is not None:
            # Convert string values to appropriate types
            if config_key in ("dpi", "default_rows", "default_cols"):
                try:
                    config[config_key] = int(value)
                except ValueError:
                    continue  # Skip invalid values
            elif config_key == "ocr_confidence_threshold":
                try:
                    config[config_key] = float(value)
                except ValueError:
                    continue
            elif config_key in (
                "llm_fallback_enabled",
                "enable_debug_artifacts",
                "generate_overlays",
                "generate_html_report",
                "enable_line_detection",
            ):
                # Boolean values: accept "true", "True", "1", "yes" as True
                config[config_key] = value.lower() in ("true", "1", "yes", "on")
            elif config_key in (
                "line_detection_min_length",
                "line_detection_gap_tolerance",
                "line_detection_morph_iterations",
                "line_detection_min_separation",
            ):
                try:
                    config[config_key] = int(value)
                except ValueError:
                    continue  # Skip invalid values
            elif config_key in ("max_workers", "page_batch_size", "max_inflight_pages"):
                try:
                    config[config_key] = int(value)
                except ValueError:
                    continue
            elif config_key == "run_timeout_seconds":
                try:
                    config[config_key] = float(value)
                except ValueError:
                    continue
            elif config_key == "page_indices":
                # Parse comma-separated or range format (e.g., "0,2,4" or "0-5")
                try:
                    indices = []
                    for part in value.split(","):
                        part = part.strip()
                        if "-" in part:
                            # Range format: "0-5"
                            start, end = part.split("-", 1)
                            indices.extend(range(int(start), int(end) + 1))
                        else:
                            indices.append(int(part))
                    config[config_key] = indices
                except ValueError:
                    continue
            else:
                # String values
                config[config_key] = value

    return config


def merge_configs(
    defaults: Dict[str, Any],
    env_config: Dict[str, Any],
    file_config: Dict[str, Any],
    cli_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge configuration from multiple sources in priority order.

    Priority (highest to lowest):
    1. CLI arguments
    2. Config file
    3. Environment variables
    4. Defaults

    Args:
        defaults: Default configuration values.
        env_config: Configuration from environment variables.
        file_config: Configuration from config file.
        cli_config: Configuration from CLI arguments.

    Returns:
        Merged configuration dictionary.
    """
    # Start with defaults
    merged = defaults.copy()

    # Override with environment variables
    merged.update(env_config)

    # Override with file config
    merged.update(file_config)

    # Override with CLI config (highest priority)
    merged.update(cli_config)

    return merged


def create_config(
    config_file: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> PipelineConfig:
    """Create a PipelineConfig by loading from all sources.

    Args:
        config_file: Optional path to a YAML/JSON config file.
        cli_overrides: Optional dictionary of CLI argument overrides.

    Returns:
        PipelineConfig instance with merged values from all sources.
    """
    # Start with defaults (create a default config and convert to dict)
    default_config = PipelineConfig()
    defaults = {
        "input_path": default_config.input_path,
        "page_indices": default_config.page_indices,
        "dpi": default_config.dpi,
        "default_rows": default_config.default_rows,
        "default_cols": default_config.default_cols,
        "ocr_confidence_threshold": default_config.ocr_confidence_threshold,
        "llm_fallback_enabled": default_config.llm_fallback_enabled,
        "llm_provider": default_config.llm_provider,
        "llm_model": default_config.llm_model,
        "llm_api_key": default_config.llm_api_key,
        "log_level": default_config.log_level,
        "log_file": default_config.log_file,
        "log_format": default_config.log_format,
        "enable_debug_artifacts": default_config.enable_debug_artifacts,
        "debug_output_dir": default_config.debug_output_dir,
        "generate_overlays": default_config.generate_overlays,
        "generate_html_report": default_config.generate_html_report,
        "worker_type": default_config.worker_type,
        "max_workers": default_config.max_workers,
        "page_batch_size": default_config.page_batch_size,
        "max_inflight_pages": default_config.max_inflight_pages,
        "run_timeout_seconds": default_config.run_timeout_seconds,
        "enable_line_detection": default_config.enable_line_detection,
        "line_detection_min_length": default_config.line_detection_min_length,
        "line_detection_gap_tolerance": default_config.line_detection_gap_tolerance,
        "line_detection_morph_iterations": default_config.line_detection_morph_iterations,
        "line_detection_min_separation": default_config.line_detection_min_separation,
    }

    # Load from environment variables
    env_config = load_config_from_env()

    # Load from config file if provided
    file_config = {}
    if config_file:
        file_config = load_config_from_file(config_file)

    # CLI overrides
    cli_config = cli_overrides or {}

    # Merge all sources
    merged = merge_configs(defaults, env_config, file_config, cli_config)

    # Convert merged dict to PipelineConfig
    # Handle special cases
    if "input_path" in merged and merged["input_path"]:
        merged["input_path"] = Path(merged["input_path"])

    return PipelineConfig(**merged)

