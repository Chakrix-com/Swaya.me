#!/bin/bash
# High Load Test - Push to Breaking Point
# Tests: 500, 750, 1000 concurrent users

set -e

# Configuration
EMAIL="demo@swaya.me"
PASSWORD="Demo1234"
QUIZ_ID=13
TEST_DURATION="3m"
TESTS=(1000 1200)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Activate environment
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate
cd ..

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║          High Load Test - Finding Breaking Point                      ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Tests to run: 500, 750, 1000 concurrent users"
echo "Duration: 3 minutes each"
echo ""

# Function to login
login() {
    echo -e "${BLUE}🔑 Logging in...${NC}"
    LOGIN_RESPONSE=$(curl -s -X POST "https://www.swaya.me/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")
    
    TOKEN=$(echo $LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
    
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}❌ Login failed!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Logged in${NC}"
}

# Function to create session
create_session() {
    echo -e "${BLUE}🎮 Creating session...${NC}"
    SESSION_RESPONSE=$(curl -s -X POST "https://www.swaya.me/api/v1/quizzes/sessions/start?quiz_id=$QUIZ_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    SESSION_ID=$(echo $SESSION_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
    JOIN_CODE=$(echo $SESSION_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin).get('join_code', ''))" 2>/dev/null)
    
    if [ -z "$SESSION_ID" ]; then
        echo -e "${RED}❌ Failed to create session${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Session created (ID: $SESSION_ID, Code: $JOIN_CODE)${NC}"
}

# Function to open question
open_question() {
    echo -e "${BLUE}❓ Opening first question...${NC}"
    QUIZ_RESPONSE=$(curl -s "https://www.swaya.me/api/v1/quizzes/$QUIZ_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    FIRST_Q_ID=$(echo $QUIZ_RESPONSE | python -c "import sys, json; data = json.load(sys.stdin); print(data['questions'][0]['id'] if data.get('questions') else '')" 2>/dev/null)
    
    if [ -z "$FIRST_Q_ID" ]; then
        echo -e "${RED}❌ Failed to get question${NC}"
        exit 1
    fi
    
    curl -s -X POST "https://www.swaya.me/api/v1/quizzes/sessions/$SESSION_ID/open-question" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"question_id\": $FIRST_Q_ID}" > /dev/null
    
    echo -e "${GREEN}✅ Question opened${NC}"
}

# Function to update load test config
update_config() {
    sed -i "s/SESSION_ID = [0-9]*/SESSION_ID = $SESSION_ID/" load_test.py
    sed -i "s/JOIN_CODE = \"[^\"]*\"/JOIN_CODE = \"$JOIN_CODE\"/" load_test.py
}

# Main test loop
for USERS in "${TESTS[@]}"; do
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo -e "${YELLOW}TEST: $USERS CONCURRENT USERS${NC}"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo ""
    
    # Setup
    login
    create_session
    open_question
    update_config
    
    # Run test
    echo ""
    echo -e "${BLUE}🚀 Starting load test with $USERS users...${NC}"
    echo ""
    
    REPORT_FILE="load_test_${USERS}_users.html"
    LOG_FILE="load_test_${USERS}_users.log"
    
    locust -f load_test.py \
           --host=https://www.swaya.me \
           --users $USERS \
           --spawn-rate 20 \
           --run-time $TEST_DURATION \
           --headless \
           --html=$REPORT_FILE 2>&1 | tee $LOG_FILE
    
    echo ""
    echo -e "${GREEN}✅ Test complete: $USERS users${NC}"
    echo "   Report: $REPORT_FILE"
    echo "   Log: $LOG_FILE"
    echo ""
    
    # Extract quick stats
    echo -e "${BLUE}📊 Quick Results:${NC}"
    grep "Aggregated" $LOG_FILE | tail -1
    echo ""
    
    # Cool down
    if [ "$USERS" != "1000" ]; then
        echo "Waiting 30 seconds before next test..."
        sleep 30
    fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                    All Tests Complete!                                 ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Reports generated:"
ls -lh load_test_*_users.html | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Review HTML reports to analyze performance at each load level."
