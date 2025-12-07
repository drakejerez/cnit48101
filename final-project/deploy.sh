#!/bin/bash

set -e

echo "=========================================="
echo "Kubernetes Microservices Deployment"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Build images
echo ""
echo "Building Docker images..."
docker build -f Dockerfile.db -t db-service:latest .
docker build -f Dockerfile.auth -t auth-service:latest .
docker build -f Dockerfile.app -t app-service:latest .

echo ""
echo "✅ Images built successfully!"

# Load images to cluster
echo ""
echo "Loading images to Kubernetes cluster..."
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    echo "Detected minikube, loading images..."
    minikube image load db-service:latest
    minikube image load auth-service:latest
    minikube image load app-service:latest
elif command -v kind &> /dev/null; then
    echo "Detected kind, loading images..."
    kind load docker-image db-service:latest
    kind load docker-image auth-service:latest
    kind load docker-image app-service:latest
else
    echo "⚠️  Could not detect minikube or kind."
    echo "Please load images manually or push to a container registry."
    echo "For minikube: minikube image load <image-name>"
    echo "For kind: kind load docker-image <image-name>"
fi

# Deploy to Kubernetes
echo ""
echo "Deploying to Kubernetes..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/auth-deployment.yaml
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/ingress.yaml

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=db-service -n microservices --timeout=60s || true
kubectl wait --for=condition=ready pod -l app=auth-service -n microservices --timeout=60s || true
kubectl wait --for=condition=ready pod -l app=app-service -n microservices --timeout=60s || true

echo ""
echo "Pod status:"
kubectl get pods -n microservices

echo ""
echo "To access services:"
echo "  kubectl port-forward -n microservices svc/app-service 8080:8080"
echo "  kubectl port-forward -n microservices svc/auth-service 8081:8081"
echo "  kubectl port-forward -n microservices svc/db-service 8082:8082"
echo ""
echo "Or use NodePort (app-service-nodeport on port 30080)"
echo ""
echo "View logs: kubectl logs -n microservices -l app=<service-name>"

