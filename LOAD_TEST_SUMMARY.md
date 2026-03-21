# Load Testing Setup - Complete ✅

## What Was Created

### 1. Load Test Script (`load_test.py`)
- **Purpose:** Simulates concurrent quiz participants
- **Features:**
  - Participant joins with random name
  - Polls for questions (every 1-3 seconds)
  - Submits random answers
  - Tracks response times and failures
  - Reports statistics

### 2. Quick Start Runner (`run_load_test.sh`)
- **Purpose:** Interactive script to run load tests easily
- **Features:**
  - Prompts for Quiz ID, Session ID, Join Code
  - Preset test profiles (Quick, Moderate, Stress)
  - Generates HTML reports
  - Updates configuration automatically

### 3. Resource Monitor (`monitor_server.sh`)
- **Purpose:** Real-time server resource monitoring
- **Shows:**
  - CPU usage (backend + system)
  - Memory usage
  - Database connections
  - Redis connections
  - Network connections
  - Disk I/O

### 4. Documentation
- **LOAD_TEST_README.md** - Quick start guide
- **LOAD_TEST_GUIDE.md** - Comprehensive documentation
- **EXAMPLE_WORKFLOW.sh** - Visual example with ASCII art

## How to Use (TL;DR)

### One-Command Test
```bash
cd /home/vinay/Swaya.me
./run_load_test.sh
```

### Monitor While Testing
```bash
# In another terminal
./monitor_server.sh
```

### What You Need
1. Active quiz session at https://www.swaya.me
2. Session ID (from URL)
3. Join Code (displayed on screen)

## Test Profiles Available

| Profile | Users | Duration | Use Case |
|---------|-------|----------|----------|
| Quick | 50 | 2 min | Baseline testing |
| Moderate | 200 | 5 min | Realistic event |
| Stress | 500 | 5 min | Find limits |
| Custom | Your choice | Your choice | Advanced |

## Expected Results (Your Server)

**Server Specs:**
- CPU: 4 vCPUs (ARM)
- RAM: 24 GB
- Disk: Fast SSD
- Network: 1-10 Gbps

**Estimated Capacity:**
- Baseline: 50-100 users (should be perfect)
- Comfortable: 200-300 users (typical event)
- Stress: 500-800 users (pushing limits)
- Maximum: 1000+ users (may degrade)

**Actual capacity will depend on:**
- Database query performance
- Redis response times
- Network latency
- Question complexity (images, etc.)

## Metrics to Watch

### Response Times (Priority: High)
- **Good:** P95 < 500ms
- **Acceptable:** P95 < 1000ms
- **Problem:** P95 > 2000ms

### RPS (Requests Per Second)
- **Good:** Increases with users
- **Problem:** Plateaus or decreases

### Failure Rate
- **Good:** 0%
- **Acceptable:** < 1%
- **Problem:** > 5%

### CPU Usage
- **Good:** < 60%
- **Acceptable:** 60-80%
- **Problem:** > 90%

### Memory Usage
- **Good:** < 50%
- **Acceptable:** 50-70%
- **Problem:** > 80%

## Safety Checklist

- [ ] Test during off-peak hours (no real users)
- [ ] Start with small numbers (50 users)
- [ ] Monitor server resources continuously
- [ ] Have backup plan (restart backend if needed)
- [ ] Stop test if server becomes unresponsive
- [ ] Document results for future reference

## Example Test Session

```bash
# Terminal 1: Start monitoring
./monitor_server.sh

# Terminal 2: Run load test
./run_load_test.sh
# Enter Quiz ID: 13
# Enter Session ID: 124
# Enter Join Code: ABC123
# Select: Quick Test (50 users, 2 min)

# Watch both terminals:
# - Monitor shows CPU, memory, connections
# - Load test shows RPS, response times, failures

# After test completes:
# - Check HTML report
# - Note maximum concurrent users handled
# - Document results
```

## Interpreting Results

### Example 1: Healthy Server
```
Users: 200
RPS: 250
P95 Response Time: 345ms
Failures: 0%
CPU: 45%
Memory: 38%
```
**Action:** Can handle more users, increase test size

### Example 2: Near Capacity
```
Users: 500
RPS: 420
P95 Response Time: 890ms
Failures: 2%
CPU: 78%
Memory: 62%
```
**Action:** Close to limit, recommend max 400-450 users

### Example 3: Overloaded
```
Users: 1000
RPS: 380 (decreasing)
P95 Response Time: 3200ms
Failures: 15%
CPU: 98%
Memory: 85%
```
**Action:** Over capacity, scale back to previous level

## Next Steps After Testing

### 1. Document Results
Create a capacity document:
```
Swaya.me Server Capacity (OCI VM - 4vCPU/24GB)
==============================================
Tested: 2024-XX-XX
Maximum Concurrent Users: XXX
Recommended Limit: XXX (80% of max)
P95 Response Time @ Max: XXXms
Notes: ...
```

### 2. Set Application Limits
- Configure max participants per quiz
- Add queue system if needed
- Show "Event Full" message at capacity

### 3. Production Monitoring
- Set up alerts (CPU > 70%, response time > 1000ms)
- Monitor participant counts in real-time
- Track performance metrics

### 4. Scaling Plan
Document when/how to scale:
- Vertical: Increase vCPUs/RAM
- Horizontal: Add backend instances + load balancer
- Database: Optimize queries, add read replicas

## Optimization Ideas (If Needed)

If capacity is lower than expected:

### Backend
- Increase Uvicorn workers (currently 2)
- Add connection pooling
- Enable Redis persistence
- Optimize database queries

### Database
- Add indexes on frequently queried fields
- Optimize slow queries
- Increase connection pool size

### Infrastructure
- Use CDN for static assets (images)
- Add load balancer for multiple backends
- Use database read replicas
- Implement caching layers

## Files Reference

| File | Purpose | Usage |
|------|---------|-------|
| `load_test.py` | Test script | Used by Locust |
| `run_load_test.sh` | Interactive runner | `./run_load_test.sh` |
| `monitor_server.sh` | Resource monitor | `./monitor_server.sh` |
| `LOAD_TEST_README.md` | Quick guide | Read first |
| `LOAD_TEST_GUIDE.md` | Full documentation | Reference |
| `EXAMPLE_WORKFLOW.sh` | Example walkthrough | `./EXAMPLE_WORKFLOW.sh` |
| `load_test_report.html` | Test results | Generated after test |

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| "Connection refused" | Check backend: `systemctl status swayame-backend` |
| "Locust not found" | Install: `cd backend && source .venv/bin/activate && pip install locust` |
| High failures immediately | Verify Session ID and Join Code are correct |
| Server unresponsive | Stop test (Ctrl+C), restart backend |
| "Too many connections" | Database limit reached, reduce users or increase limit |

## Support

For detailed information, see:
- Quick start: `LOAD_TEST_README.md`
- Full guide: `LOAD_TEST_GUIDE.md`
- Example: `./EXAMPLE_WORKFLOW.sh`

---

**Created:** 2024
**Status:** ✅ Ready to use
**Locust Version:** 2.43.3
