#!/bin/bash
# Development setup script

set -e

echo "🚀 Swaya.me Backend Setup"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# Copy .env.example to .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration"
fi

# Wait for database
echo "Waiting for MySQL..."
until docker exec swaya-dev-mysql mysqladmin ping -h"localhost" -u"root" -p"localpass" --silent; do
    echo "   MySQL is unavailable - sleeping"
    sleep 2
done
echo "✓ MySQL is ready"

# Run migrations
echo "Running database migrations..."
alembic upgrade head || echo "⚠️  No migrations found - run 'alembic revision --autogenerate -m \"initial\"' first"

# Seed database
echo "Seeding database..."
python scripts/seed_data.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  source .venv/bin/activate"
echo "  uvicorn main:app --reload"
echo ""
