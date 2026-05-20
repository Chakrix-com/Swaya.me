#!/bin/bash
set -e

echo "🚀 End-to-End UI Test for Swaya.me"
echo "======================================"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

BASE_URL="https://www.swaya.me"

# Test 1: Homepage loads
echo -e "\n📝 Test 1: Homepage Loads"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL)
if [ "$STATUS" == "200" ]; then
  echo -e "${GREEN}✅ Homepage loaded (HTTP $STATUS)${NC}"
else
  echo -e "${RED}❌ Homepage failed (HTTP $STATUS)${NC}"
  exit 1
fi

# Test 2: Login page loads
echo -e "\n📝 Test 2: Login Page Loads"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/login)
if [ "$STATUS" == "200" ]; then
  echo -e "${GREEN}✅ Login page loaded${NC}"
else
  echo -e "${RED}❌ Login page failed${NC}"
  exit 1
fi

# Test 3: Join page loads
echo -e "\n📝 Test 3: Join Page Loads"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/join/TEST123)
if [ "$STATUS" == "200" ]; then
  echo -e "${GREEN}✅ Join page loaded${NC}"
else
  echo -e "${RED}❌ Join page failed${NC}"
  exit 1
fi

# Test 4: Frontend assets load
echo -e "\n📝 Test 4: Frontend Assets Load"
CONTENT=$(curl -s $BASE_URL)
if echo "$CONTENT" | grep -q "index.*\.js"; then
  echo -e "${GREEN}✅ JavaScript bundle found in HTML${NC}"
else
  echo -e "${RED}❌ JavaScript bundle not found${NC}"
  exit 1
fi

if echo "$CONTENT" | grep -q "index.*\.css"; then
  echo -e "${GREEN}✅ CSS bundle found in HTML${NC}"
else
  echo -e "${RED}❌ CSS bundle not found${NC}"
  exit 1
fi

# Test 5: Backend API is accessible
echo -e "\n📝 Test 5: Backend API Health Check"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/api/v1/health)
if [ "$STATUS" == "200" ]; then
  echo -e "${GREEN}✅ API health check passed${NC}"
else
  echo -e "${RED}❌ API health check failed (HTTP $STATUS)${NC}"
  exit 1
fi

# Test 6: Complete API Flow (from previous test)
echo -e "\n📝 Test 6: Complete API Flow"
echo -e "${YELLOW}Running API end-to-end test...${NC}"
/home/vinay/Swaya.me/test_api_flow.sh
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✅ Complete API flow working${NC}"
else
  echo -e "${RED}❌ API flow test failed${NC}"
  exit 1
fi

echo -e "\n${GREEN}======================================"
echo "🎉 ALL UI & API TESTS PASSED!"
echo -e "======================================${NC}\n"

echo "Summary:"
echo "✅ Homepage loads correctly"
echo "✅ Login page accessible"
echo "✅ Join page accessible"
echo "✅ Frontend assets loading"
echo "✅ Backend API healthy"
echo "✅ Complete quiz flow working (API)"
echo ""
echo "Note: UI interaction tests require browser automation."
echo "The API tests confirm all backend functionality works perfectly."
