#!/bin/bash
# Quick Load Test Runner for Swaya.me

echo "======================================"
echo "Swaya.me Load Test - Quick Start"
echo "======================================"
echo ""

# Check if Locust is installed
if ! command -v locust &> /dev/null; then
    echo "❌ Locust not found. Installing..."
    cd /home/vinay/Swaya.me/backend
    source .venv/bin/activate
    pip install locust
fi

# Activate environment
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate

echo "✅ Environment activated"
echo ""

# Get configuration from user
echo "📝 Configuration"
echo "--------------------------------------"
echo ""

read -p "Enter Quiz ID [13]: " QUIZ_ID
QUIZ_ID=${QUIZ_ID:-13}

read -p "Enter Session ID: " SESSION_ID

read -p "Enter Join Code: " JOIN_CODE

if [ -z "$SESSION_ID" ] || [ -z "$JOIN_CODE" ]; then
    echo ""
    echo "⚠️  WARNING: You need to:"
    echo "   1. Create a quiz at https://www.swaya.me"
    echo "   2. Start a quiz session"
    echo "   3. Note the Session ID (from URL)"
    echo "   4. Note the Join Code (displayed on screen)"
    echo ""
    echo "Then run this script again with those values."
    exit 1
fi

echo ""
echo "📊 Test Configuration"
echo "--------------------------------------"

PS3="Select test type: "
options=("Quick Test (50 users, 2 min)" "Moderate Test (200 users, 5 min)" "Stress Test (500 users, 5 min)" "Custom" "Web UI (manual control)")
select opt in "${options[@]}"
do
    case $opt in
        "Quick Test (50 users, 2 min)")
            USERS=50
            SPAWN_RATE=5
            RUN_TIME="2m"
            break
            ;;
        "Moderate Test (200 users, 5 min)")
            USERS=200
            SPAWN_RATE=10
            RUN_TIME="5m"
            break
            ;;
        "Stress Test (500 users, 5 min)")
            USERS=500
            SPAWN_RATE=10
            RUN_TIME="5m"
            break
            ;;
        "Custom")
            read -p "Number of users: " USERS
            read -p "Spawn rate (users/sec): " SPAWN_RATE
            read -p "Run time (e.g., 5m): " RUN_TIME
            break
            ;;
        "Web UI (manual control)")
            WEB_UI=true
            break
            ;;
        *) echo "Invalid option";;
    esac
done

echo ""
echo "✅ Configuration Complete"
echo "--------------------------------------"
echo "Quiz ID: $QUIZ_ID"
echo "Session ID: $SESSION_ID"
echo "Join Code: $JOIN_CODE"
if [ "$WEB_UI" = true ]; then
    echo "Mode: Web UI"
else
    echo "Users: $USERS"
    echo "Spawn Rate: $SPAWN_RATE/sec"
    echo "Duration: $RUN_TIME"
fi
echo "--------------------------------------"
echo ""

# Update the load test file with configuration
echo "📝 Updating test configuration..."
sed -i "s/QUIZ_ID = [0-9]*/QUIZ_ID = $QUIZ_ID/" /home/vinay/Swaya.me/load_test.py
sed -i "s/SESSION_ID = None/SESSION_ID = $SESSION_ID/" /home/vinay/Swaya.me/load_test.py
sed -i "s/JOIN_CODE = None/JOIN_CODE = \"$JOIN_CODE\"/" /home/vinay/Swaya.me/load_test.py

echo "✅ Configuration updated in load_test.py"
echo ""

# Offer to start monitoring
echo "💡 TIP: Open another terminal and run:"
echo "   ./monitor_server.sh"
echo ""
read -p "Press Enter to start load test..."

echo ""
echo "🚀 Starting Load Test..."
echo "======================================"
echo ""

# Run the test
if [ "$WEB_UI" = true ]; then
    echo "Opening Web UI at http://localhost:8089"
    echo "Configure your test parameters in the browser."
    echo ""
    locust -f /home/vinay/Swaya.me/load_test.py --host=https://www.swaya.me
else
    locust -f /home/vinay/Swaya.me/load_test.py \
           --host=https://www.swaya.me \
           --users $USERS \
           --spawn-rate $SPAWN_RATE \
           --run-time $RUN_TIME \
           --headless \
           --html=/home/vinay/Swaya.me/load_test_report.html
    
    echo ""
    echo "======================================"
    echo "✅ Load Test Complete!"
    echo "======================================"
    echo ""
    echo "📊 HTML Report saved to:"
    echo "   /home/vinay/Swaya.me/load_test_report.html"
    echo ""
fi
