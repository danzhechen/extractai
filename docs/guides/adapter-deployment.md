## Deployment Guide for Integration Adapters

This guide provides detailed deployment instructions for each adapter type.

---

## Airflow Deployment

### Prerequisites

- Apache Airflow 2.5.0 or later
- Python 3.10+
- Access to Airflow installation directory

### Installation Steps

1. **Install dependencies:**
   ```bash
   # In Airflow's Python environment
   pip install pdf-reader apache-airflow>=2.5.0
   ```

2. **Copy DAG file:**
   ```bash
   # Copy example DAG to Airflow DAGs directory
   cp examples/integrations/airflow_dag.py $AIRFLOW_HOME/dags/
   ```

3. **Create config file:**
   ```bash
   # Create production config
   mkdir -p configs
   cat > configs/production.yaml <<EOF
   dpi: 300
   enable_debug_artifacts: false
   llm_fallback_enabled: true
   log_level: INFO
   worker_type: thread
   max_workers: 4
   EOF
   ```

4. **Test DAG:**
   ```bash
   # List DAGs
   airflow dags list
   
   # Test DAG
   airflow dags test pdf_extraction_pipeline 2025-01-01
   ```

5. **Trigger DAG:**
   ```bash
   # Manual trigger with parameters
   airflow dags trigger pdf_extraction_pipeline \
       --conf '{"pdf_path": "/data/document.pdf", "output_dir": "/data/output"}'
   ```

### Production Configuration

For production deployments, configure:

- **Executor**: Use CeleryExecutor or KubernetesExecutor for distributed execution
- **Database**: Use PostgreSQL or MySQL (not SQLite)
- **Secrets**: Use Airflow Connections for credentials
- **Monitoring**: Enable StatsD and Flower

---

## Prefect Deployment

### Prerequisites

- Prefect 2.10.0 or later
- Python 3.10+
- Prefect Cloud account (optional, for cloud deployment)

### Installation Steps

1. **Install dependencies:**
   ```bash
   pip install pdf-reader prefect>=2.10.0
   ```

2. **Login to Prefect Cloud (optional):**
   ```bash
   prefect cloud login
   ```

3. **Create configuration blocks:**
   ```bash
   python examples/integrations/prefect_deployment.py --mode setup-blocks
   ```

4. **Test flow locally:**
   ```bash
   python examples/integrations/prefect_deployment.py --mode local
   ```

5. **Deploy flow:**
   ```bash
   python examples/integrations/prefect_deployment.py --mode deploy
   ```

### Work Pools

#### Process Work Pool (Local)

```bash
# Create work pool
prefect work-pool create local-pool --type process

# Start worker
prefect worker start --pool local-pool
```

#### Kubernetes Work Pool

```bash
# Create work pool
prefect work-pool create k8s-pool --type kubernetes

# Configure Kubernetes manifest
prefect work-pool set-manifest k8s-pool --file k8s-manifest.yaml

# Deploy agent
kubectl apply -f prefect-agent.yaml
```

### Scheduling

```python
from prefect.server.schemas.schedules import CronSchedule

deployment = Deployment.build_from_flow(
    flow=extract_tables_flow,
    name="pdf-extraction-hourly",
    schedule=CronSchedule(cron="0 * * * *"),
)

deployment.apply()
```

---

## HTTP Service Deployment

### Local Development

1. **Install dependencies:**
   ```bash
   pip install pdf-reader fastapi uvicorn[standard] python-multipart
   ```

2. **Start service:**
   ```bash
   uvicorn pdf_reader.adapters.http.service:app --reload --port 8000
   ```

3. **Access API docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Build image:**
   ```bash
   docker build -f src/pdf_reader/adapters/http/Dockerfile -t pdf-extraction-api:latest .
   ```

2. **Run container:**
   ```bash
   docker run -d \
       -p 8000:8000 \
       -v /data/output:/data/output \
       -e LOG_LEVEL=INFO \
       --name pdf-extraction-api \
       pdf-extraction-api:latest
   ```

3. **Test service:**
   ```bash
   curl http://localhost:8000/health
   ```

### Docker Compose Deployment

1. **Start services:**
   ```bash
   cd src/pdf_reader/adapters/http
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f pdf-extraction-api
   ```

3. **Stop services:**
   ```bash
   docker-compose down
   ```

### Cloud Deployment

#### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/pdf-extraction-api

# Deploy to Cloud Run
gcloud run deploy pdf-extraction-api \
    --image gcr.io/PROJECT_ID/pdf-extraction-api \
    --platform managed \
    --region us-central1 \
    --memory 4Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --allow-unauthenticated

# Get service URL
gcloud run services describe pdf-extraction-api --format='value(status.url)'
```

#### AWS ECS Fargate

```bash
# Create ECR repository
aws ecr create-repository --repository-name pdf-extraction-api

# Build and push image
aws ecr get-login-password | docker login --username AWS --password-stdin ECR_URL
docker tag pdf-extraction-api:latest ECR_URL/pdf-extraction-api:latest
docker push ECR_URL/pdf-extraction-api:latest

# Create task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create service
aws ecs create-service --cli-input-json file://ecs-service.json
```

Example `ecs-task-definition.json`:

```json
{
  "family": "pdf-extraction-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "ECR_URL/pdf-extraction-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/pdf-extraction-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pdf-extraction-api
  labels:
    app: pdf-extraction-api
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
        env:
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: pdf-extraction-api
spec:
  selector:
    app: pdf-extraction-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pdf-extraction-api
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: pdf-extraction-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pdf-extraction-api
            port:
              number: 80
```

Deploy:

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
```

---

## Production Considerations

### Monitoring

#### Metrics

- **Airflow**: Use StatsD exporter + Prometheus
- **Prefect**: Built-in metrics in Prefect Cloud
- **HTTP Service**: Add Prometheus metrics endpoint

#### Logging

- Use structured logging (JSON format)
- Centralize logs (CloudWatch, Stackdriver, ELK)
- Set up alerts for errors

### Security

#### Authentication

- **Airflow**: Use RBAC and authentication backends
- **Prefect**: Use Prefect Cloud authentication
- **HTTP Service**: Add JWT or API key authentication

Example JWT middleware:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT token
    if not verify_jwt(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

#### Network Security

- Use HTTPS/TLS for external endpoints
- Restrict network access with security groups/firewalls
- Use VPC/private subnets for internal services

### Scaling

#### Horizontal Scaling

- **Airflow**: Add more Celery workers
- **Prefect**: Increase work pool concurrency
- **HTTP Service**: Deploy multiple instances behind load balancer

#### Vertical Scaling

- Increase CPU/memory for individual instances
- Configure `max_workers` in pipeline config

### Cost Optimization

- Use spot/preemptible instances for batch workloads
- Set up auto-scaling based on queue depth
- Use lifecycle policies for output artifacts (archive to cold storage)

---

## Troubleshooting

### Common Issues

#### High Memory Usage

**Solution**: Reduce `dpi`, limit `max_workers`, or enable streaming for large PDFs.

#### Slow Processing

**Solution**: Enable parallel processing (Story 3.1), use faster hardware, or reduce quality settings.

#### Import Errors

**Solution**: Ensure all dependencies are installed in correct Python environment.

#### Permission Errors

**Solution**: Check file permissions, run as appropriate user, configure IAM roles for cloud storage.

---

**Last Updated**: 2025-11-21


