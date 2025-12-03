#!/bin/bash
set -euo pipefail

echo "Deploying Kubernetes Tutorial Application"
echo "=========================================="

# Set kubectl context (should already be set from cloud-init)
export KUBECONFIG=/home/ubuntu/.kube/config

# Wait for cluster to be ready
echo "[STEP 1] Waiting for cluster to be ready..."
kubectl wait --for=condition=ready node --all --timeout=300s

# Create a Deployment (from Kubernetes basics tutorial)
echo "[STEP 2] Creating Deployment..."
kubectl create deployment kubernetes-bootcamp --image=gcr.io/google-samples/kubernetes-bootcamp:v1

# Wait for deployment to be ready
echo "[STEP 3] Waiting for Deployment to be ready..."
kubectl wait --for=condition=available deployment/kubernetes-bootcamp --timeout=300s

# Expose the Deployment as a Service
echo "[STEP 4] Exposing Deployment as a Service..."
kubectl expose deployment/kubernetes-bootcamp --type="LoadBalancer" --port 8080

# Wait for service to get an external IP (from MetalLB)
echo "[STEP 5] Waiting for Service to get external IP..."
sleep 30

# Scale the deployment (part of the tutorial)
echo "[STEP 6] Scaling Deployment to 3 replicas..."
kubectl scale deployment/kubernetes-bootcamp --replicas=3

# Wait for pods to be ready
echo "[STEP 7] Waiting for Pods to be ready..."
kubectl wait --for=condition=ready pod -l app=kubernetes-bootcamp --timeout=300s

# Get Pod name
POD_NAME=$(kubectl get pods -l app=kubernetes-bootcamp -o jsonpath='{.items[0].metadata.name}')

echo ""
echo "=========================================="
echo "Dumping YAML files"
echo "=========================================="

# Dump Pod YAML
echo "[OUTPUT] Pod YAML:"
echo "---"
kubectl get pod $POD_NAME -o yaml

echo ""
echo "=========================================="

# Dump Deployment YAML
echo "[OUTPUT] Deployment YAML:"
echo "---"
kubectl get deployment kubernetes-bootcamp -o yaml

echo ""
echo "=========================================="

# Dump Service YAML
echo "[OUTPUT] Service YAML:"
echo "---"
kubectl get service kubernetes-bootcamp -o yaml

echo ""
echo "=========================================="
echo "Tutorial deployment complete!"
echo "=========================================="

# Show status
echo ""
echo "Current status:"
kubectl get all -l app=kubernetes-bootcamp

