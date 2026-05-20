#!/bin/bash
# Swaya.me Server Resource Monitor
# Run this in a separate terminal while load testing

echo "======================================"
echo "Swaya.me Server Resource Monitor"
echo "======================================"
echo ""
echo "Monitoring backend processes..."
echo "Press Ctrl+C to stop"
echo ""

# Find backend PID
BACKEND_PID=$(pgrep -f "uvicorn main:app")

if [ -z "$BACKEND_PID" ]; then
    echo "❌ Backend not running!"
    exit 1
fi

echo "✅ Backend PID: $BACKEND_PID"
echo ""

# Monitoring loop
while true; do
    clear
    echo "======================================"
    echo "Swaya.me Resource Monitor - $(date '+%H:%M:%S')"
    echo "======================================"
    echo ""
    
    # CPU and Memory for backend
    echo "📊 Backend Process (PID: $BACKEND_PID)"
    echo "--------------------------------------"
    ps -p $BACKEND_PID -o %cpu,%mem,vsz,rss,cmd 2>/dev/null | tail -n +2 || echo "Process not found"
    echo ""
    
    # All Python processes
    echo "🐍 All Python Processes"
    echo "--------------------------------------"
    PYTHON_MEM=$(ps aux | grep python | grep -v grep | awk '{sum+=$6} END {print sum/1024}')
    PYTHON_CPU=$(ps aux | grep python | grep -v grep | awk '{sum+=$3} END {print sum}')
    echo "Total CPU: ${PYTHON_CPU:-0}%"
    echo "Total Memory: ${PYTHON_MEM:-0} MB"
    echo ""
    
    # System Overview
    echo "💻 System Resources"
    echo "--------------------------------------"
    
    # CPU
    CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    echo "CPU Usage: ${CPU_IDLE}%"
    
    # Memory
    free -h | grep "Mem:" | awk '{print "Memory: " $3 " / " $2 " (" int($3/$2*100) "%)"}'
    
    # Load Average
    uptime | awk -F'load average:' '{print "Load Average:" $2}'
    echo ""
    
    # Network Connections
    echo "🌐 Network Connections"
    echo "--------------------------------------"
    ESTABLISHED=$(netstat -an 2>/dev/null | grep ESTABLISHED | wc -l)
    BACKEND_CONNS=$(netstat -anp 2>/dev/null | grep ":8000" | grep ESTABLISHED | wc -l)
    echo "Total Established: $ESTABLISHED"
    echo "Backend Port 8000: $BACKEND_CONNS"
    echo ""
    
    # MySQL (if accessible)
    echo "🗄️  Database Connections"
    echo "--------------------------------------"
    MYSQL_CONNS=$(mysql -u swayame_user -pPowerUser2024_09 -e "SHOW STATUS LIKE 'Threads_connected';" 2>/dev/null | tail -n 1 | awk '{print $2}')
    if [ ! -z "$MYSQL_CONNS" ]; then
        echo "MySQL Connections: $MYSQL_CONNS"
    else
        echo "MySQL: Unable to connect"
    fi
    echo ""
    
    # Redis
    echo "⚡ Redis Status"
    echo "--------------------------------------"
    REDIS_CONNS=$(redis-cli INFO clients 2>/dev/null | grep connected_clients | cut -d: -f2 | tr -d '\r')
    REDIS_MEM=$(redis-cli INFO memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    if [ ! -z "$REDIS_CONNS" ]; then
        echo "Connections: $REDIS_CONNS"
        echo "Memory: $REDIS_MEM"
    else
        echo "Redis: Unable to connect"
    fi
    echo ""
    
    # Disk I/O
    echo "💾 Disk I/O"
    echo "--------------------------------------"
    iostat -x 1 1 | grep -A1 "Device" | tail -n 1 | awk '{print "r/s: " $4 ", w/s: " $5}'
    echo ""
    
    echo "======================================"
    echo "Refreshing in 2 seconds... (Ctrl+C to stop)"
    echo "======================================"
    
    sleep 2
done
