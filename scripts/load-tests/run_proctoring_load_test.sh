#!/bin/bash
# Proctoring & AI Load Test Runner for Swaya.me

echo "======================================"
echo "Swaya.me Proctoring & AI Load Test"
echo "======================================"
echo ""

# Activate environment
cd /home/vinay/Swaya.me/backend
source .venv/bin/activate
cd ..

echo "✅ Environment activated"
echo ""

# Get configuration from user
echo "📝 Configuration"
echo "--------------------------------------"
echo ""

read -p "Enter Quiz ID: " QUIZ_ID
read -p "Enter Session ID: " SESSION_ID
read -p "Enter Join Code: " JOIN_CODE

if [ -z "$QUIZ_ID" ] || [ -z "$SESSION_ID" ] || [ -z "$JOIN_CODE" ]; then
    echo "ERROR: All IDs are required."
    exit 1
fi

echo ""
echo "📊 Test Configuration"
echo "--------------------------------------"

PS3="Select test type: "
options=("Quick Test (50 users, 2 min)" "Moderate Test (200 users, 5 min)" "Stress Test (500 users, 5 min)" "Custom")
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
        *) echo "Invalid option";;
    esac
done

export QUIZ_ID=$QUIZ_ID
export SESSION_ID=$SESSION_ID
export JOIN_CODE=$JOIN_CODE
export APP_BASE_URL="${APP_BASE_URL:-https://test.swaya.me}"

echo ""
echo "🚀 Starting Proctoring Load Test..."
echo "Target: $APP_BASE_URL"
echo "======================================"
echo ""

locust -f locustfile_proctoring.py \
       --host=$APP_BASE_URL \
       --users $USERS \
       --spawn-rate $SPAWN_RATE \
       --run-time $RUN_TIME \
       --headless \
       --html=proctoring_load_report.html

echo ""
echo "======================================"
echo "✅ Load Test Complete!"
echo "📊 Report: proctoring_load_report.html"
echo "======================================"
