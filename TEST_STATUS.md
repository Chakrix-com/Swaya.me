# Incremental Load Test - RUNNING ✅

## Current Status

🔄 **AUTOMATED TESTING IN PROGRESS**

An incremental load test is running in the background to find your server's capacity limit.

## Quick Summary

**Test 1 Complete:** ✅ 100 users
- P95 Response Time: ~20ms ⚡
- Failures: 0% ✅
- RPS: 14.7
- **Result:** Excellent performance!

**Test 2:** 🔄 Running now (200 users)
**Tests 3-10:** ⏳ Queued (300-1000 users)

## Monitor Progress

```bash
# Quick status check
./CHECK_TEST_STATUS.sh

# Watch live output  
tail -f incremental_test_output.log

# Monitor server resources
./monitor_server.sh
```

## What's Being Tested

Each test:
- Creates fresh quiz session
- Spawns X concurrent users (100, 200, 300...)
- Each user joins and submits answers
- Runs for 3 minutes
- Collects performance metrics
- Increases by 100 users for next test

## Expected Timeline

- **Each test:** ~4 minutes
- **Total tests:** Up to 10 (will stop at breaking point)
- **Estimated completion:** ~30-40 minutes from start

## Results Location

All results are saved in `/home/vinay/Swaya.me/`:
- `load_test_100_users.html` - Test 1 detailed report
- `load_test_200_users.html` - Test 2 detailed report
- ... and so on

## What Happens Next

The test will automatically:
1. ✅ Run all tests up to 1000 users OR
2. ⏹️ Stop when breaking point is found (P95 > 1000ms or failures > 5%)
3. 📊 Generate HTML reports for each test
4. 💾 Save all logs

## After Completion

Once all tests complete, review the HTML reports to find:
- **Maximum capacity:** Where performance degraded
- **Recommended limit:** 80% of maximum
- **Comfortable range:** Sweet spot for production

## Manual Control

### Check if still running
```bash
ps aux | grep run_incremental
```

### Stop early (if needed)
```bash
# Find the process ID first
ps aux | grep run_incremental

# Then stop it with specific PID
# Example: kill 1234567
```

---

**Started:** 2026-02-21 12:44 UTC  
**Test 1 Result:** 100 users = ✅ Perfect (20ms P95, 0% failures)  
**Currently Running:** Test 2 (200 users)  
**Next:** Will auto-progress through 300, 400, 500... users

Check back in ~35 minutes for complete results!
