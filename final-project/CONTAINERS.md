# Container Breakdown

## What Gets Deployed

### 3 Microservice Containers
1. **app-service** (`app-service:latest`)
   - Main application orchestrator
   - Port: 8080
   - Calls auth and db services

2. **auth-service** (`auth-service:latest`)
   - JWT authentication service
   - Port: 8081
   - Queries db-service for user credentials

3. **db-service** (`db-service:latest`)
   - **This IS the database** (SQLite)
   - Port: 8082
   - Contains SQLite database file (`/data/app.db`)
   - Provides REST API for data operations
   - Pre-populated with users and items

### 3 OpenTelemetry Collector Sidecars
- One sidecar container in each service pod:
  - `otel/opentelemetry-collector-contrib:0.91.0`
  - Collects traces and metrics from the service
  - Exports to Jaeger (traces) and Prometheus (metrics)
  - Port: 4317 (OTLP gRPC)

### 1 Jaeger Container
- **jaeger** (`jaegertracing/all-in-one:1.50`)
  - Distributed tracing visualization
  - Ports: 16686 (UI), 14250 (gRPC), 9411 (Zipkin)
  - Receives traces from OTEL collectors

### 1 Prometheus Container
- **prometheus** (`prom/prometheus:v2.45.0`)
  - Metrics collection and monitoring
  - Port: 9090
  - Scrapes metrics from OTEL collectors

## Total Container Count

**8 containers total:**
- 3 service containers (app, auth, db)
- 3 OTEL collector sidecars (one per service)
- 1 Jaeger
- 1 Prometheus

## Note on Database

The **db-service IS the database** - it's not a separate container. It runs SQLite internally and exposes a REST API. The database file is stored in a volume (`/data/app.db`).

## Pod Structure

Each service pod contains 2 containers:
- Service container (app/auth/db)
- OTEL collector sidecar

Jaeger and Prometheus run in their own separate pods.

