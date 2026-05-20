#!/bin/bash

# Pre-Startup Verification Script
# Run this before starting the backend to catch configuration and data issues early

set -e

echo "=================================================="
echo "🚀 Swaya.me Pre-Startup Verification"
echo "=================================================="

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$BACKEND_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counter for issues
ISSUES=0

# 1. Check Python environment
echo -e "\n📋 Checking Python environment..."
if [ -d ".venv" ]; then
    echo -e "${GREEN}✅${NC} Virtual environment exists"
    source .venv/bin/activate
else
    echo -e "${RED}❌${NC} Virtual environment not found at .venv"
    echo "   Run: python3 -m venv .venv && source .venv/bin/activate"
    ((ISSUES++))
fi

# 2. Check .env file
echo -e "\n📋 Checking configuration (.env)..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✅${NC} .env file exists"
    
    # Check critical env vars
    for var in "DB_HOST" "DB_NAME" "DB_USER" "DB_PASSWORD" "JWT_SECRET"; do
        if grep -q "^$var=" .env; then
            echo -e "   ${GREEN}✅${NC} $var is set"
        else
            echo -e "   ${YELLOW}⚠️${NC} $var not found in .env"
            ((ISSUES++))
        fi
    done
else
    echo -e "${RED}❌${NC} .env file not found"
    echo "   Copy .env.example to .env and update values"
    ((ISSUES++))
fi

# 3. Check database connection
echo -e "\n📋 Checking database connection..."
python3 << 'PYEOF'
import sys
import os
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv()

try:
    from persistence.database import engine
    # Try to connect
    with engine.connect() as conn:
        print("\033[0;32m✅\033[0m Database connection successful")
except Exception as e:
    print(f"\033[0;31m❌\033[0m Database connection failed: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    ((ISSUES++))
fi

# 4. Check database schema
echo -e "\n📋 Checking database schema..."
python3 << 'PYEOF'
import sys
from sqlalchemy import inspect

try:
    from persistence.database import engine
    inspector = inspect(engine)
    
    required_tables = [
        'tenants', 'users', 'events', 'quizzes', 'questions',
        'quiz_sessions', 'participants', 'answers'
    ]
    
    existing_tables = inspector.get_table_names()
    
    for table in required_tables:
        if table in existing_tables:
            print(f"\033[0;32m✅\033[0m Table '{table}' exists")
        else:
            print(f"\033[0;31m❌\033[0m Table '{table}' not found")
            print("   Run: alembic upgrade head")
            sys.exit(1)
            
except Exception as e:
    print(f"\033[0;31m❌\033[0m Schema check failed: {e}")
    sys.exit(1)
PYEOF

if [ $? -ne 0 ]; then
    ((ISSUES++))
fi

# 5. Check demo data
echo -e "\n📋 Checking demo data..."
python3 << 'PYEOF'
import sys
from sqlalchemy.orm import Session
from persistence.database import SessionLocal
from persistence.models.core import User, Tenant

db = SessionLocal()
try:
    demo_user = db.query(User).filter(User.email == "demo@swaya.me").first()
    
    if demo_user:
        print(f"\033[0;32m✅\033[0m Demo user exists (demo@swaya.me)")
        
        demo_tenant = db.query(Tenant).filter(Tenant.id == demo_user.tenant_id).first()
        if demo_tenant and demo_tenant.is_active:
            print(f"\033[0;32m✅\033[0m Demo tenant is active")
        else:
            print(f"\033[1;33m⚠️\033[0m Demo tenant is inactive - run: python scripts/seed_data.py")
    else:
        print(f"\033[1;33m⚠️\033[0m Demo user not found - run: python scripts/seed_data.py")
        
finally:
    db.close()
PYEOF

if [ $? -ne 0 ]; then
    ((ISSUES++))
fi

# 6. Database health check
echo -e "\n📋 Running database health check..."
python3 scripts/db_health_check.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅${NC} Database integrity check passed"
else
    echo -e "${YELLOW}⚠️${NC} Database health check found issues"
    python3 scripts/db_health_check.py
    ((ISSUES++))
fi

# Final summary
echo ""
echo "=================================================="
echo "📊 Pre-Startup Summary"
echo "=================================================="

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "You can now start the backend:"
    echo "  cd /path/to/backend"
    echo "  uvicorn main:app --host 0.0.0.0 --port 8000"
    exit 0
else
    echo -e "${RED}❌ Found $ISSUES issue(s) that need to be fixed${NC}"
    echo ""
    echo "Please fix the issues above before starting the backend."
    exit 1
fi

