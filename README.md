# Swaya.me - Interactive Quiz Platform

A Slido-like interactive quiz platform built with 100% open source technologies. Designed as a modular monolith with multi-tenant SaaS architecture.

## Features (MVP)

- **Quiz Builder**: Create quizzes with MCQ questions (4 options each)
- **Live Sessions**: Host-controlled quiz sessions with real-time audience participation
- **Anonymous Join**: Audience joins via code/link without login
- **Real-time Results**: Live answer aggregation and results display
- **Multi-Tenant**: Tier-based subscription model (Free, Pro, Enterprise)

## Technology Stack (100% Open Source)

### Backend
- **FastAPI** (MIT) - Web framework
- **SQLAlchemy 2.0** (MIT) - ORM
- **MySQL 8.0** (GPL v2) - Database
- **Redis 7** (BSD) - Caching and live state
- **Alembic** (MIT) - Database migrations
- **PyJWT** (MIT) - Authentication

### Frontend
- **React** (MIT) - UI framework
- **Ant Design** (MIT) - Component library
- **Redux Toolkit** (MIT) - State management
- **Vite** (MIT) - Build tool

### Infrastructure
- **Docker** (Apache 2.0) - Containerization
- **Docker Compose** (Apache 2.0) - Orchestration
- **Nginx** (BSD) - Reverse proxy

## Architecture

3-layer modular monolith:

1. **Core Layer**: Authentication, tenant management, configuration
2. **Broker Layer**: API gateway, policy enforcement, rate limiting
3. **Features Layer**: Quiz business logic

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Local Development Setup

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd swaya.me
   ```

2. **Start services (MySQL + Redis)**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d mysql redis
   ```

3. **Backend setup**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your configuration
   
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # OR: .venv\Scripts\activate  # Windows
   
   pip install -r requirements.txt -r requirements-dev.txt
   
   # Run migrations
   alembic upgrade head
   
   # Start backend server
   uvicorn main:app --reload
   ```

4. **Frontend setup** (coming soon)
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access application**
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs
   - Frontend: http://localhost:5173

## Project Structure

```
swaya.me/
├── backend/
│   ├── core/           # Platform foundation
│   ├── broker/         # API gateway & policies
│   ├── features/       # Business logic (Quiz)
│   ├── persistence/    # Database models & migrations
│   └── shared/         # Utilities
├── frontend/
│   └── src/
│       ├── features/   # Feature-specific components
│       ├── shared/     # Reusable components
│       └── store/      # Redux slices
├── specs/              # Complete specifications
├── Docs/               # Architecture documentation
└── docker-compose.dev.yml
```

## Development Workflow

1. **Database Migrations**
   ```bash
   # Create migration
   alembic revision --autogenerate -m "description"
   
   # Apply migrations
   alembic upgrade head
   
   # Rollback
   alembic downgrade -1
   ```

2. **Code Quality**
   ```bash
   # Format code
   black .
   isort .
   
   # Linting
   flake8 .
   mypy .
   ```

3. **Testing**
   ```bash
   pytest
   pytest --cov=. --cov-report=html
   ```

## Documentation

- [Specifications](/specs/) - Complete MVP specifications
- [Architecture](/Docs/logical_architecture.md) - 3-layer architecture
- [API Contracts](/specs/backend/api-contracts.md) - REST API endpoints
- [Data Model](/specs/backend/domain-model.md) - Database schema
- [Development Plan](/Plan.md) - Implementation roadmap

## License

MIT License - see LICENSE file for details

## Contributing

This is a planning/development project. Contributions welcome following the architectural guidelines in `/Docs/`.
