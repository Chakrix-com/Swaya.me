#!/bin/bash
# Test script for word cloud question creation

echo "========================================="
echo "Word Cloud Question - Full Flow Test"
echo "========================================="

# Configuration (UPDATE THESE)
BASE_URL="http://localhost:8000"
AUTH_TOKEN="YOUR_JWT_TOKEN_HERE"
QUIZ_ID="1"  # Replace with your quiz ID

echo ""
echo "📝 Step 1: Create a word cloud question"
echo "-----------------------------------------"

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${BASE_URL}/quizzes/${QUIZ_ID}/questions" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "question_type": "word_cloud",
    "text": "What is one word that describes this session?"
  }')

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "201" ] || [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Question created successfully!"
    echo "Response:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    
    # Extract question ID
    QUESTION_ID=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
    echo ""
    echo "Created Question ID: $QUESTION_ID"
else
    echo "❌ Failed to create question"
    echo "Response:"
    echo "$BODY"
    exit 1
fi

echo ""
echo "📋 Step 2: Get quiz with questions"
echo "-----------------------------------------"

QUIZ_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "${BASE_URL}/quizzes/${QUIZ_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")

HTTP_STATUS=$(echo "$QUIZ_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$QUIZ_RESPONSE" | sed '/HTTP_STATUS/d')

echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Quiz retrieved successfully!"
    
    # Check if word cloud question is in the list
    WORD_CLOUD_COUNT=$(echo "$BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for q in data.get('questions', []) if q.get('question_type') == 'word_cloud'))" 2>/dev/null)
    
    echo "Word cloud questions in quiz: $WORD_CLOUD_COUNT"
    
    if [ "$WORD_CLOUD_COUNT" -gt "0" ]; then
        echo "✅ Word cloud question found in quiz!"
        echo ""
        echo "Questions summary:"
        echo "$BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, q in enumerate(data.get('questions', []), 1):
    qtype = q.get('question_type', 'mcq')
    text = q.get('text', '')[:50]
    print(f'  {i}. [{qtype.upper()}] {text}...')
" 2>/dev/null || echo "  (Could not parse questions)"
    else
        echo "❌ Word cloud question NOT found in quiz"
        echo "Questions:"
        echo "$BODY" | python3 -m json.tool 2>/dev/null | grep -A5 "questions"
    fi
else
    echo "❌ Failed to get quiz"
    echo "$BODY"
    exit 1
fi

echo ""
echo "========================================="
echo "Test Complete!"
echo "========================================="
echo ""
echo "📌 If word cloud question is not showing:"
echo "   1. Check backend logs for errors"
echo "   2. Verify migration was applied: alembic current"
echo "   3. Check database: SELECT id, question_type FROM questions;"
echo "   4. Restart backend server"
