#!/bin/bash
# Automated Incremental Load Test
# Runs load tests with increasing user counts until system breaks

set -e  # Exit on error

# Configuration
EMAIL="demo@swaya.me"
PASSWORD="Demo1234"
QUIZ_ID=13  # Update if needed
TEST_DURATION="3m"
START_USERS=100
INCREMENT=100
MAX_USERS=1000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Activate environment
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate
cd ..

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║          Incremental Load Test - Find Breaking Point                  ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Email: $EMAIL"
echo "  Quiz ID: $QUIZ_ID"
echo "  Test Duration: $TEST_DURATION"
echo "  Start: $START_USERS users"
echo "  Increment: $INCREMENT users"
echo "  Max: $MAX_USERS users"
echo ""

# Function to login and get token
login() {
    echo -e "${BLUE}🔑 Logging in...${NC}"
    LOGIN_RESPONSE=$(curl -s -X POST "https://www.swaya.me/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")
    
    TOKEN=$(echo $LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
    
    if [ -z "$TOKEN" ]; then
        echo -e "${RED}❌ Login failed!${NC}"
        echo "Response: $LOGIN_RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Login successful${NC}"
}

# Function to create and start session
create_session() {
    echo -e "${BLUE}🎮 Creating and starting quiz session...${NC}"
    SESSION_RESPONSE=$(curl -s -X POST "https://www.swaya.me/api/v1/quizzes/sessions/start?quiz_id=$QUIZ_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json")
    
    SESSION_ID=$(echo $SESSION_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
    JOIN_CODE=$(echo $SESSION_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin).get('join_code', ''))" 2>/dev/null)
    
    if [ -z "$SESSION_ID" ] || [ -z "$JOIN_CODE" ]; then
        echo -e "${RED}❌ Failed to create session!${NC}"
        echo "Response: $SESSION_RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Session created and started${NC}"
    echo "   Session ID: $SESSION_ID"
    echo "   Join Code: $JOIN_CODE"
}

# Function to open first question
open_question() {
    echo -e "${BLUE}❓ Opening first question...${NC}"
    # Get first question ID
    QUIZ_RESPONSE=$(curl -s "https://www.swaya.me/api/v1/quizzes/$QUIZ_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    FIRST_Q_ID=$(echo $QUIZ_RESPONSE | python -c "import sys, json; data = json.load(sys.stdin); print(data['questions'][0]['id'] if data.get('questions') else '')" 2>/dev/null)
    
    if [ -z "$FIRST_Q_ID" ]; then
        echo -e "${RED}❌ Failed to get first question ID!${NC}"
        exit 1
    fi
    
    OPEN_RESPONSE=$(curl -s -X POST "https://www.swaya.me/api/v1/quizzes/sessions/$SESSION_ID/open-question" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"question_id\": $FIRST_Q_ID}")
    
    echo -e "${GREEN}✅ Question opened (ID: $FIRST_Q_ID)${NC}"
}

# Function to update load test config
update_load_test() {
    local session_id=$1
    local join_code=$2
    
    sed -i "s/SESSION_ID = [0-9]*/SESSION_ID = $session_id/" load_test.py
    sed -i "s/JOIN_CODE = \"[^\"]*\"/JOIN_CODE = \"$join_code\"/" load_test.py
}

# Function to run load test
run_load_test() {
    local users=$1
    local test_num=$2
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo -e "${YELLOW}TEST $test_num: $users USERS${NC}"
    echo "═══════════════════════════════════════════════════════════════════════"
    
    # Create new session for this test
    login
    create_session
    open_question
    update_load_test $SESSION_ID $JOIN_CODE
    
    echo ""
    echo -e "${BLUE}🚀 Running load test: $users users, $TEST_DURATION...${NC}"
    echo ""
    
    # Run test
    REPORT_FILE="load_test_${users}_users.html"
    locust -f load_test.py \
           --host=https://www.swaya.me \
           --users $users \
           --spawn-rate 10 \
           --run-time $TEST_DURATION \
           --headless \
           --html=$REPORT_FILE 2>&1 | tee "load_test_${users}_users.log"
    
    # Extract key metrics
    echo ""
    echo -e "${BLUE}📊 Extracting metrics...${NC}"
    
    # Get last stats line
    STATS=$(grep "Aggregated" "load_test_${users}_users.log" | tail -1)
    
    echo -e "${GREEN}Results saved:${NC}"
    echo "  Report: $REPORT_FILE"
    echo "  Log: load_test_${users}_users.log"
    echo ""
    
    # Ask if continue
    read -p "Continue to next test? (y/n): " CONTINUE
    
    if [ "$CONTINUE" != "y" ]; then
        echo -e "${YELLOW}⏸  Testing stopped by user${NC}"
        return 1
    fi
    
    # Small delay between tests
    echo ""
    echo "Waiting 30 seconds before next test..."
    sleep 30
    
    return 0
}

# Main test loop
CURRENT_USERS=$START_USERS
TEST_NUM=1

while [ $CURRENT_USERS -le $MAX_USERS ]; do
    if ! run_load_test $CURRENT_USERS $TEST_NUM; then
        break
    fi
    
    CURRENT_USERS=$((CURRENT_USERS + INCREMENT))
    TEST_NUM=$((TEST_NUM + 1))
done

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                    Load Testing Complete                               ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Results files:"
ls -1 load_test_*_users.html load_test_*_users.log 2>/dev/null
echo ""
echo "Review HTML reports to find breaking point!"
