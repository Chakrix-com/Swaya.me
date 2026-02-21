# Load Testing Swaya.me - Quick Start

## 🎯 Goal
Find out how many concurrent visitors can participate in a single quiz on your server.

## 📋 Prerequisites

1. **Active Quiz Session:**
   - Login to https://www.swaya.me
   - Create a quiz with at least one MCQ question
   - Start a quiz session
   - **Note the Session ID** (from URL: `/quiz/13/control` → ID is 13)
   - **Note the Join Code** (displayed on control screen)

## 🚀 Quick Start (Easiest)

```bash
cd /home/vinay/Swaya.me

# Run the interactive load test script
./run_load_test.sh
```

The script will:
1. Ask for your Quiz ID, Session ID, and Join Code
2. Let you choose a test profile:
   - **Quick Test:** 50 users for 2 minutes (safe baseline)
   - **Moderate Test:** 200 users for 5 minutes (typical event)
   - **Stress Test:** 500 users for 5 minutes (find limits)
   - **Custom:** Set your own parameters
   - **Web UI:** Manual control via browser

3. Run the test and generate an HTML report

## 📊 Monitor Server Resources

While the load test runs, open **another terminal** and run:

```bash
cd /home/vinay/Swaya.me
./monitor_server.sh
```

This shows real-time:
- CPU usage
- Memory usage
- Database connections
- Redis connections
- Network connections

Press `Ctrl+C` to stop monitoring.

## 🎮 Manual Testing (Advanced)

### Option 1: Web UI (Interactive)

```bash
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate

# Edit load_test.py first and set:
# QUIZ_ID = 13
# SESSION_ID = 124  # Your actual session ID
# JOIN_CODE = "ABC123"  # Your actual join code

# Start Locust web UI
locust -f /home/vinay/Swaya.me/load_test.py --host=https://www.swaya.me

# Open browser: http://localhost:8089
# Set number of users and spawn rate
# Click "Start swarming"
```

### Option 2: Command Line (Automated)

```bash
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate

# Edit load_test.py first (same as above)

# Run specific test
locust -f /home/vinay/Swaya.me/load_test.py \
       --host=https://www.swaya.me \
       --users 100 \
       --spawn-rate 10 \
       --run-time 3m \
       --headless \
       --html=report.html
```

## 📈 Understanding Results

### Good Performance ✅
```
Users: 100
RPS: 150+
P95 Response Time: <500ms
Failure Rate: 0%
CPU: <60%
Memory: <50%
```
**Interpretation:** Server handling load well, can add more users.

### Moderate Stress ⚠️
```
Users: 300
RPS: 200
P95 Response Time: 500-1500ms
Failure Rate: 1-5%
CPU: 60-80%
Memory: 50-70%
```
**Interpretation:** Server under stress but functional. Close to comfortable limit.

### Overload ❌
```
Users: 500+
RPS: Decreasing
P95 Response Time: >2000ms
Failure Rate: >10%
CPU: >90%
Memory: >80%
```
**Interpretation:** Server overloaded. This is your maximum capacity.

## 🔍 Key Metrics Explained

- **RPS (Requests Per Second):** Higher is better. Should increase with users.
- **Response Time P95:** 95% of requests complete within this time. <1000ms is good.
- **Failure Rate:** Percentage of failed requests. <1% is acceptable.
- **CPU Usage:** Backend process CPU. >90% means CPU bottleneck.
- **Database Connections:** Should stay below max limit (usually 150).

## 📝 Recommended Test Plan

### Test 1: Baseline
```bash
Users: 50
Duration: 2 minutes
Goal: Establish normal performance
```

### Test 2: Typical Event
```bash
Users: 200
Duration: 5 minutes
Goal: Simulate realistic quiz
```

### Test 3: Find Limit
```bash
Users: 500
Duration: 5 minutes
Goal: Find degradation point
```

### Test 4: Breaking Point
```bash
Users: 1000
Duration: 5 minutes
Goal: Find absolute maximum
```

**Important:** Run tests in order, from small to large!

## 🛠️ Files Created

- **load_test.py** - Locust test script (simulates participants)
- **run_load_test.sh** - Interactive test runner (easiest way)
- **monitor_server.sh** - Real-time resource monitor
- **LOAD_TEST_GUIDE.md** - Detailed documentation
- **load_test_report.html** - Generated after each test

## ⚠️ Safety Tips

1. **Don't test during real events** - Only test when no one is using the system
2. **Start small** - Begin with 10-50 users, increase gradually
3. **Monitor continuously** - Watch CPU, memory, database
4. **Have backup** - Be ready to stop test if server struggles
5. **Off-peak testing** - Run tests during low-traffic hours

## 🔧 Troubleshooting

### "Connection refused"
```bash
# Check if backend is running
systemctl status swayame-backend

# Restart if needed
sudo systemctl restart swayame-backend
```

### "Locust not found"
```bash
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate
pip install locust
```

### High failure rate immediately
- Check Session ID and Join Code are correct
- Verify quiz session is ACTIVE (not ended)
- Check backend logs: `journalctl -u swayame-backend -f`

### Server becomes unresponsive
```bash
# Stop load test: Ctrl+C
# Restart backend if needed
sudo systemctl restart swayame-backend
```

## 📞 Need Help?

See detailed guide: **LOAD_TEST_GUIDE.md**

## 🎯 Expected Results (Estimate)

Based on your server specs (4 vCPUs, 24GB RAM):

- **Conservative:** 200-300 concurrent users
- **Realistic:** 500-800 concurrent users  
- **Optimistic:** 1000+ concurrent users

Actual results depend on:
- Question complexity
- Database performance
- Network latency
- Code optimization

Run the tests to find YOUR specific limits! 🚀
