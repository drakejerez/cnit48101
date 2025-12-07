# Microservices with OpenTelemetry

Three microservices (app, auth, db) with OpenTelemetry instrumentation, deployed on Kubernetes.

## Services

- **app-service** (8080): Main application orchestrator
- **auth-service** (8081): JWT authentication
- **db-service** (8082): SQLite database

## Quick Start

```bash
# Check prerequisites
./check-prereqs.sh

# Deploy everything
make deploy

# Or manually:
make build-all
make k8s-load-images
make k8s-deploy
```

## Access

```bash
# Port forward services
kubectl port-forward -n microservices svc/app-service 8080:8080
kubectl port-forward -n microservices svc/auth-service 8081:8081

# Jaeger UI (traces)
minikube service -n microservices jaeger-query

# Prometheus (metrics)
minikube service -n microservices prometheus
```

## Testing

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8081/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.token')

# Test endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/presets

# Generate traffic
python3 traffic-generator.py --duration 60 --threads 10
```

## Telemetry

- **Traces**: OTLP → Collector sidecar → Zipkin → Jaeger
- **Metrics**: OTLP → Collector sidecar → Prometheus
- **Collector**: Sidecar in each pod (port 4317)

## Default Users

- `admin` / `admin123`
- `user1` / `password1`
- `testuser` / `testpass`
