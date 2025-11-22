"""
Core adapter abstractions and utilities.

This module defines the base configuration and abstractions used by all adapters.
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Union

from ..models import ExtractionResult
from ..pipeline import PipelineConfig, PipelineRunner

logger = logging.getLogger(__name__)


@dataclass
class InputSource:
    """Abstract input source for PDF documents.
    
    Supports multiple source types:
    - file: Local filesystem path
    - url: HTTP/HTTPS URL
    - s3: S3 URI (s3://bucket/key)
    - gcs: GCS URI (gs://bucket/key)
    - bytes: Raw PDF bytes
    
    Attributes:
        type: Source type identifier
        location: Source location (path, URL, URI) - not used for bytes type
        credentials: Optional authentication credentials dict
        data: Raw bytes data (only for bytes type)
    
    Example:
        >>> # Local file
        >>> source = InputSource(type="file", location="/path/to/doc.pdf")
        >>> 
        >>> # S3 with credentials
        >>> source = InputSource(
        ...     type="s3",
        ...     location="s3://my-bucket/document.pdf",
        ...     credentials={"aws_access_key_id": "...", "aws_secret_access_key": "..."}
        ... )
        >>> 
        >>> # Raw bytes
        >>> with open("doc.pdf", "rb") as f:
        ...     source = InputSource(type="bytes", data=f.read())
    """
    
    type: Literal["file", "url", "s3", "gcs", "bytes"]
    location: Optional[str] = None
    credentials: Optional[Dict[str, str]] = None
    data: Optional[bytes] = None
    
    def __post_init__(self) -> None:
        """Validate input source configuration."""
        if self.type == "bytes":
            if self.data is None:
                raise ValueError("InputSource type 'bytes' requires 'data' field")
        else:
            if self.location is None:
                raise ValueError(f"InputSource type '{self.type}' requires 'location' field")
    
    def resolve(self) -> Union[Path, bytes]:
        """Resolve input source to a path or bytes for pipeline consumption.
        
        Returns:
            Path object for file sources, bytes for all other sources
            
        Raises:
            NotImplementedError: For URL, S3, and GCS sources (requires additional dependencies)
            FileNotFoundError: If file source doesn't exist
        """
        if self.type == "file":
            path = Path(self.location)
            if not path.exists():
                raise FileNotFoundError(f"Input file not found: {path}")
            return path
        
        elif self.type == "bytes":
            return self.data
        
        elif self.type == "url":
            # TODO: Implement URL fetching with requests
            raise NotImplementedError(
                "URL input source requires 'requests' library. "
                "Install with: pip install pdf-reader[http]"
            )
        
        elif self.type in ("s3", "gcs"):
            # TODO: Implement cloud storage fetching
            raise NotImplementedError(
                f"{self.type.upper()} input source requires cloud storage libraries. "
                f"Install with: pip install pdf-reader[cloud]"
            )
        
        else:
            raise ValueError(f"Unknown input source type: {self.type}")


@dataclass
class OutputSink:
    """Abstract output destination for extraction results.
    
    Supports multiple destination types:
    - filesystem: Local directory
    - s3: S3 prefix (s3://bucket/prefix/)
    - gcs: GCS prefix (gs://bucket/prefix/)
    - database: Database connection (future)
    
    Attributes:
        type: Sink type identifier
        location: Destination location (path, URI)
        credentials: Optional authentication credentials dict
        options: Additional sink-specific options
    
    Example:
        >>> # Local filesystem
        >>> sink = OutputSink(type="filesystem", location="/path/to/output/")
        >>> 
        >>> # S3 with custom options
        >>> sink = OutputSink(
        ...     type="s3",
        ...     location="s3://my-bucket/outputs/",
        ...     credentials={"aws_access_key_id": "...", "aws_secret_access_key": "..."},
        ...     options={"acl": "private", "storage_class": "STANDARD"}
        ... )
    """
    
    type: Literal["filesystem", "s3", "gcs", "database"]
    location: str
    credentials: Optional[Dict[str, str]] = None
    options: Dict[str, Any] = field(default_factory=dict)
    
    def write_extraction_result(
        self,
        result: ExtractionResult,
        run_id: str,
        manifest_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write extraction result to configured sink.
        
        Creates the following artifacts in the sink:
        - manifest.json: Run manifest with metadata
        - config.yaml: Pipeline config snapshot
        - extraction_report.html: HTML report (if enabled)
        - tables/table_N.csv: Individual table CSV files
        - debug/page_N_overlay.png: Debug overlays (if enabled)
        
        Args:
            result: Extraction result to write
            run_id: Unique run identifier for organizing outputs
            manifest_data: Optional manifest data to include
            
        Raises:
            NotImplementedError: For non-filesystem sinks
        """
        if self.type == "filesystem":
            self._write_to_filesystem(result, run_id, manifest_data)
        else:
            raise NotImplementedError(
                f"{self.type} output sink not yet implemented. "
                f"Currently only 'filesystem' is supported."
            )
    
    def _write_to_filesystem(
        self,
        result: ExtractionResult,
        run_id: str,
        manifest_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write result to local filesystem."""
        output_dir = Path(self.location) / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write manifest
        if manifest_data:
            manifest_path = output_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest_data, f, indent=2, default=str)
            logger.info(f"Wrote manifest to {manifest_path}")
        
        # Write tables as CSV
        tables_dir = output_dir / "tables"
        tables_dir.mkdir(exist_ok=True)
        
        for i, table_spec in enumerate(result.tables):
            table_path = tables_dir / f"table_{i}.csv"
            self._write_table_csv(table_spec, table_path)
            logger.info(f"Wrote table {i} to {table_path}")
        
        # Write run stats as JSON
        stats_path = output_dir / "run_stats.json"
        with open(stats_path, "w") as f:
            json.dump(asdict(result.stats), f, indent=2)
        logger.info(f"Wrote run stats to {stats_path}")
        
        logger.info(f"Extraction results written to {output_dir}")
    
    def _write_table_csv(self, table_spec, path: Path) -> None:
        """Write a single table to CSV."""
        import csv
        
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Write header
            header = [col.name for col in table_spec.columns]
            writer.writerow(header)
            
            # Write data rows
            for row in table_spec.rows:
                writer.writerow(row)


@dataclass
class AdapterConfig:
    """Unified configuration for adapter input/output.
    
    This configuration wraps PipelineConfig and adds adapter-specific settings
    for input source and output sink.
    
    Attributes:
        input_source: Input source (file, URL, S3, etc.)
        output_sink: Output destination
        pipeline_config: Core pipeline configuration
        run_id: Optional run identifier (auto-generated if not provided)
        metadata: Additional run metadata (tags, labels, etc.)
    
    Example:
        >>> from pdf_reader.pipeline import PipelineConfig
        >>> 
        >>> adapter_config = AdapterConfig(
        ...     input_source=InputSource(type="file", location="doc.pdf"),
        ...     output_sink=OutputSink(type="filesystem", location="output/"),
        ...     pipeline_config=PipelineConfig(dpi=300, enable_debug_artifacts=True),
        ...     metadata={"team": "analytics", "project": "q4-reports"}
        ... )
    """
    
    input_source: InputSource
    output_sink: OutputSink
    pipeline_config: PipelineConfig
    run_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Generate run_id if not provided."""
        if self.run_id is None:
            import uuid
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            short_uuid = str(uuid.uuid4())[:8]
            self.run_id = f"run_{timestamp}_{short_uuid}"


def run_extraction(adapter_config: AdapterConfig) -> ExtractionResult:
    """Execute extraction with adapter configuration.
    
    This is the main entry point for all adapters. It handles:
    1. Resolving input source to PDF bytes/path
    2. Running the extraction pipeline
    3. Writing results to output sink
    4. Generating manifest
    
    Args:
        adapter_config: Adapter configuration
        
    Returns:
        ExtractionResult object with tables and run stats
        
    Raises:
        Exception: Any exception from pipeline execution
        
    Example:
        >>> config = AdapterConfig(...)
        >>> result = run_extraction(config)
        >>> print(f"Extracted {len(result.tables)} tables")
    """
    logger.info(f"Starting extraction run: {adapter_config.run_id}")
    logger.info(f"Input source: {adapter_config.input_source.type}")
    logger.info(f"Output sink: {adapter_config.output_sink.type}")
    
    # Resolve input source
    pdf_input = adapter_config.input_source.resolve()
    logger.debug(f"Resolved input: {type(pdf_input)}")
    
    # Run extraction
    runner = PipelineRunner()
    result = runner.extract_tables(
        pdf_input=pdf_input,
        config=adapter_config.pipeline_config,
    )
    
    # Generate manifest
    from ..manifest import create_run_manifest
    
    manifest = create_run_manifest(
        pdf_path=str(adapter_config.input_source.location or "bytes_input"),
        config=adapter_config.pipeline_config,
        result=result,
    )
    
    # Add adapter metadata to manifest
    manifest_data = asdict(manifest)
    manifest_data["adapter_metadata"] = adapter_config.metadata
    manifest_data["run_id"] = adapter_config.run_id
    
    # Write results to sink
    adapter_config.output_sink.write_extraction_result(
        result=result,
        run_id=adapter_config.run_id,
        manifest_data=manifest_data,
    )
    
    logger.info(
        f"Extraction complete: {result.stats.tables_extracted} tables extracted "
        f"in {result.stats.elapsed_seconds:.2f}s"
    )
    
    return result


