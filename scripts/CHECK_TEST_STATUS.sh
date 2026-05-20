#!/bin/bash
# Check status of incremental load test

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║              Incremental Load Test - Status Check                     ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if test is running
if ps aux | grep -q "[r]un_incremental_load_test"; then
    echo "✅ Test is RUNNING"
    echo ""
    PID=$(ps aux | grep "[r]un_incremental_load_test" | awk '{print $2}')
    echo "Process ID: $PID"
    echo ""
else
    echo "❌ Test is NOT running"
    echo ""
fi

# Show current test
echo "Current Test Status:"
echo "═══════════════════════════════════════════════════════════════════════"
tail -30 incremental_test_output.log 2>/dev/null | grep -A 5 "TEST [0-9]:" | tail -6
echo ""

# Show completed tests
echo "Completed Tests:"
echo "═══════════════════════════════════════════════════════════════════════"
ls -1 load_test_*_users.html 2>/dev/null | while read file; do
    users=$(echo $file | sed 's/load_test_\([0-9]*\)_users.html/\1/')
    size=$(ls -lh $file | awk '{print $5}')
    echo "  ✅ $users users - Report: $file ($size)"
done
echo ""

# Show quick results from logs
echo "Quick Results Summary:"
echo "═══════════════════════════════════════════════════════════════════════"
for log in load_test_*_users.log; do
    if [ -f "$log" ]; then
        users=$(echo $log | sed 's/load_test_\([0-9]*\)_users.log/\1/')
        stats=$(grep "Aggregated" "$log" | tail -1)
        echo "[$users users] $stats"
    fi
done
echo ""

echo "Commands:"
echo "  Monitor live: tail -f incremental_test_output.log"
echo "  View report: open load_test_XXX_users.html"
echo ""

