#!/bin/bash

echo "=========================================="
echo "Testing Kubernetes Deployment"
echo "=========================================="

# Port forward services in background
echo "Setting up port forwarding..."
kubectl port-forward -n microservices svc/app-service 8080:8080 > /dev/null 2>&1 &
APP_PF=$!
kubectl port-forward -n microservices svc/auth-service 8081:8081 > /dev/null 2>&1 &
AUTH_PF=$!
kubectl port-forward -n microservices svc/db-service 8082:8082 > /dev/null 2>&1 &
DB_PF=$!

# Wait for port forwarding
sleep 3

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up port forwarding..."
    kill $APP_PF $AUTH_PF $DB_PF 2>/dev/null
    pkill -f "kubectl port-forward" 2>/dev/null
}
trap cleanup EXIT

# Test health endpoints
echo ""
echo "Testing health endpoints..."
for port in 8080 8081 8082; do
    if curl -s http://localhost:$port/health > /dev/null; then
        echo "  ✅ Port $port: Healthy"
    else
        echo "  ❌ Port $port: Failed"
    fi
done

# Test authentication
echo ""
echo "Testing authentication..."
TOKEN=$(curl -s -X POST http://localhost:8081/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo "  ✅ Login successful"
    echo "  Token: ${TOKEN:0:50}..."
    
    # Test app endpoints
    echo ""
    echo "Testing application endpoints..."
    
    # Test presets
    if curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/presets > /dev/null; then
        echo "  ✅ GET /api/presets"
    else
        echo "  ❌ GET /api/presets"
    fi
    
    # Test preset data
    if curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/preset/welcome > /dev/null; then
        echo "  ✅ GET /api/preset/welcome"
    else
        echo "  ❌ GET /api/preset/welcome"
    fi
    
    # Test data creation
    CREATE_RESPONSE=$(curl -s -X POST http://localhost:8080/api/data \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"test": "k8s-test", "value": 42}')
    
    if echo "$CREATE_RESPONSE" | grep -q "id"; then
        echo "  ✅ POST /api/data"
        ITEM_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
        if [ -n "$ITEM_ID" ]; then
            echo "    Created item: $ITEM_ID"
        fi
    else
        echo "  ❌ POST /api/data"
    fi
else
    echo "  ❌ Login failed"
fi

echo ""
echo "=========================================="
echo "Test complete!"
echo "=========================================="
echo ""
echo "To access services without port forwarding:"
echo "  kubectl port-forward -n microservices svc/app-service 8080:8080"
echo "  kubectl port-forward -n microservices svc/auth-service 8081:8081"
echo ""
echo "Or use NodePort (app-service only):"
echo "  minikube service -n microservices app-service-nodeport"

