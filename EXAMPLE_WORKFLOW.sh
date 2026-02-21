#!/bin/bash
# Example: How to run a simple load test

echo "======================================"
echo "Example Load Test Workflow"
echo "======================================"
echo ""

cat << 'EOF'
STEP 1: Prepare Your Quiz
==========================

1. Go to https://www.swaya.me
2. Login with your credentials
3. Create a quiz with at least one MCQ question
4. Click "Start Session"
5. You'll see a screen like:

   ┌─────────────────────────────────┐
   │  Quiz Control                   │
   │                                 │
   │  Join Code: 05IIMN              │ ← Copy this
   │  Session ID: 124                │ ← Note this (from URL)
   │                                 │
   │  Participants: 0                │
   │  Status: Waiting                │
   │                                 │
   │  [Start Quiz]                   │
   └─────────────────────────────────┘


STEP 2: Update Test Configuration
==================================

Edit load_test.py and set these values:

   QUIZ_ID = 13         # Your quiz ID
   SESSION_ID = 124     # From step 1
   JOIN_CODE = "05IIMN" # From step 1


STEP 3: Run the Test
====================

Option A - Quick Interactive Test:
   ./run_load_test.sh

Option B - Web UI:
   cd backend
   source .venv/bin/activate
   locust -f ../load_test.py --host=https://www.swaya.me
   # Open http://localhost:8089

Option C - Command Line:
   cd backend
   source .venv/bin/activate
   locust -f ../load_test.py \
          --host=https://www.swaya.me \
          --users 50 \
          --spawn-rate 5 \
          --run-time 2m \
          --headless


STEP 4: Monitor Resources (Optional)
=====================================

In another terminal:
   ./monitor_server.sh


STEP 5: Watch the Results
==========================

You'll see:
- Participants joining your quiz session
- Number increasing in "Participants: X"
- Each "user" in the load test = one participant

The test simulates:
1. Joining with random display name (User_1234)
2. Polling for current question
3. Submitting random answers (A, B, C, or D)
4. Checking results


STEP 6: Interpret Results
==========================

Example output:

┌────────────────────────────────────────────┐
│ Type     Name                      RPS     │
├────────────────────────────────────────────┤
│ POST     /api/v1/.../join          10.2    │
│ GET      /api/v1/.../results       45.8    │
│ POST     /api/v1/.../submit        15.3    │
├────────────────────────────────────────────┤
│ Aggregated                         71.3    │
└────────────────────────────────────────────┘

RPS = Requests Per Second
Higher = Better

Response Times (ms):
┌────────────────────────────────────────────┐
│          Min   Median  P95    Max          │
├────────────────────────────────────────────┤
│ join     45    89      234    456          │
│ results  12    34      87     234          │
│ submit   23    56      145    345          │
└────────────────────────────────────────────┘

P95 < 500ms = Good ✅
P95 < 1000ms = OK ⚠️
P95 > 2000ms = Overloaded ❌


STEP 7: Find Your Limit
========================

Run multiple tests with increasing users:

Test 1:  50 users → All green? Continue
Test 2: 100 users → All green? Continue
Test 3: 200 users → All green? Continue
Test 4: 500 users → Yellow/Red? You found your limit!

Your limit is where:
- Response times jump above 1000ms
- Failure rate > 5%
- CPU > 90%
- RPS stops increasing


Example Results:
================

Good Server (4 vCPU, 24GB RAM):
   50 users   → P95: 150ms, CPU: 20% ✅
  100 users   → P95: 280ms, CPU: 35% ✅
  200 users   → P95: 450ms, CPU: 55% ✅
  500 users   → P95: 890ms, CPU: 78% ⚠️
 1000 users   → P95: 2300ms, CPU: 95% ❌

Recommendation: Max 500 concurrent users


What to Do With Results:
=========================

1. Document Your Limit:
   "Our server can handle 500 concurrent quiz participants"

2. Set Event Limits:
   - Max participants: 400 (80% of capacity)
   - Queue additional participants
   - Show "Event Full" message

3. Monitor Production:
   - Alert at 300 users (60% capacity)
   - Scale up if needed

4. Marketing:
   "Support for 500+ concurrent participants"


EOF

echo ""
echo "======================================"
echo "Ready to start testing!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Create a quiz session at https://www.swaya.me"
echo "2. Run: ./run_load_test.sh"
echo ""
