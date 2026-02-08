# Swaya.me UI Testing Guide

## Prerequisites Setup

Since Docker and Python tools need to be installed on your system, follow these steps:

### 1. Install Required Tools

```bash
# Install Python venv
sudo apt update
sudo apt install -y python3.10-venv python3-pip

# Install Docker (if not already installed)
sudo apt install -y docker.io docker-compose

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

---

## Quick Start for UI Testing

### Step 1: Start Infrastructure (MySQL + Redis)

```bash
cd /home/vinay/Swaya.me

# Start MySQL and Redis with Docker
docker compose -f docker-compose.dev.yml up -d mysql redis

# Wait for services to be ready (30 seconds)
sleep 30

# Verify services are running
docker ps
```

### Step 2: Setup Backend

```bash
cd /home/vinay/Swaya.me/backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env

# Run database migrations
alembic upgrade head

# Seed demo data
python scripts/seed_data.py

# Start backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will run at:** http://localhost:8000

Leave this terminal running and open a new terminal for frontend.

### Step 3: Setup Frontend

```bash
cd /home/vinay/Swaya.me/frontend

# Install Node.js if not available
# sudo apt install -y nodejs npm

# Install dependencies
npm install

# Start development server
npm run dev
```

**Frontend will run at:** http://localhost:5173

---

## Testing the Application

### Access Points

1. **Frontend UI:** http://localhost:5173
2. **API Documentation:** http://localhost:8000/api/docs
3. **API Root:** http://localhost:8000/api/v1

### Demo Credentials

```
Email: demo@swaya.me
Password: Demo1234
Tenant: Demo Organization
Tier: Pro
```

---

## UI Test Scenarios

### Scenario 1: User Registration & Login

1. Open http://localhost:5173
2. Click "Register now"
3. Fill in:
   - Organization Name: "My Test Org"
   - Email: "test@example.com"
   - Password: "Test1234"
4. Click Register
5. You should be redirected to Dashboard

### Scenario 2: Login with Demo Account

1. Open http://localhost:5173/login
2. Enter demo credentials:
   - Email: demo@swaya.me
   - Password: Demo1234
3. Click Login
4. Dashboard should load with existing quizzes (if any)

### Scenario 3: Quiz Management (Using API Docs)

Since the frontend quiz builder is a placeholder, test with API docs:

1. Open http://localhost:8000/api/docs
2. Click "Authorize" and enter your JWT token
3. Test endpoints:
   - POST /api/v1/quizzes - Create quiz
   - POST /api/v1/quizzes/{id}/questions - Add questions
   - POST /api/v1/quizzes/{id}/publish - Publish quiz
   - POST /api/v1/quizzes/sessions/start - Start session

### Scenario 4: Audience Join

1. Start a session (get join code from API)
2. Open http://localhost:5173/join
3. Enter the 6-digit join code
4. Enter a display name
5. Click "Join Quiz"

---

## Expected Behavior

### ✅ What Should Work

1. **Authentication**
   - Registration creates user + tenant
   - Login returns JWT token
   - Token stored in localStorage
   - Protected routes redirect to login

2. **Dashboard**
   - Shows list of quizzes
   - Displays quiz status (draft/ready)
   - Shows question count
   - Has "Create Quiz" button

3. **Join Screen**
   - Accepts 6-character code
   - Validates input
   - Joins session successfully

### 🚧 What's Not Yet Implemented (Frontend)

1. **Quiz Builder UI** - Placeholder (use API docs instead)
2. **Host Control Panel** - Placeholder
3. **Audience Session Screen** - Placeholder
4. **Real-time Updates** - Not yet implemented

---

## Troubleshooting

### Backend Won't Start

```bash
# Check MySQL is running
docker ps | grep mysql

# Check Redis is running
docker ps | grep redis

# View backend logs
cd /home/vinay/Swaya.me/backend
tail -f logs/app.log

# Test database connection
docker exec -it swaya-dev-mysql mysql -u root -plocalpass -e "SELECT 1;"
```

### Frontend Won't Start

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check port availability
lsof -i :5173
```

### Can't Connect to Services

```bash
# Restart all services
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d mysql redis

# Check network
docker network ls
docker network inspect swaya-dev-network
```

---

## API Testing with Postman/Thunder Client

### 1. Register User

```http
POST http://localhost:8000/api/v1/auth/register
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "Test1234",
  "tenant_name": "Test Org",
  "full_name": "Test User"
}
```

### 2. Login

```http
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "Test1234"
}
```

Copy the `access_token` from response.

### 3. Create Quiz

```http
POST http://localhost:8000/api/v1/quizzes
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "title": "JavaScript Basics",
  "description": "Test your JS knowledge",
  "event_id": 1
}
```

### 4. Add Question

```http
POST http://localhost:8000/api/v1/quizzes/1/questions
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "text": "What is 2 + 2?",
  "options": ["3", "4", "5", "6"],
  "correct_answer_index": 1
}
```

### 5. Publish Quiz

```http
POST http://localhost:8000/api/v1/quizzes/1/publish
Authorization: Bearer {your_token}
```

### 6. Start Session

```http
POST http://localhost:8000/api/v1/quizzes/sessions/start?quiz_id=1
Authorization: Bearer {your_token}
```

Response will include `join_code` for audience.

---

## Next Steps After Testing

1. **Report Issues**: Document any bugs or unexpected behavior
2. **Complete Frontend**: Implement quiz builder UI
3. **Add WebSocket**: For real-time updates
4. **Write Tests**: Unit and integration tests
5. **Deploy**: To production environment

---

## Support

- **API Documentation:** http://localhost:8000/api/docs
- **Full Deployment Guide:** DEPLOYMENT.md
- **API Reference:** API_REFERENCE.md
- **Implementation Details:** IMPLEMENTATION_COMPLETE.md

---

**Ready to Test!** 🚀

Start with the demo account (demo@swaya.me / Demo1234) and use the API docs for full functionality testing.
