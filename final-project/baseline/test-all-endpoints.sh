#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_URL="http://localhost:8080"
AUTH_URL="http://localhost:8081"
DB_URL="http://localhost:8082"

PASSED=0
FAILED=0

# Test counter
test_count() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# Setup port forwarding
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Setting up port forwarding...${NC}"
echo -e "${BLUE}========================================${NC}"

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
    kill $APP_PF $AUTH_PF $DB_PF 2>/dev/null
    pkill -f "kubectl port-forward" 2>/dev/null
}
trap cleanup EXIT

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}COMPREHENSIVE ENDPOINT TESTING${NC}"
echo -e "${BLUE}========================================${NC}"

# ============================================
# SECTION 1: Public Endpoints (No Auth)
# ============================================
echo ""
echo -e "${YELLOW}SECTION 1: Public Endpoints (No Authentication Required)${NC}"
echo "------------------------------------------------"

# App Service - Root
echo -n "  Testing GET /app/ (root)... "
RESPONSE=$(curl -s -w "\n%{http_code}" $APP_URL/)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" -eq 200 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE"
    test_count 1
fi

# App Service - Health
echo -n "  Testing GET /app/health... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL/health)
if [ "$HTTP_CODE" -eq 200 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE"
    test_count 1
fi

# Auth Service - Root
echo -n "  Testing GET /auth/ (root)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $AUTH_URL/)
if [ "$HTTP_CODE" -eq 200 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE"
    test_count 1
fi

# Auth Service - Health
echo -n "  Testing GET /auth/health... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $AUTH_URL/health)
if [ "$HTTP_CODE" -eq 200 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE"
    test_count 1
fi

# DB Service - Root
echo -n "  Testing GET /db/ (root)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $DB_URL/)
if [ "$HTTP_CODE" -eq 200 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE"
    test_count 1
fi

# DB Service - Health
echo -n "  Testing GET /db/health... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $DB_URL/health)
if [ "$HTTP_CODE" -eq 200 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE"
    test_count 1
fi

# ============================================
# SECTION 2: Authentication Tests
# ============================================
echo ""
echo -e "${YELLOW}SECTION 2: Authentication Tests${NC}"
echo "------------------------------------------------"

# Test login with valid credentials
echo -n "  Testing POST /auth/login (valid credentials)... "
LOGIN_RESPONSE=$(curl -s -X POST $AUTH_URL/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
if [ -n "$TOKEN" ]; then
    test_count 0
    echo "    Token: ${TOKEN:0:30}..."
else
    echo "Failed to get token"
    test_count 1
fi

# Test login with invalid credentials
echo -n "  Testing POST /auth/login (invalid credentials)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $AUTH_URL/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrong"}')
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

# Test login with missing credentials
echo -n "  Testing POST /auth/login (missing password)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $AUTH_URL/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin"}')
if [ "$HTTP_CODE" -eq 401 ] || [ "$HTTP_CODE" -eq 422 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE"
    test_count 1
fi

# Test all default users
echo -n "  Testing login with user1... "
USER1_TOKEN=$(curl -s -X POST $AUTH_URL/login \
    -H "Content-Type: application/json" \
    -d '{"username":"user1","password":"password1"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
if [ -n "$USER1_TOKEN" ]; then
    test_count 0
else
    test_count 1
fi

echo -n "  Testing login with testuser... "
TESTUSER_TOKEN=$(curl -s -X POST $AUTH_URL/login \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","password":"testpass"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
if [ -n "$TESTUSER_TOKEN" ]; then
    test_count 0
else
    test_count 1
fi

# ============================================
# SECTION 3: Protected Endpoints WITHOUT JWT
# ============================================
echo ""
echo -e "${YELLOW}SECTION 3: Protected Endpoints WITHOUT JWT (Should Fail)${NC}"
echo "------------------------------------------------"

# App Service endpoints
echo -n "  Testing POST /app/api/data (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $APP_URL/api/data \
    -H "Content-Type: application/json" \
    -d '{"test":"data"}')
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

echo -n "  Testing GET /app/api/data/{id} (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL/api/data/test-id)
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

echo -n "  Testing GET /app/api/presets (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL/api/presets)
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

echo -n "  Testing GET /app/api/preset/welcome (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $APP_URL/api/preset/welcome)
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

echo -n "  Testing POST /app/api/seed (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $APP_URL/api/seed)
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

# Auth Service endpoints
echo -n "  Testing POST /auth/validate (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $AUTH_URL/validate)
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

echo -n "  Testing GET /auth/token/info (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $AUTH_URL/token/info)
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

# DB Service endpoints
echo -n "  Testing POST /db/store (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $DB_URL/store \
    -H "Content-Type: application/json" \
    -d '{"test":"data"}')
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

echo -n "  Testing GET /db/retrieve/{id} (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $DB_URL/retrieve/test-id)
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

echo -n "  Testing GET /db/list (no JWT)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $DB_URL/list)
if [ "$HTTP_CODE" -eq 401 ]; then
    test_count 0
else
    echo "HTTP $HTTP_CODE (expected 401)"
    test_count 1
fi

# ============================================
# SECTION 4: Protected Endpoints WITH JWT
# ============================================
echo ""
echo -e "${YELLOW}SECTION 4: Protected Endpoints WITH Valid JWT${NC}"
echo "------------------------------------------------"

if [ -z "$TOKEN" ]; then
    echo -e "${RED}  Cannot test - no valid token available${NC}"
    FAILED=$((FAILED + 1))
else
    # Auth Service - Validate token
    echo -n "  Testing POST /auth/validate (with JWT)... "
    VALIDATE_RESPONSE=$(curl -s -X POST $AUTH_URL/validate \
        -H "Authorization: Bearer $TOKEN")
    if echo "$VALIDATE_RESPONSE" | grep -q "valid"; then
        test_count 0
    else
        echo "Response: $VALIDATE_RESPONSE"
        test_count 1
    fi

    # Auth Service - Token info
    echo -n "  Testing GET /auth/token/info (with JWT)... "
    INFO_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" $AUTH_URL/token/info)
    if echo "$INFO_RESPONSE" | grep -q "username"; then
        test_count 0
    else
        echo "Response: $INFO_RESPONSE"
        test_count 1
    fi

    # App Service - List presets
    echo -n "  Testing GET /app/api/presets (with JWT)... "
    PRESETS_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" $APP_URL/api/presets)
    if echo "$PRESETS_RESPONSE" | grep -q "available_presets"; then
        test_count 0
    else
        echo "Response: $PRESETS_RESPONSE"
        test_count 1
    fi

    # App Service - Get preset
    echo -n "  Testing GET /app/api/preset/welcome (with JWT)... "
    PRESET_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" $APP_URL/api/preset/welcome)
    if echo "$PRESET_RESPONSE" | grep -q "preset_id"; then
        test_count 0
    else
        echo "Response: $PRESET_RESPONSE"
        test_count 1
    fi

    echo -n "  Testing GET /app/api/preset/status (with JWT)... "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" $APP_URL/api/preset/status)
    if [ "$HTTP_CODE" -eq 200 ]; then
        test_count 0
    else
        echo "HTTP $HTTP_CODE"
        test_count 1
    fi

    echo -n "  Testing GET /app/api/preset/info (with JWT)... "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" $APP_URL/api/preset/info)
    if [ "$HTTP_CODE" -eq 200 ]; then
        test_count 0
    else
        echo "HTTP $HTTP_CODE"
        test_count 1
    fi

    echo -n "  Testing GET /app/api/preset/invalid (with JWT)... "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" $APP_URL/api/preset/invalid)
    if [ "$HTTP_CODE" -eq 404 ]; then
        test_count 0
    else
        echo "HTTP $HTTP_CODE (expected 404)"
        test_count 1
    fi

    # ============================================
    # SECTION 5: Database Operations
    # ============================================
    echo ""
    echo -e "${YELLOW}SECTION 5: Database Operations (With JWT)${NC}"
    echo "------------------------------------------------"

    # Create data via App Service
    echo -n "  Testing POST /app/api/data (create via app)... "
    CREATE_RESPONSE=$(curl -s -X POST $APP_URL/api/data \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name":"Test Item","value":42,"category":"test"}')
    ITEM_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
    if [ -n "$ITEM_ID" ]; then
        test_count 0
        echo "    Created item: $ITEM_ID"
    else
        echo "Response: $CREATE_RESPONSE"
        test_count 1
    fi

    # Retrieve data via App Service
    if [ -n "$ITEM_ID" ]; then
        echo -n "  Testing GET /app/api/data/{id} (retrieve via app)... "
        sleep 1  # Small delay for DB
        RETRIEVE_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" $APP_URL/api/data/$ITEM_ID)
        if echo "$RETRIEVE_RESPONSE" | grep -q "Test Item"; then
            test_count 0
        else
            echo "Response: $RETRIEVE_RESPONSE"
            test_count 1
        fi
    fi

    # Create data directly via DB Service
    echo -n "  Testing POST /db/store (direct DB access)... "
    DB_CREATE_RESPONSE=$(curl -s -X POST $DB_URL/store \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name":"Direct DB Item","value":100}')
    DB_ITEM_ID=$(echo "$DB_CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
    if [ -n "$DB_ITEM_ID" ]; then
        test_count 0
        echo "    Created item: $DB_ITEM_ID"
    else
        echo "Response: $DB_CREATE_RESPONSE"
        test_count 1
    fi

    # Retrieve data directly via DB Service
    if [ -n "$DB_ITEM_ID" ]; then
        echo -n "  Testing GET /db/retrieve/{id} (direct DB access)... "
        sleep 1
        DB_RETRIEVE_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" $DB_URL/retrieve/$DB_ITEM_ID)
        if echo "$DB_RETRIEVE_RESPONSE" | grep -q "Direct DB Item"; then
            test_count 0
        else
            echo "Response: $DB_RETRIEVE_RESPONSE"
            test_count 1
        fi
    fi

    # List items via DB Service
    echo -n "  Testing GET /db/list (list all items)... "
    LIST_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" $DB_URL/list)
    if echo "$LIST_RESPONSE" | grep -q "items"; then
        test_count 0
        ITEM_COUNT=$(echo "$LIST_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null)
        echo "    Found $ITEM_COUNT items"
    else
        echo "Response: $LIST_RESPONSE"
        test_count 1
    fi

    # Test seed endpoint
    echo -n "  Testing POST /app/api/seed (seed database)... "
    SEED_RESPONSE=$(curl -s -X POST $APP_URL/api/seed \
        -H "Authorization: Bearer $TOKEN")
    if echo "$SEED_RESPONSE" | grep -q "seeded"; then
        test_count 0
        SEED_COUNT=$(echo "$SEED_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('items_created', 0))" 2>/dev/null)
        echo "    Seeded $SEED_COUNT items"
    else
        echo "Response: $SEED_RESPONSE"
        test_count 1
    fi

    # Delete item via DB Service
    if [ -n "$DB_ITEM_ID" ]; then
        echo -n "  Testing DELETE /db/delete/{id} (delete item)... "
        DELETE_RESPONSE=$(curl -s -X DELETE -H "Authorization: Bearer $TOKEN" $DB_URL/delete/$DB_ITEM_ID)
        if echo "$DELETE_RESPONSE" | grep -q "deleted"; then
            test_count 0
        else
            echo "Response: $DELETE_RESPONSE"
            test_count 1
        fi

        # Verify deletion
        echo -n "  Testing GET /db/retrieve/{id} (verify deletion)... "
        sleep 1
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" $DB_URL/retrieve/$DB_ITEM_ID)
        if [ "$HTTP_CODE" -eq 404 ]; then
            test_count 0
        else
            echo "HTTP $HTTP_CODE (expected 404)"
            test_count 1
        fi
    fi

    # ============================================
    # SECTION 6: Database User Management
    # ============================================
    echo ""
    echo -e "${YELLOW}SECTION 6: Database User Management${NC}"
    echo "------------------------------------------------"

    # Get user (used by auth service)
    echo -n "  Testing GET /db/user/admin (get user)... "
    USER_RESPONSE=$(curl -s $DB_URL/user/admin)
    if echo "$USER_RESPONSE" | grep -q "admin"; then
        test_count 0
    else
        echo "Response: $USER_RESPONSE"
        test_count 1
    fi

    echo -n "  Testing GET /db/user/user1 (get user)... "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $DB_URL/user/user1)
    if [ "$HTTP_CODE" -eq 200 ]; then
        test_count 0
    else
        echo "HTTP $HTTP_CODE"
        test_count 1
    fi

    echo -n "  Testing GET /db/user/nonexistent (get non-existent user)... "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $DB_URL/user/nonexistent)
    if [ "$HTTP_CODE" -eq 404 ]; then
        test_count 0
    else
        echo "HTTP $HTTP_CODE (expected 404)"
        test_count 1
    fi

    # Create new user
    echo -n "  Testing POST /db/user (create new user)... "
    NEW_USER_RESPONSE=$(curl -s -X POST $DB_URL/user \
        -H "Content-Type: application/json" \
        -d '{"username":"newuser","password":"newpass123"}')
    if echo "$NEW_USER_RESPONSE" | grep -q "created"; then
        test_count 0
        
        # Test login with new user
        echo -n "  Testing login with newly created user... "
        NEW_USER_TOKEN=$(curl -s -X POST $AUTH_URL/login \
            -H "Content-Type: application/json" \
            -d '{"username":"newuser","password":"newpass123"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
        if [ -n "$NEW_USER_TOKEN" ]; then
            test_count 0
        else
            test_count 1
        fi
    else
        echo "Response: $NEW_USER_RESPONSE"
        test_count 1
    fi

    # ============================================
    # SECTION 7: Invalid JWT Tests
    # ============================================
    echo ""
    echo -e "${YELLOW}SECTION 7: Invalid JWT Tests${NC}"
    echo "------------------------------------------------"

    echo -n "  Testing with invalid JWT token... "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer invalid.token.here" $APP_URL/api/presets)
    if [ "$HTTP_CODE" -eq 401 ]; then
        test_count 0
    else
        echo "HTTP $HTTP_CODE (expected 401)"
        test_count 1
    fi

    echo -n "  Testing with malformed Authorization header... "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: InvalidFormat" $APP_URL/api/presets)
    if [ "$HTTP_CODE" -eq 401 ]; then
        test_count 0
    else
        echo "HTTP $HTTP_CODE (expected 401)"
        test_count 1
    fi
fi

# ============================================
# SECTION 8: Database Persistence Check
# ============================================
echo ""
echo -e "${YELLOW}SECTION 8: Database Persistence Verification${NC}"
echo "------------------------------------------------"

# Check if database pod has persistent volume
echo -n "  Checking database pod status... "
DB_POD=$(kubectl get pods -n microservices -l app=db-service -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$DB_POD" ]; then
    POD_STATUS=$(kubectl get pod -n microservices $DB_POD -o jsonpath='{.status.phase}' 2>/dev/null)
    if [ "$POD_STATUS" = "Running" ]; then
        test_count 0
        echo "    Pod: $DB_POD (Status: $POD_STATUS)"
    else
        echo "Status: $POD_STATUS"
        test_count 1
    fi
else
    echo "No DB pod found"
    test_count 1
fi

# Check database volume mount
if [ -n "$DB_POD" ]; then
    echo -n "  Checking database volume mount... "
    VOLUME_MOUNT=$(kubectl get pod -n microservices $DB_POD -o jsonpath='{.spec.containers[0].volumeMounts[?(@.mountPath=="/data")].mountPath}' 2>/dev/null)
    if [ "$VOLUME_MOUNT" = "/data" ]; then
        test_count 0
    else
        echo "Volume mount: $VOLUME_MOUNT"
        test_count 1
    fi
fi

# ============================================
# SUMMARY
# ============================================
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}TEST SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"
TOTAL=$((PASSED + FAILED))
echo -e "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

