"""
Integration tests for HTTP service adapter.

These tests use FastAPI TestClient to test the HTTP endpoints without
starting an actual server.
"""

import io
import json
import pytest
from pathlib import Path


pytestmark = pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed"
)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from pdf_reader.adapters.http.service import app
    
    return TestClient(app)


@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a sample PDF file for testing."""
    # Minimal valid PDF
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
    
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(pdf_content)
    return pdf_path


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert "jobs_queued" in data


def test_extract_endpoint_file_upload(client, sample_pdf_file):
    """Test extraction endpoint with file upload."""
    # Upload PDF file
    with open(sample_pdf_file, "rb") as f:
        response = client.post(
            "/extract",
            files={"file": ("test.pdf", f, "application/pdf")},
        )
    
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"


def test_extract_endpoint_with_config(client, sample_pdf_file):
    """Test extraction endpoint with custom config."""
    config = {
        "dpi": 300,
        "enable_debug_artifacts": True,
    }
    
    with open(sample_pdf_file, "rb") as f:
        response = client.post(
            "/extract",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"config": json.dumps(config)},
        )
    
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


def test_extract_endpoint_invalid_file(client):
    """Test extraction endpoint with invalid file type."""
    # Try to upload a non-PDF file
    response = client.post(
        "/extract",
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    
    assert response.status_code == 400


def test_extract_endpoint_no_file(client):
    """Test extraction endpoint without file."""
    response = client.post("/extract")
    
    assert response.status_code == 400


def test_status_endpoint(client, sample_pdf_file):
    """Test status endpoint."""
    # Submit job
    with open(sample_pdf_file, "rb") as f:
        response = client.post(
            "/extract",
            files={"file": ("test.pdf", f, "application/pdf")},
        )
    
    job_id = response.json()["job_id"]
    
    # Get status
    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert "status" in data
    assert "progress" in data


def test_status_endpoint_invalid_job(client):
    """Test status endpoint with invalid job ID."""
    response = client.get("/status/invalid-job-id")
    
    assert response.status_code == 404


def test_results_endpoint(client, sample_pdf_file):
    """Test results endpoint."""
    # Submit job
    with open(sample_pdf_file, "rb") as f:
        response = client.post(
            "/extract",
            files={"file": ("test.pdf", f, "application/pdf")},
        )
    
    job_id = response.json()["job_id"]
    
    # Get results (may not be ready yet)
    response = client.get(f"/results/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id


def test_results_endpoint_invalid_job(client):
    """Test results endpoint with invalid job ID."""
    response = client.get("/results/invalid-job-id")
    
    assert response.status_code == 404


def test_openapi_docs(client):
    """Test that OpenAPI docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc(client):
    """Test that ReDoc is available."""
    response = client.get("/redoc")
    assert response.status_code == 200


