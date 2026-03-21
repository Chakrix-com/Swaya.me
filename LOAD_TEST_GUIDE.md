# Load Testing Guide for Swaya.me

## Overview
This guide helps you test how many concurrent participants your Swaya.me server can handle.

## Prerequisites

1. **Active Quiz:** You need a published quiz with at least one MCQ question
2. **Quiz Session:** Create an active quiz session
3. **Join Code:** Note the join code for the session

## Quick Start

### Step 1: Prepare Your Quiz

```bash
# 1. Login to Swaya.me at https://www.swaya.me
# 2. Create a quiz with at least one MCQ question
# 3. Publish the quiz
# 4. Start a quiz session
# 5. Note the JOIN CODE and SESSION ID
```

### Step 2: Update Test Configuration

Edit `load_test.py` and update these variables:

```python
QUIZ_ID = 13  # Your quiz ID
SESSION_ID = 124  # Your session ID (from URL /quiz/13/control)
JOIN_CODE = "ABC123"  # Your join code
```

### Step 3: Run the Load Test

#### Option A: Web UI (Recommended)

```bash
# Activate backend environment
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate

# Run Locust with web interface
locust -f /home/vinay/Swaya.me/load_test.py --host=https://www.swaya.me

# Open browser to: http://localhost:8089
# Configure:
#   - Number of users: Start with 10, increase gradually
#   - Spawn rate: 1-2 users per second
#   - Click "Start swarming"
```

#### Option B: Headless (Command Line)

```bash
# Run test with specific parameters
locust -f /home/vinay/Swaya.me/load_test.py \
       --host=https://www.swaya.me \
       --users 50 \
       --spawn-rate 5 \
       --run-time 5m \
       --headless

# This will:
# - Spawn 50 concurrent users
# - Add 5 new users per second
# - Run for 5 minutes
# - Output stats to terminal
```

## Understanding the Results

### Key Metrics

1. **Users:** Number of concurrent participants
2. **RPS (Requests Per Second):** Server throughput
3. **Response Time:** How fast the server responds
   - P50: 50% of requests faster than this
   - P95: 95% of requests faster than this
   - P99: 99% of requests faster than this
4. **Failure Rate:** Percentage of failed requests

### What to Look For

#### Healthy Server
```
Users: 100
RPS: 150
P95 Response Time: <500ms
Failure Rate: 0%
```

#### Server Under Stress
```
Users: 500
RPS: 200 (not increasing with users)
P95 Response Time: >2000ms
Failure Rate: 5-10%
```

#### Server Overloaded
```
Users: 1000
RPS: Decreasing
P95 Response Time: >5000ms
Failure Rate: >20%
```

## Testing Strategy

### Phase 1: Baseline (10-50 users)
```bash
locust -f load_test.py --host=https://www.swaya.me \
       --users 50 --spawn-rate 5 --run-time 2m --headless
```

**Goal:** Establish normal performance baseline

### Phase 2: Moderate Load (50-200 users)
```bash
locust -f load_test.py --host=https://www.swaya.me \
       --users 200 --spawn-rate 10 --run-time 5m --headless
```

**Goal:** Find comfortable operating range

### Phase 3: Stress Test (200-500 users)
```bash
locust -f load_test.py --host=https://www.swaya.me \
       --users 500 --spawn-rate 10 --run-time 5m --headless
```

**Goal:** Find performance degradation point

### Phase 4: Breaking Point (500-1000+ users)
```bash
locust -f load_test.py --host=https://www.swaya.me \
       --users 1000 --spawn-rate 20 --run-time 5m --headless
```

**Goal:** Find maximum capacity before failure

## What Gets Tested

The load test simulates real participants:

1. **Join Quiz:**
   - POST `/api/v1/quizzes/sessions/join`
   - Creates session token

2. **Poll for Questions:**
   - GET `/api/v1/quizzes/sessions/{id}/results`
   - Checks every 1-3 seconds

3. **Submit Answers:**
   - POST `/api/v1/quizzes/sessions/submit-answer`
   - Random MCQ answers

## Resource Monitoring

While running load tests, monitor server resources:

### CPU Usage
```bash
# Watch CPU in real-time
htop

# Or specific processes
top -p $(pgrep -f uvicorn)
```

### Memory Usage
```bash
# Overall memory
free -h

# Python processes
ps aux | grep python | awk '{sum+=$6} END {print sum/1024 " MB"}'
```

### Database Connections
```bash
# MySQL connections
mysql -u swayame_user -p -e "SHOW PROCESSLIST;"

# Count active connections
mysql -u swayame_user -p -e "SHOW STATUS LIKE 'Threads_connected';"
```

### Redis Performance
```bash
# Redis info
redis-cli INFO stats

# Monitor commands
redis-cli MONITOR
```

### Network Usage
```bash
# Network stats
iftop

# Or
nload
```

## Interpreting Server Specs

Your current server (OCI VM):
```
CPU: 4 vCPUs (ARM)
RAM: 24 GB
Disk: Fast SSD
Network: 1-10 Gbps
```

**Estimated Capacity:**
- **Conservative:** 200-300 concurrent users
- **Moderate:** 500-800 concurrent users
- **Optimistic:** 1000+ concurrent users

Actual capacity depends on:
- Database performance
- Redis performance
- Question complexity
- Network latency
- Code optimization

## Optimization Tips

If you hit limits before expected:

### Backend Optimization
1. **Increase Uvicorn Workers:**
   ```bash
   # Edit systemd service
   ExecStart=... --workers 4  # Increase from 2
   ```

2. **Add Database Connection Pooling:**
   - Already using SQLAlchemy pool
   - Increase pool size if needed

3. **Redis Optimization:**
   - Enable persistence if needed
   - Adjust maxmemory policy

### Database Optimization
1. **Add Indexes:**
   - session_token (already indexed)
   - participant lookups
   - answer queries

2. **Query Optimization:**
   - Review slow queries
   - Add query caching

### Infrastructure
1. **Horizontal Scaling:**
   - Add more backend instances
   - Load balancer in front

2. **Caching:**
   - CDN for static assets
   - Redis for session data (already doing)

## Safety Notes

⚠️ **Important:**
1. Don't run load tests on production during real events
2. Start with small numbers (10-50 users)
3. Monitor server resources continuously
4. Have backup plan if server crashes
5. Test during off-peak hours

## Sample Test Plan

### Test 1: Baseline
- Users: 50
- Duration: 2 minutes
- Expected: All green, <200ms P95

### Test 2: Normal Load
- Users: 200
- Duration: 5 minutes
- Expected: All green, <500ms P95

### Test 3: Peak Load
- Users: 500
- Duration: 5 minutes
- Expected: Some yellow, <1000ms P95

### Test 4: Stress
- Users: 1000
- Duration: 5 minutes
- Expected: Find breaking point

## Troubleshooting

### "Connection Refused"
- Backend not running
- Check: `systemctl status swayame-backend`

### High Failure Rate
- Server overloaded
- Reduce users or increase resources

### Slow Response Times
- Database bottleneck
- Redis bottleneck
- CPU maxed out

### "Too Many Open Files"
- Increase file descriptor limit
- `ulimit -n 65536`

## Next Steps After Testing

1. **Document Results:**
   - Note max concurrent users
   - Note response times
   - Note failure threshold

2. **Set Limits:**
   - Configure max participants per quiz
   - Add queue system if needed

3. **Monitoring:**
   - Set up alerts for high load
   - Monitor in production

4. **Scaling Plan:**
   - Document when to scale
   - Prepare additional resources
