# Manual Load Test - Step by Step

## Current Setup
- **Session ID:** 127
- **Join Code:** 9GP6BX
- **Quiz ID:** 13
- **Quiz:** Demo Quiz - General Knowledge

## Steps to Run Load Test

### 1. Start the Quiz Manually

Open your browser and go to:
```
https://www.swaya.me/quiz/13/control
```

Click:
1. **"Start Quiz"** button
2. **"Open Question"** for the first question

You should see the question become active.

### 2. Run the Load Test

In your terminal:
```bash
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate
cd ..

# Run the test
locust -f load_test.py \
       --host=https://www.swaya.me \
       --users 200 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless \
       --html=load_test_report.html
```

### 3. Watch It Happen!

While the test runs:
- Watch the Quiz Control screen
- You'll see participant count increasing
- Answers coming in
- Real-time aggregation

In another terminal (optional):
```bash
./monitor_server.sh
```

### 4. View Results

After test completes:
```bash
# View summary
cat load_test_report.html

# Or open in browser
```

## What to Look For

### Good Results ✅
- P95 Response Time < 500ms
- Failure Rate: 0%
- RPS increasing with users
- CPU < 60%

### At Capacity ⚠️
- P95 Response Time 500-1000ms
- Failure Rate 1-5%
- RPS plateauing
- CPU 60-80%

### Overloaded ❌
- P95 Response Time > 2000ms
- Failure Rate > 10%
- RPS decreasing
- CPU > 90%

## Quick Commands

Start quiz (after login in browser):
```
Already started in browser ✅
```

Run test:
```bash
cd /home/vinay/Swaya.me/backend && source .venv/bin/activate && cd .. && \
locust -f load_test.py --host=https://www.swaya.me \
--users 200 --spawn-rate 10 --run-time 5m --headless --html=load_test_report.html
```

Monitor:
```bash
./monitor_server.sh
```

## Troubleshooting

**Problem:** Still getting 422 errors
- Make sure question is OPEN (not just started)
- Check question_id in error

**Problem:** No current_question
- Click "Open Question" in Quiz Control

**Problem:** Test finishes too fast
- Increase run time: `--run-time 10m`
