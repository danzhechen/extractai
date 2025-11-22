"""
Integration tests for adapter modules.

These tests verify that adapters can be imported and instantiated correctly.
Full integration tests (running actual extractions) are in separate test files.
"""

import pytest
from pathlib import Path


def test_adapter_core_imports():
    """Test that core adapter classes can be imported."""
    from pdf_reader.adapters.core import AdapterConfig, InputSource, OutputSink
    
    assert AdapterConfig is not None
    assert InputSource is not None
    assert OutputSink is not None


def test_input_source_file():
    """Test InputSource with file type."""
    from pdf_reader.adapters.core import InputSource
    
    source = InputSource(type="file", location="/path/to/doc.pdf")
    assert source.type == "file"
    assert source.location == "/path/to/doc.pdf"


def test_input_source_bytes():
    """Test InputSource with bytes type."""
    from pdf_reader.adapters.core import InputSource
    
    data = b"fake pdf content"
    source = InputSource(type="bytes", data=data)
    assert source.type == "bytes"
    assert source.data == data


def test_input_source_validation():
    """Test InputSource validation."""
    from pdf_reader.adapters.core import InputSource
    
    # bytes type requires data field
    with pytest.raises(ValueError, match="requires 'data' field"):
        InputSource(type="bytes")
    
    # non-bytes types require location field
    with pytest.raises(ValueError, match="requires 'location' field"):
        InputSource(type="file")


def test_output_sink_filesystem():
    """Test OutputSink with filesystem type."""
    from pdf_reader.adapters.core import OutputSink
    
    sink = OutputSink(type="filesystem", location="/output/dir")
    assert sink.type == "filesystem"
    assert sink.location == "/output/dir"


def test_adapter_config_creation():
    """Test AdapterConfig creation."""
    from pdf_reader.adapters.core import AdapterConfig, InputSource, OutputSink
    from pdf_reader.pipeline import PipelineConfig
    
    config = AdapterConfig(
        input_source=InputSource(type="file", location="doc.pdf"),
        output_sink=OutputSink(type="filesystem", location="output/"),
        pipeline_config=PipelineConfig(extraction_preset="offline"),
    )
    
    assert config.input_source is not None
    assert config.output_sink is not None
    assert config.pipeline_config is not None
    assert config.run_id is not None  # Auto-generated


def test_adapter_config_run_id_generation():
    """Test that run_id is auto-generated with correct format."""
    from pdf_reader.adapters.core import AdapterConfig, InputSource, OutputSink
    from pdf_reader.pipeline import PipelineConfig
    
    config = AdapterConfig(
        input_source=InputSource(type="file", location="doc.pdf"),
        output_sink=OutputSink(type="filesystem", location="output/"),
        pipeline_config=PipelineConfig(extraction_preset="offline"),
    )
    
    assert config.run_id.startswith("run_")
    assert len(config.run_id.split("_")) == 3  # run_timestamp_uuid


def test_airflow_operator_import():
    """Test that Airflow operator can be imported (if Airflow installed)."""
    pytest.importorskip("airflow", reason="Airflow not installed")
    
    from pdf_reader.adapters.airflow import PdfExtractionOperator
    
    assert PdfExtractionOperator is not None


def test_airflow_operator_instantiation():
    """Test Airflow operator instantiation."""
    pytest.importorskip("airflow", reason="Airflow not installed")
    
    from pdf_reader.adapters.airflow import PdfExtractionOperator
    
    operator = PdfExtractionOperator(
        task_id="test_extract",
        input_path="/path/to/doc.pdf",
        output_dir="/output",
    )
    
    assert operator.task_id == "test_extract"
    assert operator.input_path == "/path/to/doc.pdf"
    assert operator.output_dir == "/output"


def test_prefect_flow_import():
    """Test that Prefect flow can be imported (if Prefect installed)."""
    pytest.importorskip("prefect", reason="Prefect not installed")
    
    from pdf_reader.adapters.prefect import extract_tables_flow, extract_tables_task
    
    assert extract_tables_flow is not None
    assert extract_tables_task is not None


def test_http_service_import():
    """Test that HTTP service can be imported (if FastAPI installed)."""
    pytest.importorskip("fastapi", reason="FastAPI not installed")
    
    from pdf_reader.adapters.http.service import app
    
    assert app is not None


@pytest.mark.integration
def test_run_extraction_with_adapter(tmp_path, sample_pdf_bytes):
    """Test end-to-end extraction using adapter API."""
    from pdf_reader.adapters.core import AdapterConfig, InputSource, OutputSink, run_extraction
    from pdf_reader.pipeline import PipelineConfig
    
    # Create temporary PDF file
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(sample_pdf_bytes)
    
    # Create adapter config
    config = AdapterConfig(
        input_source=InputSource(type="file", location=str(pdf_path)),
        output_sink=OutputSink(type="filesystem", location=str(tmp_path / "output")),
        pipeline_config=PipelineConfig(
            dpi=150,  # Lower DPI for faster test
            enable_debug_artifacts=False,
            extraction_preset="offline",
        ),
    )
    
    # Run extraction
    result = run_extraction(config)
    
    # Verify results
    assert result is not None
    assert result.stats.pages_processed >= 0
    
    # Verify output files were created
    output_dir = tmp_path / "output" / config.run_id
    assert output_dir.exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "run_stats.json").exists()


# Fixtures
@pytest.fixture
def sample_pdf_bytes():
    """Generate minimal valid PDF bytes for testing."""
    # Minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
189
%%EOF
"""
    return pdf_content

