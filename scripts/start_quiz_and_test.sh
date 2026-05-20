#!/bin/bash
# Start quiz and run load test

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║              Start Quiz & Run Load Test                               ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

SESSION_ID=127
QUIZ_ID=13
JOIN_CODE="9GP6BX"

echo "📋 Session Details:"
echo "   Session ID: $SESSION_ID"
echo "   Quiz ID: $QUIZ_ID"
echo "   Join Code: $JOIN_CODE"
echo ""

# Activate environment
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate

echo "🔐 Login Required"
echo "Please enter your host credentials to start the quiz:"
echo ""

read -p "Email: " EMAIL
read -sp "Password: " PASSWORD
echo ""
echo ""

# Login to get token
echo "🔑 Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "https://www.swaya.me/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed. Please check your credentials."
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful"
echo ""

# Start quiz
echo "🎮 Starting quiz session..."
START_RESPONSE=$(curl -s -X POST "https://www.swaya.me/api/v1/quizzes/$QUIZ_ID/sessions/$SESSION_ID/start" \
  -H "Authorization: Bearer $TOKEN")

echo "$START_RESPONSE" | python -m json.tool 2>/dev/null || echo "$START_RESPONSE"
echo ""

# Show first question
echo "❓ Opening first question..."
FIRST_Q_RESPONSE=$(curl -s -X POST "https://www.swaya.me/api/v1/quizzes/sessions/$SESSION_ID/open-question" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question_id": 15}')

echo "$FIRST_Q_RESPONSE" | python -m json.tool 2>/dev/null || echo "$FIRST_Q_RESPONSE"
echo ""

echo "✅ Quiz started with first question active!"
echo ""

# Ask if ready to run test
read -p "Ready to run load test? (y/n): " READY

if [ "$READY" != "y" ]; then
    echo "Test cancelled. Quiz is ready when you are!"
    exit 0
fi

echo ""
echo "🚀 Starting Load Test: 200 users over 5 minutes"
echo "============================================================"
echo ""

# Run load test
cd /home/vinay/Swaya.me
locust -f load_test.py \
       --host=https://www.swaya.me \
       --users 200 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless \
       --html=load_test_report.html

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║ ✅ Load Test Complete!                                                 ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 HTML Report: /home/vinay/Swaya.me/load_test_report.html"
echo ""
