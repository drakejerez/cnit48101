# Microservices Application

A microservices-based application with Application, Auth, and Database services, ready for OpenTelemetry instrumentation.

## Services

- **app-service** (Port 8080): Main application service that orchestrates requests
- **auth-service** (Port 8081): JWT-based authentication service
- **db-service** (Port 8082): SQLite database service

## Quick Start

### 1. Check Prerequisites
```bash
./check-prereqs.sh
```

### 2. Setup Local Kubernetes Cluster (if needed)

**Option A: Using minikube**
```bash
# Install minikube (if not installed)
brew install minikube

# Start minikube cluster
minikube start

# Verify cluster is running
kubectl cluster-info
```

**Option B: Using kind**
```bash
# Install kind (if not installed)
brew install kind

# Create kind cluster
kind create cluster --name microservices

# Verify cluster is running
kubectl cluster-info
```

### 3. Deploy
```bash
# Build images, load to cluster, and deploy
make deploy

# Or use the deployment script
./deploy.sh
```

## Kubernetes Deployment

### Prerequisites
- Docker running
- Kubernetes cluster (minikube, kind, or cloud)
- kubectl installed and configured

### Build Images

```bash
# Build all images
make build-all

# Or build individually
make build-app
make build-auth
make build-db
```

### Load Images to Cluster

For **minikube**:
```bash
minikube image load db-service:latest
minikube image load auth-service:latest
minikube image load app-service:latest
```

For **kind**:
```bash
kind load docker-image db-service:latest
kind load docker-image auth-service:latest
kind load docker-image app-service:latest
```

### Deploy to Kubernetes

```bash
# Deploy all resources
make k8s-deploy

# Or manually
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/auth-deployment.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### Access Services

```bash
# Port forward to access services
kubectl port-forward -n microservices svc/app-service 8080:8080
kubectl port-forward -n microservices svc/auth-service 8081:8081
kubectl port-forward -n microservices svc/db-service 8082:8082

# Or use NodePort (app-service-nodeport on port 30080)
kubectl get svc -n microservices
```

### Check Status

```bash
# Check pods
kubectl get pods -n microservices

# Check services
kubectl get svc -n microservices

# View logs
kubectl logs -n microservices -l app=app-service
kubectl logs -n microservices -l app=auth-service
kubectl logs -n microservices -l app=db-service
```

### Cleanup

```bash
make k8s-delete
```

## Testing

### Get Authentication Token

```bash
curl -X POST http://localhost:8081/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### Test Application Endpoints

```bash
# Set token variable
TOKEN="your-token-here"

# List presets
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/presets

# Get preset data
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/preset/welcome

# Create data
curl -X POST http://localhost:8080/api/data \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "value": 42}'

# Seed database
curl -X POST http://localhost:8080/api/seed \
  -H "Authorization: Bearer $TOKEN"
```

## Default Users

- username: `admin`, password: `admin123`
- username: `user1`, password: `password1`
- username: `testuser`, password: `testpass`

## Environment Variables

### App Service
- `AUTH_SERVICE_URL`: Auth service URL (default: http://localhost:8081, Kubernetes: http://auth-service:8081)
- `DB_SERVICE_URL`: DB service URL (default: http://localhost:8082, Kubernetes: http://db-service:8082)

### Auth Service
- `JWT_SECRET`: JWT secret key
- `DB_SERVICE_URL`: DB service URL (default: http://localhost:8082, Kubernetes: http://db-service:8082)

### DB Service
- `DB_PATH`: Database file path (default: /data/app.db)
- `ARTIFICIAL_LATENCY_MS`: Artificial latency in milliseconds (default: 100)

Note: In Kubernetes, service URLs are automatically set via environment variables in the deployment manifests.

## Next Steps

Ready for OpenTelemetry instrumentation!

