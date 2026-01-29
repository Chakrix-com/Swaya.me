# Technology Stack Reference — Open Source Technologies

## Quick Reference

This document provides a quick reference of all technologies used in Swaya.me with their licenses and purposes.

**Commitment:** 100% open source and free software with zero licensing costs.

---

## Backend Stack

```yaml
Framework:
  FastAPI:
    License: MIT
    Purpose: Web framework and API development
    
Data Layer:
  SQLAlchemy:
    License: MIT
    Version: 2.0+
    Purpose: ORM and database abstraction
  
  Alembic:
    License: MIT
    Purpose: Database migrations
  
  Pydantic:
    License: MIT
    Version: 2.0+
    Purpose: Data validation and serialization

Database:
  MySQL:
    License: GPL v2
    Version: 8.0+
    Purpose: Persistent relational storage
    
  Redis:
    License: BSD 3-Clause
    Version: 7+
    Purpose: In-memory cache and session storage

Authentication:
  PyJWT:
    License: MIT
    Purpose: JWT token generation and validation
    
  bcrypt:
    License: Apache 2.0
    Purpose: Password hashing

Rate Limiting & Policy Enforcement:
  Slowapi:
    License: MIT
    Version: 0.1.9+
    Purpose: Application-level rate limiting with Redis backend
    Note: Context-aware rate limiting (per-IP, per-participant, per-role)

Logging & Observability:
  python-json-logger:
    License: BSD 2-Clause
    Version: 2.0+
    Purpose: Structured JSON logging for API analytics and audit trails

Content Moderation (MVP):
  better-profanity:
    License: MIT
    Version: 0.7.0+
    Purpose: Profanity detection and filtering for user-generated content
    Scope: Questions, answers, display names, poll options
    
  bleach:
    License: Apache 2.0
    Version: 6.1.0+
    Purpose: HTML and text sanitization to prevent XSS attacks
    Scope: All user text input before storage

State Management (Features Layer):
  python-statemachine:
    License: MIT
    Version: 2.3.0+
    Purpose: Formal state machine for quiz session lifecycle
    Scope: Enforce valid state transitions (CREATED → ACTIVE → QUESTION_CLOSED → ENDED)

Testing:
  pytest:
    License: MIT
    Purpose: Unit and integration testing
    
  pytest-asyncio:
    License: Apache 2.0
    Version: 0.23.0+
    Purpose: Test async functions and FastAPI endpoints
    
  pytest-cov:
    License: MIT
    Purpose: Code coverage reporting (post-MVP)

Python Runtime:
  CPython:
    License: PSF License (Open Source)
    Version: 3.11+
    Purpose: Python interpreter
```

---

## Frontend Stack

```yaml
UI Framework:
  React:
    License: MIT
    Version: 18+
    Purpose: Component-based UI development
    
Component Library:
  Ant Design:
    License: MIT
    Version: 5+
    Purpose: Pre-built UI components

State Management:
  Redux Toolkit:
    License: MIT
    Purpose: Global application state

Routing:
  React Router:
    License: MIT
    Version: 6+
    Purpose: Client-side routing

HTTP Client:
  Axios:
    License: MIT
    Purpose: API communication

Form Management:
  React Hook Form:
    License: MIT
    Version: 7.50.0+
    Purpose: Performant form state management with validation
    Scope: Login form, quiz builder, all user input forms
    
  Yup:
    License: MIT
    Version: 1.3.0+
    Purpose: Schema-based validation for forms
    Integration: Works with React Hook Form for declarative validation

Icons:
  Font Awesome:
    License: MIT (Code) / CC BY 4.0 (Icons)
    Version: 6.5.0+ (Free version)
    Purpose: Consistent icon set across application
    Scope: UI actions, status indicators, navigation

Utilities:
  date-fns:
    License: MIT
    Version: 3.0.0+
    Purpose: Date formatting and manipulation
    Scope: Timestamp display, relative time ("2 minutes ago")

Build Tools:
  Vite:
    License: MIT
    Purpose: Fast development server and build tool
  
  Alternative - Create React App:
    License: MIT
    Purpose: React build toolchain

JavaScript Runtime:
  Node.js:
    License: MIT
    Version: 18+
    Purpose: Development environment and build process
```

---

## Infrastructure Stack

```yaml
Operating System:
  Ubuntu:
    License: Free & Open Source
    Version: 24.04 LTS
    Purpose: Server operating system

Containerization:
  Docker:
    License: Apache 2.0
    Version: 24.0+
    Purpose: Application containerization
    
  Docker Compose:
    License: Apache 2.0
    Version: 2.20+
    Purpose: Multi-container orchestration

Reverse Proxy:
  Nginx:
    License: BSD 2-Clause
    Version: 1.24+
    Purpose: HTTP routing, SSL termination, static file serving

Version Control:
  Git:
    License: GPL v2
    Version: 2.40+
    Purpose: Source code version control
    
  Gitea:
    License: MIT
    Purpose: Self-hosted Git server
```

---

## Development Tools

```yaml
IDE:
  VS Code:
    License: MIT
    Purpose: Code editor

Testing:
  pytest:
    License: MIT
    Purpose: Python unit testing
    
  Jest:
    License: MIT
    Purpose: JavaScript unit testing
    
  React Testing Library:
    License: MIT
    Purpose: React component testing

Code Quality:
  Black:
    License: MIT
    Purpose: Python code formatting
    
  Pylint / Flake8:
    License: GPL v2 / MIT
    Purpose: Python linting
    
  ESLint:
    License: MIT
    Purpose: JavaScript linting
    
  Prettier:
    License: MIT
    Purpose: JavaScript code formatting
```

---

## Future Additions (Post-MVP)

All future technologies must be open source and free:

```yaml
Container Orchestration:
  Kubernetes:
    License: Apache 2.0
    
  K3s:
    License: Apache 2.0
    Purpose: Lightweight Kubernetes

CI/CD:
  Jenkins:
    License: MIT
    
  Drone CI:
    License: Apache 2.0

Monitoring:
  Prometheus:
    License: Apache 2.0
    Purpose: Metrics collection
    
  Grafana:
    License: AGPL v3
    Purpose: Visualization dashboards
    
  Loki:
    License: AGPL v3
    Purpose: Log aggregation

Object Storage:
  MinIO:
    License: AGPL v3
    Purpose: S3-compatible object storage

Load Balancing:
  HAProxy:
    License: GPL
    
  Traefik:
    License: MIT

Message Queue:
  RabbitMQ:
    License: MPL 2.0
    
  Apache Kafka:
    License: Apache 2.0

Search:
  OpenSearch:
    License: Apache 2.0
    Purpose: Full-text search
    
  Meilisearch:
    License: MIT
    Purpose: Fast search API
```

---

## Cloud Hosting

```yaml
Primary:
  Oracle Cloud Infrastructure (OCI):
    Type: Proprietary Cloud Platform
    Tier: Free Tier
    Purpose: Cost-effective cloud hosting
    Note: Application is fully portable to any Linux environment

Alternative Deployment Targets:
  - AWS EC2 (self-managed Linux instances)
  - Google Compute Engine (self-managed)
  - Azure Virtual Machines (self-managed)
  - DigitalOcean Droplets
  - Linode
  - Bare metal servers
  - On-premises infrastructure
```

---

## License Categories

### Highly Permissive (Minimal Restrictions)
- **MIT License**: FastAPI, Pydantic, React, Redux, Ant Design, most tools
- **Apache 2.0**: Docker, bcrypt, Kubernetes (future)
- **BSD 2-Clause/3-Clause**: Nginx, Redis

### Copyleft (Source Distribution Required)
- **GPL v2**: MySQL, Git
- **AGPL v3**: Grafana, MinIO (future), Loki (future)

### Other Open Source
- **PSF License**: Python
- **MPL 2.0**: RabbitMQ (future)

All licenses are OSI-approved and compatible with commercial use.

---

## Key Advantages

1. **Zero Licensing Costs**: No per-user or usage-based fees
2. **Full Portability**: Deploy anywhere without vendor restrictions
3. **Transparency**: All source code is auditable
4. **Community Support**: Large, active communities for all technologies
5. **Flexibility**: Freedom to modify and extend as needed
6. **Longevity**: No vendor discontinuation risk
7. **Compliance**: Easier auditing and certification

---

## Technology Evaluation Criteria

Before adding any new dependency, verify:

✅ Open source with OSI-approved license  
✅ Free to use at any scale  
✅ Active community and regular updates  
✅ Production-ready and battle-tested  
✅ No vendor lock-in  
✅ Compatible with existing stack  
✅ Portable across environments  
✅ Well-documented  

---

## See Also

- [Full Technology Commitment Document](/Docs/TECHNOLOGY_COMMITMENT.md)
- [Technology Stack Details](/Docs/Technology_Stack_Final.md)
- [DevOps Stack](/Docs/devops-stack.md)
- [Development Environment Setup](/specs/runtime/dev-env.md)

---

**Maintained By:** Architecture Team  
**Last Updated:** January 28, 2026
