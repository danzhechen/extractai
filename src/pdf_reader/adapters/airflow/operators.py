"""
Airflow operator for PDF table extraction.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

try:
    from airflow.models import BaseOperator
    from airflow.utils.decorators import apply_defaults
except ImportError:
    raise ImportError(
        "Airflow is not installed. Install with: pip install pdf-reader[airflow] "
        "or pip install apache-airflow>=2.5.0"
    )

from ...pipeline import PipelineConfig
from ..core import AdapterConfig, InputSource, OutputSink, run_extraction

logger = logging.getLogger(__name__)


class PdfExtractionOperator(BaseOperator):
    """Airflow operator for PDF table extraction.
    
    This operator runs the PDF table extraction pipeline as part of an Airflow DAG.
    It supports templated fields for dynamic task parameters and pushes extraction
    results to XCom for downstream tasks.
    
    Attributes:
        input_path: Path to input PDF file (supports Jinja templating)
        output_dir: Directory for output artifacts (supports Jinja templating)
        config_path: Optional path to YAML config file (supports Jinja templating)
        pipeline_config: Optional dict of pipeline config overrides
        push_results: Whether to push extraction summary to XCom (default: True)
        run_id: Optional run identifier (auto-generated if not provided)
        metadata: Additional run metadata dict
    
    Example:
        >>> from airflow import DAG
        >>> from pdf_reader.adapters.airflow import PdfExtractionOperator
        >>> from datetime import datetime
        >>> 
        >>> with DAG("pdf_extraction", start_date=datetime(2025, 1, 1)):
        ...     extract = PdfExtractionOperator(
        ...         task_id="extract_tables",
        ...         input_path="{{ params.pdf_path }}",
        ...         output_dir="{{ params.output_dir }}",
        ...         config_path="configs/production.yaml",
        ...         pipeline_config={"dpi": 300, "enable_debug_artifacts": True},
        ...         metadata={"team": "analytics", "project": "q4-reports"},
        ...     )
    
    XCom Output:
        The operator pushes a dict with the following keys to XCom:
        - tables_extracted: Number of tables successfully extracted
        - pages_processed: Number of pages processed
        - elapsed_seconds: Total execution time in seconds
        - run_id: Unique run identifier
    """
    
    # Airflow templated fields (support Jinja2 templating)
    template_fields: Sequence[str] = ("input_path", "output_dir", "config_path")
    
    # UI color for operator in Airflow UI
    ui_color = "#e8f4f8"
    
    @apply_defaults
    def __init__(
        self,
        input_path: str,
        output_dir: str,
        config_path: Optional[str] = None,
        pipeline_config: Optional[Dict[str, Any]] = None,
        push_results: bool = True,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Initialize PdfExtractionOperator.
        
        Args:
            input_path: Path to input PDF file
            output_dir: Directory for output artifacts
            config_path: Optional path to YAML config file
            pipeline_config: Optional dict of pipeline config overrides
            push_results: Whether to push extraction summary to XCom
            run_id: Optional run identifier (auto-generated if not provided)
            metadata: Additional run metadata dict
            **kwargs: Additional BaseOperator arguments
        """
        super().__init__(**kwargs)
        self.input_path = input_path
        self.output_dir = output_dir
        self.config_path = config_path
        self.pipeline_config = pipeline_config or {}
        self.push_results = push_results
        self.run_id = run_id
        self.metadata = metadata or {}
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PDF table extraction.
        
        Args:
            context: Airflow task execution context
            
        Returns:
            Dict with extraction summary (pushed to XCom if push_results=True)
            
        Raises:
            Exception: Any exception from pipeline execution
        """
        logger.info(f"Starting PDF extraction: {self.input_path}")
        
        # Load pipeline config
        config = self._load_pipeline_config()
        
        # Add Airflow context to metadata
        run_metadata = {
            **self.metadata,
            "airflow_dag_id": context.get("dag").dag_id if context.get("dag") else None,
            "airflow_task_id": context.get("task_instance").task_id if context.get("task_instance") else None,
            "airflow_execution_date": str(context.get("execution_date")),
            "airflow_run_id": context.get("run_id"),
        }
        
        # Create adapter config
        adapter_config = AdapterConfig(
            input_source=InputSource(type="file", location=self.input_path),
            output_sink=OutputSink(type="filesystem", location=self.output_dir),
            pipeline_config=config,
            run_id=self.run_id,
            metadata=run_metadata,
        )
        
        # Run extraction
        result = run_extraction(adapter_config)
        
        # Prepare summary for XCom
        summary = {
            "tables_extracted": result.stats.tables_extracted,
            "pages_processed": result.stats.pages_processed,
            "elapsed_seconds": result.stats.elapsed_seconds,
            "run_id": adapter_config.run_id,
            "output_dir": str(Path(self.output_dir) / adapter_config.run_id),
        }
        
        logger.info(f"Extraction complete: {summary}")
        
        # Push to XCom if enabled
        if self.push_results:
            context["task_instance"].xcom_push(key="extraction_summary", value=summary)
        
        return summary
    
    def _load_pipeline_config(self) -> PipelineConfig:
        """Load pipeline configuration from file and overrides.
        
        Returns:
            PipelineConfig instance
        """
        # Start with defaults
        config_dict = {}
        
        # Load from config file if provided
        if self.config_path:
            config_path = Path(self.config_path)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {config_path}")
            
            import yaml
            with open(config_path) as f:
                config_dict = yaml.safe_load(f) or {}
            
            logger.info(f"Loaded config from {config_path}")
        
        # Apply overrides from pipeline_config parameter
        config_dict.update(self.pipeline_config)
        
        # Create PipelineConfig instance
        return PipelineConfig(**config_dict)


