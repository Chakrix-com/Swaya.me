#!/bin/bash
set -e

echo "🚀 Testing Complete Quiz Flow via API"
echo "======================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL="${BASE_URL:-https://www.swaya.me/api/v1}"
HOST_EMAIL="${HOST_EMAIL:-demo@swaya.me}"
HOST_PASSWORD="${HOST_PASSWORD:-Demo1234}"

# Step 1: Login as host
echo -e "\n📝 Step 1: Host Login"
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$HOST_EMAIL\",\"password\":\"$HOST_PASSWORD\"}" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo -e "${RED}❌ Login failed${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Host logged in${NC}"

# Step 2: Get first quiz
echo -e "\n📝 Step 2: Getting Quiz List"
QUIZ_ID=$(curl -s "$BASE_URL/quizzes/" -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys, json; data=json.load(sys.stdin); ready=next((q for q in data if str(q.get('status','')).lower()=='ready'), None); print(ready['id'] if ready else '')")

if [ -z "$QUIZ_ID" ]; then
  echo -e "${RED}❌ No READY quiz found${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Found quiz ID: $QUIZ_ID${NC}"

# End any existing open sessions for this quiz to ensure deterministic flow
OPEN_SESSIONS=$(curl -s "$BASE_URL/quizzes/$QUIZ_ID/sessions" -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print('\n'.join(str(s['id']) for s in data.get('sessions', []) if s.get('status') in ('active','created')))")

if [ -n "$OPEN_SESSIONS" ]; then
  echo -e "\n🧹 Cleaning open sessions before test"
  while IFS= read -r SID; do
    [ -z "$SID" ] && continue
    curl -s -X POST "$BASE_URL/quizzes/sessions/$SID/end" -H "Authorization: Bearer $TOKEN" > /dev/null || true
  done <<< "$OPEN_SESSIONS"
fi

# Step 3: Start session
echo -e "\n📝 Step 3: Starting Quiz Session"
SESSION_DATA=$(curl -s -X POST "$BASE_URL/quizzes/sessions/start?quiz_id=$QUIZ_ID" \
  -H "Authorization: Bearer $TOKEN")
SESSION_ID=$(echo $SESSION_DATA | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
JOIN_CODE=$(echo $SESSION_DATA | python3 -c "import sys, json; print(json.load(sys.stdin)['join_code'])")

echo -e "${GREEN}✅ Session started - ID: $SESSION_ID, Join Code: $JOIN_CODE${NC}"

# Step 4: Advance to first question
echo -e "\n📝 Step 4: Advancing to First Question"
curl -s -X POST "$BASE_URL/quizzes/sessions/$SESSION_ID/advance" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
echo -e "${GREEN}✅ Advanced to question 1${NC}"

# Step 5: Audience joins
echo -e "\n📝 Step 5: Audience Joining Session"
PARTICIPANT_DATA=$(curl -s -X POST "$BASE_URL/quizzes/sessions/join" \
  -H "Content-Type: application/json" \
  -d "{\"join_code\":\"$JOIN_CODE\",\"display_name\":\"Test User\"}")
PARTICIPANT_TOKEN=$(echo $PARTICIPANT_DATA | python3 -c "import sys, json; print(json.load(sys.stdin)['session_token'])")
PARTICIPANT_SESSION_ID=$(echo $PARTICIPANT_DATA | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

echo -e "${GREEN}✅ Participant joined - Session: $PARTICIPANT_SESSION_ID${NC}"

# Step 6: Get current question
echo -e "\n📝 Step 6: Fetching Current Question"
QUESTION_DATA=$(curl -s "$BASE_URL/quizzes/sessions/$PARTICIPANT_SESSION_ID/audience-results?session_token=$PARTICIPANT_TOKEN")
QUESTION_ID=$(echo $QUESTION_DATA | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['current_question']['id'] if data.get('current_question') else '')")
QUESTION_TEXT=$(echo $QUESTION_DATA | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['current_question']['text'] if data.get('current_question') else 'No question')")

if [ -z "$QUESTION_ID" ]; then
  echo -e "${RED}❌ No current question found${NC}"
  echo "Response: $QUESTION_DATA"
  exit 1
fi
echo -e "${GREEN}✅ Question received: \"$QUESTION_TEXT\" (ID: $QUESTION_ID)${NC}"

# Step 7: Submit answer
echo -e "\n📝 Step 7: Submitting Answer (Option A = Index 0)"
QUESTION_TYPE=$(echo "$QUESTION_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('current_question',{}).get('question_type','mcq'))" 2>/dev/null || echo "mcq")

if [ "$QUESTION_TYPE" = "word_cloud" ] || [ "$QUESTION_TYPE" = "single_line" ] || [ "$QUESTION_TYPE" = "paragraph" ]; then
  SUBMIT_RESPONSE=$(curl -s -X POST "$BASE_URL/quizzes/sessions/submit-word-cloud?session_token=$PARTICIPANT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"question_id\":$QUESTION_ID,\"text_answer\":\"regression\"}")
else
  SUBMIT_RESPONSE=$(curl -s -X POST "$BASE_URL/quizzes/sessions/submit-answer?session_token=$PARTICIPANT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"question_id\":$QUESTION_ID,\"selected_option_index\":0}")
fi

SUCCESS=$(echo $SUBMIT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))")
if [ "$SUCCESS" != "True" ]; then
  echo -e "${RED}❌ Answer submission failed${NC}"
  echo "Response: $SUBMIT_RESPONSE"
  exit 1
fi
echo -e "${GREEN}✅ Answer submitted successfully${NC}"

# Step 8: Check host sees the answer
echo -e "\n📝 Step 8: Verifying Host Sees Results"
sleep 2
HOST_RESULTS=$(curl -s "$BASE_URL/quizzes/sessions/$SESSION_ID/results" \
  -H "Authorization: Bearer $TOKEN")
ANSWER_COUNT=$(echo $HOST_RESULTS | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['current_question']['total_answers'] if data.get('current_question') else 0)")

if [ "$ANSWER_COUNT" -lt "1" ]; then
  echo -e "${RED}❌ Host doesn't see answer (count: $ANSWER_COUNT)${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Host sees $ANSWER_COUNT answer(s)${NC}"

echo -e "\n${GREEN}🎉 ALL TESTS PASSED! Complete quiz flow is working!${NC}"
echo "======================================"
