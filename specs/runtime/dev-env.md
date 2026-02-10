# Development Environment Setup

This document describes how to set up a local development environment for Swaya.me.

**All development tools and dependencies are 100% open source and free.**

---

## Prerequisites

### Required Software (All Open Source)

| Tool | Version | License | Purpose |
|------|---------|---------|---------|  
| **Python** | 3.11+ | PSF License (Open Source) | Backend development |
| **Node.js** | 18+ | MIT (Open Source) | Frontend development |
| **npm/yarn** | Latest | Artistic 2.0 / BSD (Open Source) | Package management |
| **Docker** | 24.0+ | Apache 2.0 (Open Source) | Local services (Redis, MySQL) |
| **Docker Compose** | 2.20+ | Apache 2.0 (Open Source) | Multi-container orchestration |
| **Git** | 2.40+ | GPL v2 (Open Source) | Version control |
| **VS Code** | Latest | MIT (Open Source) | Recommended IDE |

### Recommended VS Code Extensions (All Free/Open Source)

- **Python** (Microsoft) - Python language support
- **Pylance** (Microsoft) - Python type checking
- **ESLint** (Open Source) - JavaScript/TypeScript linting
- **Prettier** (Open Source) - Code formatting
- **Docker** (Microsoft) - Docker container management
- **GitLens** (Open Source) - Git visualization
- **REST Client** (Open Source) or **Thunder Client** (Free) - API testing

---

## Backend Setup

### Step 1: Clone Repository

```bash
git clone https://gitea.example.com/your-org/swaya.me.git
cd swaya.me/backend
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools (pytest, black, etc.)
```

### Step 4: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with local values
nano .env
```

**Local Development .env**:
```bash
DB_HOST=localhost
DB_PORT=3306
DB_NAME=swaya_dev
DB_USER=root
DB_PASSWORD=localpass

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

JWT_SECRET=dev_secret_key_not_for_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

HOST=0.0.0.0
PORT=8000
DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000

LOG_LEVEL=DEBUG
```

### Step 5: Start Local Services (Docker)

```bash
# From project root
docker-compose -f docker-compose.dev.yml up -d

# Verify services
docker-compose ps
```

**docker-compose.dev.yml**:
```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: swaya-dev-mysql
    restart: unless-stopped
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: localpass
      MYSQL_DATABASE: swaya_dev
    volumes:
      - mysql-dev-data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    container_name: swaya-dev-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-dev-data:/data

volumes:
  mysql-dev-data:
  redis-dev-data:
```

### Step 6: Run Database Migrations

```bash
# Ensure venv is activated
source venv/bin/activate

# Run migrations
alembic upgrade head

# Seed test data
python scripts/seed_data.py
```

### Step 7: Start Backend Server

```bash
# Development mode (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# OR using make command (if Makefile exists)
make run
```

### Step 8: Verify Backend

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status": "healthy", "timestamp": "2026-01-27T10:00:00Z"}
```

---

## Frontend Setup

### Step 1: Navigate to Frontend Directory

```bash
cd swaya.me/frontend
```

### Step 2: Install Dependencies

```bash
npm install
```

### Step 3: Configure Environment

```bash
# Copy template
cp .env.example .env.development

# Edit .env.development
nano .env.development
```

**.env.development**:
```bash
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_POLL_INTERVAL=2000
REACT_APP_DEBUG=true
```

### Step 4: Start Development Server

```bash
npm start

# OR
npm run dev
```

### Step 5: Verify Frontend

Open browser and navigate to: `http://localhost:3000`.

If you develop by SSH-ing into the server:

- For hot-reload, port-forward the dev server and use `http://localhost:3000` on your machine.
- For production build testing, run `npm run build` and verify at https://www.swaya.me.

---

## Frontend Static Hosting (aaPanel + Nginx)

When testing the production build on the server, the frontend is served by **Nginx managed via aaPanel** from:

```
/home/vinay/Swaya.me/frontend/dist
```

Hosted URL:

- https://www.swaya.me

Notes:

- Run `npm run build` in `frontend/` to refresh the `dist` output.
- Nginx serves only the files already in `dist`; source changes do not appear until a rebuild.
- Cache-busting applied in `index.html` is included in `dist` only after rebuild.

---

## Development Workflow

### Backend Development

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

#### Code Formatting

```bash
# Format code with black
black .

# Sort imports
isort .

# Lint with flake8
flake8 .
```

#### Type Checking

```bash
# Run mypy for type checking
mypy backend/
```

### Frontend Development

#### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test -- screens/Login.test.tsx
```

#### Code Formatting

```bash
# Format with Prettier
npm run format

# Lint with ESLint
npm run lint

# Fix linting issues
npm run lint:fix
```

#### Build for Production

```bash
npm run build
```

---

## Database Management

### Connect to MySQL

```bash
mysql -h localhost -u root -p swaya_dev
```

### Common MySQL Commands

```sql
-- Show tables
SHOW TABLES;

-- Describe table structure
DESCRIBE users;

-- Query data
SELECT * FROM users LIMIT 10;

-- Clear table (use with caution!)
TRUNCATE TABLE submissions;
```

### Create New Migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "Add new column to users"

# Manually create migration
alembic revision -m "Custom migration"
```

### Reset Database

```bash
# Drop all tables
alembic downgrade base

# Recreate all tables
alembic upgrade head

# Seed test data
python scripts/seed_data.py
```

---

## Redis Management

### Connect to Redis CLI

```bash
docker exec -it swaya-dev-redis redis-cli
```

### Common Redis Commands

```bash
# View all keys
KEYS *

# Get key value
GET session:sess_xyz:state

# Delete key
DEL session:sess_xyz:state

# Clear all keys
FLUSHALL

# Monitor real-time commands
MONITOR
```

---

## API Testing

### Using Thunder Client (VS Code Extension)

1. Install Thunder Client extension
2. Create new request
3. Set URL: `http://localhost:8000/api/v1/auth/login`
4. Set method: POST
5. Set body:
   ```json
   {
     "email": "host@example.com",
     "password": "password123"
   }
   ```
6. Send request
7. Copy token from response

### Using curl

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"host@example.com","password":"password123"}'

# Create quiz (with token)
curl -X POST http://localhost:8000/api/v1/quizzes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"title":"Test Quiz","description":"Testing"}'
```

### Using Postman Collection (Post-MVP)

Import `docs/postman_collection.json` into Postman for pre-configured API requests.

---

## Hot Reload

### Backend

```bash
# uvicorn with --reload automatically restarts on code changes
uvicorn main:app --reload
```

### Frontend

```bash
# React dev server automatically reloads on code changes
npm start
```

---

## Debugging

### Backend Debugging (VS Code)

**launch.json**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

### Frontend Debugging (VS Code)

**launch.json**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Chrome: React",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000",
      "webRoot": "${workspaceFolder}/frontend/src"
    }
  ]
}
```

---

## Common Issues & Solutions

### Issue: Database connection failed

**Solution**:
```bash
# Ensure MySQL container is running
docker-compose ps

# Check MySQL logs
docker logs swaya-dev-mysql

# Verify credentials in .env
cat .env | grep DB_
```

### Issue: Redis connection failed

**Solution**:
```bash
# Ensure Redis container is running
docker-compose ps

# Test Redis connection
docker exec -it swaya-dev-redis redis-cli PING
# Expected: PONG
```

### Issue: Port already in use

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Issue: npm install fails

**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

---

## Quick Start Summary

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker-compose -f docker-compose.dev.yml up -d
alembic upgrade head
python scripts/seed_data.py
uvicorn main:app --reload

# Frontend (in new terminal)
cd frontend
npm install
cp .env.example .env.development
npm start
```

---

## Development Tooling Versions

| Tool | Minimum Version | Recommended Version |
|------|----------------|---------------------|
| Python | 3.11 | 3.11.7 |
| Node.js | 18.0 | 20.10 LTS |
| npm | 9.0 | 10.2 |
| Docker | 24.0 | 25.0 |
| MySQL | 8.0 | 8.0.35 |
| Redis | 7.0 | 7.2 |

---

## Performance Tips

- Use **virtual environment** to isolate Python dependencies
- Enable **hot reload** for faster development iteration
- Use **Redis GUI** (RedisInsight) for easier debugging
- Use **MySQL Workbench** for database management
- Enable **React DevTools** browser extension
- Enable **Redux DevTools** browser extension
