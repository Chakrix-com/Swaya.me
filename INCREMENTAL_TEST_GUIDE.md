# Incremental Load Test - In Progress

## What's Running

An **automated incremental load test** that increases concurrent users by 100 per test until the system breaks.

### Test Configuration
- **Start:** 100 users
- **Increment:** +100 users per test
- **Duration:** 3 minutes per test  
- **Max:** 1000 users
- **Credentials:** demo@swaya.me

### Test Sequence
1. ✅ Test 1: 100 users × 3 min
2. 🔄 Test 2: 200 users × 3 min (in progress)
3. ⏳ Test 3: 300 users × 3 min (pending)
4. ⏳ Test 4: 400 users × 3 min (pending)
5. ⏳ Test 5: 500 users × 3 min (pending)
6. ⏳ Test 6: 600 users × 3 min (pending)
7. ⏳ Test 7: 700 users × 3 min (pending)
8. ⏳ Test 8: 800 users × 3 min (pending)
9. ⏳ Test 9: 900 users × 3 min (pending)
10. ⏳ Test 10: 1000 users × 3 min (pending)

## How It Works

For each test:
1. **Create Session:** Fresh quiz session with join code
2. **Start Quiz:** Activate the quiz
3. **Open Question:** Make first question available
4. **Run Load Test:** Spawn users gradually (10/sec)
5. **Collect Metrics:** P95, P99, failures, RPS, CPU
6. **Save Results:** HTML report + log file
7. **Wait 30s:** Cool down before next test
8. **Repeat:** Increase users by 100

## Monitoring the Test

### Check Current Status
```bash
./CHECK_TEST_STATUS.sh
```

### Watch Live Output
```bash
tail -f incremental_test_output.log
```

### Monitor Server Resources
```bash
# In another terminal
./monitor_server.sh
```

## Results Files

Each test generates 2 files:
- **`load_test_XXX_users.html`** - Detailed HTML report with charts
- **`load_test_XXX_users.log`** - Text log with all output

## What to Look For

### Good Performance ✅
- P95 < 500ms
- P99 < 1000ms  
- Failures: 0%
- RPS increasing

### Warning Signs ⚠️
- P95 500-1000ms
- P99 1000-2000ms
- Failures: 1-5%
- RPS plateauing

### Breaking Point ❌
- P95 > 1000ms
- P99 > 2000ms
- Failures > 5%
- RPS decreasing

## Estimated Timeline

Each test: ~4 minutes
Total: Up to 10 tests
**Duration: ~40 minutes** (will stop early if breaking point found)

---

**Status:** 🔄 Running  
**Monitor:** `./CHECK_TEST_STATUS.sh`
