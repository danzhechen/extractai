# Integration Adapters Guide

This guide covers how to integrate the PDF table extraction pipeline with common workflow orchestration frameworks and deploy it as an HTTP service.

## Overview

The extraction pipeline provides first-class adapters for:

1. **Airflow** - Apache Airflow operator for DAG integration
2. **Prefect** - Prefect 2.x flows and tasks
3. **HTTP Service** - Lightweight FastAPI-based REST API

All adapters share a common abstraction layer (`AdapterConfig`, `InputSource`, `OutputSink`) for consistent configuration and artifact management.

---

## Installation

Install adapters as optional dependencies:

```bash
# Install Airflow support
pip install pdf-reader[airflow]

# Install Prefect support
pip install pdf-reader[prefect]

# Install HTTP service support
pip install pdf-reader[http]

# Install all integrations
pip install pdf-reader[integrations]
```

---

## Airflow Integration

### Quick Start

```python
from airflow import DAG
from pdf_reader.adapters.airflow import PdfExtractionOperator
from datetime import datetime

with DAG("pdf_extraction", start_date=datetime(2025, 1, 1)):
    extract = PdfExtractionOperator(
        task_id="extract_tables",
        input_path="{{ params.pdf_path }}",
        output_dir="{{ params.output_dir }}",
        config_path="configs/production.yaml",
    )
```

### Operator Parameters

- **input_path** (str): Path to PDF file (supports Jinja2 templating)
- **output_dir** (str): Output directory (supports Jinja2 templating)
- **config_path** (Optional[str]): Path to YAML config file
- **pipeline_config** (Optional[Dict]): Config overrides
- **push_results** (bool): Push summary to XCom (default: True)
- **metadata** (Optional[Dict]): Additional metadata

### XCom Output

The operator pushes a summary dict to XCom with keys:
- `tables_extracted`: Number of tables extracted
- `pages_processed`: Number of pages processed
- `elapsed_seconds`: Execution time
- `run_id`: Unique run identifier
- `output_dir`: Output directory path

### Example DAG

See `examples/integrations/airflow_dag.py` for comprehensive examples including:
- File sensor patterns
- Batch processing
- Post-processing tasks
- Error handling

### Deployment

#### LocalExecutor

```bash
# Set Airflow home
export AIRFLOW_HOME=~/airflow

# Initialize database
airflow db init

# Copy DAG file
cp examples/integrations/airflow_dag.py $AIRFLOW_HOME/dags/

# Start webserver and scheduler
airflow webserver --port 8080 &
airflow scheduler &
```

#### CeleryExecutor

For distributed execution:

```bash
# Start Celery worker
airflow celery worker

# Start flower (monitoring)
airflow celery flower
```

---

## Prefect Integration

### Quick Start

```python
from pdf_reader.adapters.prefect import extract_tables_flow

# Run locally
result = extract_tables_flow(
    input_path="document.pdf",
    output_dir="output/",
)

print(f"Extracted {result['tables_extracted']} tables")
```

### Flow Parameters

- **input_path** (str): Path to PDF file
- **output_dir** (str): Output directory
- **config** (Optional[PipelineConfig]): Pipeline configuration
- **config_block_name** (Optional[str]): Name of Prefect JSON block with config
- **run_id** (Optional[str]): Run identifier
- **metadata** (Optional[Dict]): Additional metadata

### Configuration Blocks

Store configuration in Prefect blocks:

```python
from prefect.blocks.system import JSON

# Create config block
config = {
    "dpi": 300,
    "enable_debug_artifacts": True,
}

json_block = JSON(value=config)
json_block.save("pdf-extraction-config")

# Use in flow
result = extract_tables_flow(
    input_path="document.pdf",
    output_dir="output/",
    config_block_name="pdf-extraction-config",
)
```

### Batch Processing

```python
from pdf_reader.adapters.prefect import batch_extract_tables_flow

result = batch_extract_tables_flow(
    input_paths=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
    output_dir="output/",
)

print(f"{result['successful']}/{result['total_files']} files processed")
```

### Deployment

#### Local Deployment

```python
from prefect.deployments import Deployment
from pdf_reader.adapters.prefect import extract_tables_flow

deployment = Deployment.build_from_flow(
    flow=extract_tables_flow,
    name="pdf-extraction",
    version="1.0.0",
)

deployment.apply()
```

#### Prefect Cloud

```bash
# Login to Prefect Cloud
prefect cloud login

# Deploy flow
python examples/integrations/prefect_deployment.py --mode deploy
```

#### Kubernetes Work Pool

```python
deployment = Deployment.build_from_flow(
    flow=extract_tables_flow,
    name="pdf-extraction-k8s",
    work_pool_name="kubernetes",
)

deployment.apply()
```

### Scheduling

```python
from prefect.server.schemas.schedules import CronSchedule

deployment = Deployment.build_from_flow(
    flow=batch_extract_tables_flow,
    name="pdf-extraction-daily",
    schedule=CronSchedule(cron="0 2 * * *"),  # Daily at 2 AM
)

deployment.apply()
```

---

## HTTP Service

### Quick Start

```bash
# Start service
uvicorn pdf_reader.adapters.http.service:app --host 0.0.0.0 --port 8000

# Submit extraction job
curl -X POST http://localhost:8000/extract \
    -F "file=@document.pdf"
```

### API Endpoints

#### POST /extract

Submit extraction job.

**Request:**
```bash
curl -X POST http://localhost:8000/extract \
    -F "file=@document.pdf" \
    -F 'config={"dpi": 300}'
```

**Response:**
```json
{
  "job_id": "abc123",
  "status": "queued",
  "message": "Extraction job abc123 queued successfully"
}
```

#### GET /status/{job_id}

Get job status.

**Request:**
```bash
curl http://localhost:8000/status/abc123
```

**Response:**
```json
{
  "job_id": "abc123",
  "status": "processing",
  "progress": 0.5,
  "created_at": "2025-11-21T10:00:00",
  "started_at": "2025-11-21T10:00:05"
}
```

#### GET /results/{job_id}

Get extraction results.

**Request:**
```bash
curl http://localhost:8000/results/abc123
```

**Response:**
```json
{
  "job_id": "abc123",
  "status": "completed",
  "tables_extracted": 3,
  "pages_processed": 5,
  "elapsed_seconds": 12.5,
  "output_dir": "/tmp/pdf_extractions/abc123",
  "tables": [...]
}
```

#### GET /health

Health check.

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "jobs_queued": 2,
  "jobs_processing": 1,
  "jobs_completed": 10,
  "jobs_failed": 0
}
```

### Python Client

```python
from pdf_reader.adapters.http import PdfExtractionClient

client = PdfExtractionClient("http://localhost:8000")

# Submit job
job_id = client.submit_extraction("document.pdf")

# Wait for completion
result = client.wait_for_completion(job_id)

# Get results
results = client.get_results(job_id)
print(f"Extracted {results['tables_extracted']} tables")
```

See `examples/integrations/http_client_example.py` for more examples.

### Docker Deployment

```bash
# Build image
docker build -f src/pdf_reader/adapters/http/Dockerfile -t pdf-extraction-api .

# Run container
docker run -p 8000:8000 pdf-extraction-api
```

### Docker Compose

```bash
# Start all services
docker-compose -f src/pdf_reader/adapters/http/docker-compose.yml up
```

This starts:
- PDF extraction API (port 8000)
- Redis (for job storage, optional)
- Nginx (reverse proxy, optional)

### Cloud Deployment

#### Google Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/pdf-extraction-api

# Deploy
gcloud run deploy pdf-extraction-api \
    --image gcr.io/PROJECT_ID/pdf-extraction-api \
    --platform managed \
    --region us-central1 \
    --memory 4Gi \
    --cpu 2 \
    --timeout 300
```

#### AWS ECS

```bash
# Push image to ECR
docker tag pdf-extraction-api:latest AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/pdf-extraction-api:latest
docker push AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/pdf-extraction-api:latest

# Create ECS task definition and service (using AWS Console or CLI)
```

#### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pdf-extraction-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pdf-extraction-api
  template:
    metadata:
      labels:
        app: pdf-extraction-api
    spec:
      containers:
      - name: api
        image: pdf-extraction-api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

---

## Common Patterns

### Configuration Management

All adapters support layered configuration:

1. **Base config** - Default `PipelineConfig()` values
2. **Config file** - YAML file loaded by adapter
3. **Programmatic overrides** - Dict passed to adapter
4. **Environment variables** - Via `PDF_READER_*` env vars

Priority: Environment > Programmatic > File > Base

### Error Handling

All adapters implement graceful error handling:

- Jobs/tasks fail without crashing the orchestrator
- Error messages are captured and surfaced
- Partial results are preserved when possible

### Idempotency

Adapters are designed for idempotent execution:

- Run IDs prevent output clobbering
- Manifest files enable result verification
- Retry-safe (same input produces same output)

### Artifact Layout

All adapters produce the same artifact layout:

```
runs/{run_id}/
  manifest.json          # Run manifest with metadata
  config.yaml            # Pipeline config snapshot
  run_stats.json         # Execution statistics
  tables/
    table_0.csv
    table_1.csv
  debug/                 # If debug enabled
    page_0_overlay.png
    page_1_overlay.png
```

---

## Trade-offs and Considerations

### Batch vs. Online Processing

- **Batch (Airflow/Prefect)**: Best for scheduled, large-scale processing
  - Pros: Better resource management, monitoring, retry logic
  - Cons: Higher setup overhead, latency for ad-hoc requests

- **Online (HTTP Service)**: Best for on-demand, low-latency requests
  - Pros: Simple integration, immediate feedback
  - Cons: Resource spikes, no built-in scheduling

### Scaling Patterns

- **Horizontal**: Deploy multiple HTTP service instances behind load balancer
- **Vertical**: Increase CPU/memory for parallel page processing (Story 3.1)
- **Hybrid**: Use HTTP service for API, trigger Prefect flows for heavy jobs

### Cost Considerations

- **Cloud Run/Lambda**: Pay-per-use, auto-scaling (best for sporadic workloads)
- **ECS/Kubernetes**: Reserved capacity (best for predictable workloads)
- **On-premise**: Fixed cost (best for high volume or data sensitivity)

---

## Troubleshooting

### Airflow: Task fails with import error

**Problem**: `ModuleNotFoundError: No module named 'pdf_reader'`

**Solution**: Ensure `pdf-reader` is installed in Airflow's Python environment:

```bash
# In Airflow environment
pip install pdf-reader[airflow]
```

### Prefect: Flow runs but doesn't process files

**Problem**: Flow completes but no tables extracted.

**Solution**: Check Prefect logs for errors. Verify input paths are absolute and accessible from worker.

### HTTP Service: Jobs stuck in "queued" status

**Problem**: Jobs never start processing.

**Solution**: Check if background tasks are running. Restart service:

```bash
uvicorn pdf_reader.adapters.http.service:app --reload
```

### All Adapters: Out of memory errors

**Problem**: Large PDFs cause OOM errors.

**Solution**: Reduce `dpi` setting, limit `max_workers`, or increase container memory.

---

## Next Steps

- See `examples/integrations/` for runnable examples
- Check Story 3.1 for parallel processing configuration
- Review Story 3.3 for manifest-based reproducibility
- Consult troubleshooting guide for common issues

---

**Last Updated**: 2025-11-21


