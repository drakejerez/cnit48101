# Kubernetes Deployment Guide

## File Structure

```
final-project/
├── app.py                 # Application service
├── auth.py                # Authentication service  
├── db.py                  # Database service
├── requirements.txt       # Python dependencies
├── Dockerfile.app         # App service Dockerfile
├── Dockerfile.auth        # Auth service Dockerfile
├── Dockerfile.db          # DB service Dockerfile
├── k8s/                   # Kubernetes manifests
│   ├── namespace.yaml
│   ├── db-deployment.yaml
│   ├── auth-deployment.yaml
│   ├── app-deployment.yaml
│   └── ingress.yaml
├── Makefile              # Build/deploy commands
├── deploy.sh             # Quick deployment script
└── README.md             # Documentation
```

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster running (minikube, kind, or cloud)
- kubectl configured
- Docker images built

### Step 1: Build Images
```bash
make build-all
# Or individually:
docker build -f Dockerfile.db -t db-service:latest .
docker build -f Dockerfile.auth -t auth-service:latest .
docker build -f Dockerfile.app -t app-service:latest .
```

### Step 2: Load Images to Cluster

**For minikube:**
```bash
minikube image load db-service:latest
minikube image load auth-service:latest
minikube image load app-service:latest
```

**For kind:**
```bash
kind load docker-image db-service:latest
kind load docker-image auth-service:latest
kind load docker-image app-service:latest
```

**For other clusters:**
Push images to a registry and update imagePullPolicy in manifests.

### Step 3: Deploy
```bash
make k8s-deploy
# Or manually:
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/auth-deployment.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### Step 4: Verify Deployment
```bash
# Check pods
kubectl get pods -n microservices

# Check services
kubectl get svc -n microservices

# Check logs
kubectl logs -n microservices -l app=app-service
kubectl logs -n microservices -l app=auth-service
kubectl logs -n microservices -l app=db-service
```

### Step 5: Access Services

**Port Forward:**
```bash
kubectl port-forward -n microservices svc/app-service 8080:8080
kubectl port-forward -n microservices svc/auth-service 8081:8081
kubectl port-forward -n microservices svc/db-service 8082:8082
```

**NodePort (app-service only):**
```bash
# Get node IP
minikube ip  # for minikube
# Access at: http://<node-ip>:30080
```

### Cleanup
```bash
make k8s-delete
# Or manually:
kubectl delete -f k8s/
```

## Service URLs

### Kubernetes
- Services communicate via service names: `http://db-service.microservices.svc.cluster.local:8082`
- Short form: `http://db-service:8082` (within same namespace)
- External access via NodePort (30080) or port-forward

## Testing

After deployment, test with:

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8081/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.token')

# Test endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/presets
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/preset/welcome
curl -X POST http://localhost:8080/api/seed -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

### Kubernetes
- Check pod status: `kubectl describe pod <pod-name> -n microservices`
- Check events: `kubectl get events -n microservices --sort-by='.lastTimestamp'`
- Debug pod: `kubectl exec -it <pod-name> -n microservices -- /bin/sh`
- Check service endpoints: `kubectl get endpoints -n microservices`

### Common Issues
1. **Images not found**: Load images to cluster or push to registry
2. **Services can't connect**: Check service names and ports match
3. **Health checks failing**: Increase initialDelaySeconds in deployment
4. **Database not persisting**: Check volume mounts in Kubernetes

