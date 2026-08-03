╔════════════════════════════════════════════════════════════════════════╗
║                    SWAYA.ME LOAD TESTING - CHEAT SHEET                 ║
╚════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│ QUICK START (3 STEPS)                                                   │
└─────────────────────────────────────────────────────────────────────────┘

  1. Create Quiz Session
     → https://www.swaya.me
     → Create quiz → Start session
     → Note: Join Code & Session ID

  2. Run Load Test
     → cd /home/vinay/Swaya.me/scripts/load-tests
     → ./run_load_test.sh

  3. Monitor Server (optional)
     → Open new terminal
     → cd /home/vinay/Swaya.me/scripts
     → ./monitor_server.sh


┌─────────────────────────────────────────────────────────────────────────┐
│ COMMANDS                                                                 │
└─────────────────────────────────────────────────────────────────────────┘

  Interactive Test:
    cd /home/vinay/Swaya.me/scripts/load-tests
    ./run_load_test.sh

  Monitor Resources:
    /home/vinay/Swaya.me/scripts/monitor_server.sh

  Manual Test (Web UI):
    cd /home/vinay/Swaya.me/backend
    source .venv/bin/activate
    locust -f ../scripts/load-tests/load_test.py --host=https://www.swaya.me
    # Open: http://localhost:8089

  Manual Test (CLI):
    cd /home/vinay/Swaya.me/backend
    source .venv/bin/activate
    locust -f ../scripts/load-tests/load_test.py --host=https://www.swaya.me \
           --users 100 --spawn-rate 10 --run-time 3m --headless

  Other runners in this directory (not covered step-by-step above):
    run_high_load_test.sh, run_incremental_load_test.sh, run_proctoring_load_test.sh
    locustfile.py, locustfile_multi_host.py, locustfile_proctoring.py, locustfile_realistic.py


┌─────────────────────────────────────────────────────────────────────────┐
│ TEST PROFILES                                                            │
└─────────────────────────────────────────────────────────────────────────┘

  Quick Test:      50 users,   2 min  (baseline)
  Moderate Test:  200 users,   5 min  (realistic event)
  Stress Test:    500 users,   5 min  (find limits)
  Custom:         Your choice


┌─────────────────────────────────────────────────────────────────────────┐
│ INTERPRETING RESULTS                                                     │
└─────────────────────────────────────────────────────────────────────────┘

  Response Time (P95):
    ✅ < 500ms   → Excellent
    ⚠️ 500-1000ms → Acceptable
    ❌ > 2000ms   → Overloaded

  Failure Rate:
    ✅ 0%        → Perfect
    ⚠️ 1-5%      → Acceptable
    ❌ > 10%      → Problem

  CPU Usage:
    ✅ < 60%     → Good
    ⚠️ 60-80%    → Near limit
    ❌ > 90%      → Bottleneck

  RPS (Requests/sec):
    ✅ Increasing with users → Good
    ❌ Plateauing/decreasing → At capacity


┌─────────────────────────────────────────────────────────────────────────┐
│ EXPECTED CAPACITY (Your Server: 4 vCPU, 24GB RAM)                       │
└─────────────────────────────────────────────────────────────────────────┘

  Baseline:     50-100 users   (should be perfect)
  Comfortable:  200-300 users   (typical event)
  Stress:       500-800 users   (pushing limits)
  Maximum:     1000+ users      (may degrade)


┌─────────────────────────────────────────────────────────────────────────┐
│ SAFETY CHECKLIST                                                         │
└─────────────────────────────────────────────────────────────────────────┘

  ☐ Test during off-peak hours (no real users online)
  ☐ Start with small numbers (50 users first)
  ☐ Monitor server resources while testing
  ☐ Have restart plan ready if server struggles
  ☐ Increase gradually (50 → 100 → 200 → 500)


┌─────────────────────────────────────────────────────────────────────────┐
│ TROUBLESHOOTING                                                          │
└─────────────────────────────────────────────────────────────────────────┘

  Problem: "Connection refused"
  → Check backend: systemctl status swayame-backend
  → Restart: sudo systemctl restart swayame-backend

  Problem: "Locust not found"
  → cd backend && source .venv/bin/activate
  → pip install locust

  Problem: High failures immediately
  → Verify Quiz ID, Session ID, Join Code correct
  → Check session is ACTIVE (not ended)

  Problem: Server becomes unresponsive
  → Stop test: Ctrl+C
  → Restart: sudo systemctl restart swayame-backend


┌─────────────────────────────────────────────────────────────────────────┐
│ FILES                                                                    │
└─────────────────────────────────────────────────────────────────────────┘

  load_test.py             - Locust test script (this directory)
  run_load_test.sh         - Interactive runner ⭐ (this directory)
  ../monitor_server.sh     - Resource monitor (one level up, in scripts/)
  README.md                - This file
  load_test_report.html    - Generated after test (written to repo root)


┌─────────────────────────────────────────────────────────────────────────┐
│ TYPICAL WORKFLOW                                                         │
└─────────────────────────────────────────────────────────────────────────┘

  Terminal 1:
    cd /home/vinay/Swaya.me/scripts
    ./monitor_server.sh
    # Watch: CPU, Memory, Connections

  Terminal 2:
    cd /home/vinay/Swaya.me/scripts/load-tests
    ./run_load_test.sh
    # Enter: Quiz ID, Session ID, Join Code
    # Select: Test profile

  Browser:
    https://www.swaya.me/quiz/13/control
    # Watch participants joining in real-time!

  After Test:
    Open: /home/vinay/Swaya.me/load_test_report.html
    # Review detailed statistics


┌─────────────────────────────────────────────────────────────────────────┐
│ INCREMENTAL TESTING STRATEGY                                             │
└─────────────────────────────────────────────────────────────────────────┘

  Test 1:   50 users × 2 min → All ✅? Continue
  Test 2:  100 users × 3 min → All ✅? Continue
  Test 3:  200 users × 5 min → All ✅? Continue
  Test 4:  500 users × 5 min → Yellow ⚠️? Near limit
  Test 5: 1000 users × 5 min → Red ❌? Found max!

  Your Limit = Last test with all green metrics


┌─────────────────────────────────────────────────────────────────────────┐
│ WHAT THE TEST DOES                                                       │
└─────────────────────────────────────────────────────────────────────────┘

  Each simulated user:
    1. Joins quiz with random name (User_1234)
    2. Polls for current question (every 1-3 sec)
    3. Submits random answer (A, B, C, or D)
    4. Checks results
    5. Repeats until test ends

  You'll see:
    - Participant count increasing in Quiz Control
    - Real quiz participants joining
    - Answers being submitted
    - Server handling concurrent load


╔════════════════════════════════════════════════════════════════════════╗
║ READY TO TEST!                                                          ║
║                                                                          ║
║ Quick start: cd scripts/load-tests && ./run_load_test.sh                ║
║ Full guide:  cat scripts/load-tests/README.md (this file)               ║
╚════════════════════════════════════════════════════════════════════════╝
