#!/bin/bash

echo "=========================================="
echo "Checking Prerequisites for Kubernetes Deployment"
echo "=========================================="

ERRORS=0

# Check Docker
echo -n "Checking Docker... "
if command -v docker &> /dev/null && docker info > /dev/null 2>&1; then
    echo "✅ Docker is running"
else
    echo "❌ Docker is not running or not installed"
    ERRORS=$((ERRORS + 1))
fi

# Check kubectl
echo -n "Checking kubectl... "
if command -v kubectl &> /dev/null; then
    echo "✅ kubectl is installed"
    KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null | head -n1)
    echo "   Version: $KUBECTL_VERSION"
else
    echo "❌ kubectl is not installed"
    echo "   Install: brew install kubectl"
    ERRORS=$((ERRORS + 1))
fi

# Check Kubernetes cluster
echo -n "Checking Kubernetes cluster... "
if kubectl cluster-info > /dev/null 2>&1; then
    echo "✅ Kubernetes cluster is accessible"
    CONTEXT=$(kubectl config current-context 2>/dev/null || echo "none")
    echo "   Current context: $CONTEXT"
else
    echo "❌ No Kubernetes cluster found"
    ERRORS=$((ERRORS + 1))
    
    # Check for minikube
    if command -v minikube &> /dev/null; then
        echo ""
        echo "💡 minikube is installed. To start a cluster:"
        echo "   minikube start"
    elif command -v kind &> /dev/null; then
        echo ""
        echo "💡 kind is installed. To create a cluster:"
        echo "   kind create cluster --name microservices"
    else
        echo ""
        echo "💡 Install a local Kubernetes cluster:"
        echo "   - minikube: brew install minikube && minikube start"
        echo "   - kind: brew install kind && kind create cluster"
    fi
fi

# Check for minikube or kind
echo ""
echo -n "Checking local cluster tools... "
if command -v minikube &> /dev/null; then
    echo "✅ minikube is installed"
    if minikube status > /dev/null 2>&1; then
        echo "   Status: $(minikube status --format '{{.Host}} {{.Kubelet}} {{.APIServer}}' 2>/dev/null || echo 'not running')"
    else
        echo "   Status: not running (start with: minikube start)"
    fi
elif command -v kind &> /dev/null; then
    echo "✅ kind is installed"
    if kind get clusters &> /dev/null; then
        CLUSTERS=$(kind get clusters 2>/dev/null | wc -l | tr -d ' ')
        echo "   Clusters: $CLUSTERS"
    else
        echo "   No clusters found (create with: kind create cluster)"
    fi
else
    echo "⚠️  No local cluster tools found (minikube or kind)"
    echo "   Install: brew install minikube  OR  brew install kind"
fi

echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ All prerequisites met! Ready to deploy."
    echo ""
    echo "Next steps:"
    echo "  1. Build images: make build-all"
    echo "  2. Load images: make k8s-load-images"
    echo "  3. Deploy: make k8s-deploy"
else
    echo "❌ $ERRORS prerequisite(s) missing. Please fix above issues."
    exit 1
fi
echo "=========================================="

