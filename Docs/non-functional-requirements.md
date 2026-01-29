# Non-Functional Requirements (NFRs)

## Overview

This document defines the non-functional requirements for the Interactive Audience Engagement Platform MVP, specifically the Quiz feature. These requirements are scoped for the initial pilot deployment on OCI Free Tier infrastructure.

**Technology Commitment:** All software components are 100% open source and free (GPL, MIT, Apache, BSD, or similar permissive licenses). This ensures:
- Zero licensing costs at any scale
- Full transparency and auditability
- No vendor lock-in
- Community-driven improvements
- Portability across cloud providers and on-premises infrastructure

**Exception:** Oracle Cloud Infrastructure (OCI) is used for cost-effective hosting (generous free tier), but the application stack remains fully portable to any Linux environment (AWS, GCP, Azure, DigitalOcean, bare metal, etc.).

---

## Infrastructure Constraints

### Pilot & Development Environment
- **Platform**: Oracle Cloud Infrastructure (OCI) Free Tier
- **Instance Type**: Ampere ARM-based compute (aarch64)
- **Resources**: 4 OCPU, 24 GB RAM (23.98 GiB available)
- **Storage**: 97 GB SSD (11 GB used, 86 GB available)
- **Deployment**: Single VM (modular monolith)
- **Purpose**: Pilot testing AND active development environment

### Baseline System Metrics (Idle)
- **CPU Load**: 0.00 (4 cores idle)
- **Memory Usage**: 2.4 GB used (~10%), 20 GB available (~87%)
- **Swap**: Disabled (0 GB)
- **Disk Usage**: 12% utilized (11 GB / 97 GB)
- **System Uptime**: 9+ days stable operation
- **OS**: Ubuntu 22.04.1 LTS (6.8.0-1041-oracle kernel)

**Impact**: Requirements must accommodate both development workloads (IDE, databases, build tools) and production quiz sessions running simultaneously.

---

## 1. Performance Requirements

### 1.1 Response Time
- **API Response Time**: 95th percentile < 500ms for read operations
- **API Response Time**: 95th percentile < 1s for write operations
- **Real-time Message Latency**: < 2s from host action to audience notification
- **Quiz Result Aggregation**: Results displayed within 2s of question close

### 1.2 Throughput
- **Concurrent Quiz Sessions**: Support 5 simultaneous live quiz sessions
- **Concurrent Users per Session**: Support up to 200 participants per quiz session
- **Total Concurrent Users**: 500-1000 active connections system-wide
- **Message Throughput**: Handle 100 messages/second for real-time updates

### 1.3 Resource Utilization
- **CPU Usage**: Average < 40% under quiz load, peak < 70% (development tools consume ~20%)
- **Memory Usage**: < 16 GB under peak load (leaving 7 GB for development and OS)
- **Database Connections**: Pool size optimized for 4 OCPU (max 20-30 connections)
- **Network Bandwidth**: < 100 Mbps sustained
- **Development Headroom**: System must support concurrent VS Code, Docker daemon, MySQL, Redis during development

---

## 2. Scalability Requirements

### 2.1 Horizontal Scalability (Post-MVP)
- Architecture must support migration from single-VM to multi-instance deployment
- State management (Redis) must be externally accessible for future distributed setup
- Database must support read replicas and connection pooling

### 2.2 Vertical Scalability
- Application must efficiently utilize ARM architecture and multi-core processing
- Memory footprint must be optimized to run within 24 GB constraint
- No hard-coded limits that prevent running on larger instances

### 2.3 Data Growth (Pilot MVP Phase)
**For single VM pilot on OCI Free Tier:**
- 100 quiz definitions (testing/demonstration)
- 1,000 quiz sessions per month
- 50,000 participant responses per month
- 6-month data retention without performance degradation

**Post-MVP: Tiered SaaS Model (Free/Paid tiers)**
Scalability requirements shift significantly for multi-tenant SaaS:

**Free Tier (per user):**
- Up to 5 quiz definitions
- Up to 50 quiz sessions/month
- Up to 500 participant responses/month
- Data retention: 3 months

**Paid Tier (per user, baseline):**
- Up to 100 quiz definitions
- Unlimited quiz sessions
- Unlimited participant responses
- Data retention: 12 months

**System-wide aggregates (SaaS at scale):**
- 10,000+ quiz definitions across all users
- 100,000+ quiz sessions per month
- 5,000,000+ participant responses per month
- Database size: 50+ GB (with efficient indexing)
- Performance must degrade gracefully, not linearly with user count

---

## 3. Availability & Reliability

### 3.1 Uptime
- **Target Availability**: 99% uptime during pilot phase (allows ~7 hours downtime/month)
- **Development Impact**: Downtime expected during code deployments, database migrations, and dependency updates
- **Planned Maintenance Window**: Weekly maintenance window acceptable
- **Recovery Time Objective (RTO)**: < 15 minutes for system restart
- **Graceful Shutdown**: Zero-downtime deployment for non-breaking changes

### 3.2 Data Durability
- **MySQL Persistence**: Daily automated backups with 7-day retention
- **Redis Durability**: AOF persistence enabled for session state
- **Data Loss**: Recovery Point Objective (RPO) < 24 hours

### 3.3 Error Handling
- Graceful degradation when Redis is unavailable (serve from database with degraded performance)
- Clear error messages for users when services are unavailable
- Automatic reconnection for WebSocket/SSE connections

---

## 4. Security Requirements

### 4.1 Authentication & Authorization
- **Authentication**: JWT-based authentication with secure token generation
- **Token Expiry**: Access tokens expire within 1 hour, refresh tokens within 7 days
- **Authorization**: Role-based access control (Host vs. Participant)
- **Password Security**: Bcrypt or Argon2 hashing with minimum 10 rounds

### 4.2 Data Protection
- **Transport Security**: All HTTP traffic over HTTPS (TLS 1.2+)
- **WebSocket Security**: WSS (WebSocket Secure) for real-time connections
- **Database Access**: No direct external access; application-only access via localhost
- **Secrets Management**: Environment variables for credentials, no hardcoded secrets

### 4.3 Input Validation
- Server-side validation for all user inputs
- Protection against SQL injection (via ORM parameterized queries)
- Protection against XSS attacks (input sanitization)
- Rate limiting on API endpoints (100 requests/minute per user)

---

## 5. Usability Requirements

### 5.1 User Experience
- **First-Time Host**: Able to create and launch a quiz within 5 minutes
- **Participant Join**: Join a quiz within 30 seconds using a simple code
- **Mobile Responsiveness**: Functional on mobile devices (iOS Safari, Android Chrome)
- **Browser Compatibility**: Support latest 2 versions of Chrome, Firefox, Safari, Edge

### 5.2 Accessibility
- Semantic HTML for screen reader compatibility
- Keyboard navigation support for critical workflows
- Color contrast ratio meeting WCAG 2.1 Level AA standards

---

## 6. Maintainability & Supportability

### 6.1 Code Quality
- **Test Coverage**: Minimum 70% code coverage for backend business logic
- **Linting**: Code passes ESLint (frontend) and flake8/pylint (backend)
- **Type Safety**: TypeScript for frontend, Python type hints for backend
- **Documentation**: All public APIs documented with OpenAPI/Swagger

### 6.2 Monitoring & Observability
- **Application Logs**: Structured JSON logs with appropriate levels (INFO, WARN, ERROR)
- **Health Checks**: `/health` endpoint for liveness and readiness probes
- **Metrics**: Basic metrics collection (request count, response time, error rate)
- **Resource Monitoring**: CPU, memory, disk usage tracked

### 6.3 Deployment
- **Containerization**: Docker images for all components
- **Deployment Time**: Full deployment (including database migrations) < 5 minutes
- **Rollback Capability**: Ability to rollback to previous version within 5 minutes
- **Configuration Management**: Environment-based configuration (dev, staging, prod)

---

## 7. Compatibility Requirements

### 7.1 Platform Compatibility
- **OS**: Linux (Ubuntu 22.04 LTS or similar)
- **Architecture**: ARM64 (Ampere) compatibility for all dependencies
- **Python Version**: Python 3.11+
- **Node.js Version**: Node.js 20 LTS

### 7.2 Database Compatibility
- **MySQL**: Version 8.0+
- **Redis**: Version 7.0+

### 7.3 Browser Compatibility
- Chrome/Edge 120+
- Firefox 120+
- Safari 17+
- Mobile browsers (iOS Safari 16+, Chrome Android 120+)

---

## 8. Extensibility Requirements

### 8.1 Architectural Flexibility
- **Modular Design**: Core modules (auth, quiz, real-time) independently testable
- **Feature Flags**: Support for feature toggles to enable/disable functionality
- **Plugin Architecture**: Quiz feature isolated for future feature additions (polls, surveys)

### 8.2 API Versioning
- REST API versioned (e.g., `/api/v1/`)
- Backward compatibility maintained for at least one major version

### 8.3 Database Schema Evolution
- **Migrations**: Alembic migrations for schema changes
- **Backward Compatibility**: Schema changes must not break existing data
- **Data Migration**: Support for data transformations during schema updates

---

## 9. Localization & Internationalization

### 9.1 MVP Phase
- **Language**: English only for MVP
- **Time Zone**: UTC for all stored timestamps
- **Date Format**: ISO 8601 format

### 9.2 Post-MVP Readiness
- UI strings externalized for future translation
- Database schema supports UTF-8 character sets
- Frontend framework supports i18n libraries (react-i18next)

---

## 10. Business Model & Multi-Tenancy Requirements

### 10.1 Tiered SaaS Model (Post-MVP)
- **Free Tier**: Limited quiz capacity, basic features
- **Paid Tier**: Higher limits, advanced features, priority support
- **Tenant Isolation**: Complete data isolation between user accounts
- **Billing Integration**: Ready for payment processing (Stripe, etc.)
- **Usage Tracking**: Accurate per-user quota monitoring for enforcement
- **Upgrade Path**: Seamless upgrade from free to paid without data loss

### 10.2 Multi-Tenancy Constraints
- **Data Isolation**: Row-level security ensures one user cannot access another's data
- **Resource Quotas**: Per-user resource limits enforced at application layer
- **Concurrent User Limits**: Single VM pilot supports 5-10 concurrent free/paid users
- **Noisy Neighbor Prevention**: Heavy users cannot degrade service for others (rate limiting, CPU throttling)

### 10.3 Analytics & Observability for Multi-Tenant
- Per-user usage metrics (quiz count, session count, response count)
- Feature usage tracking for product decisions
- Performance monitoring by tier to ensure quality
- SLA monitoring per paid tier customer

---

## 11. Development Environment Requirements

### 11.1 Server Management & Configuration
- **Aapanel**: Web-based server management UI for simplified server configuration
  - **Status**: Installed but compatibility issues with Ubuntu 22.04 LTS (not fully functional)
  - **Memory Footprint**: ~200-300 MB when running
  - **Port**: Typically 7888 (web console)
  - **Note**: Use for reference/documentation only; direct configuration via SSH recommended for reliability

### 11.2 Local Development Tools
- **IDE**: VS Code with extensions (typically ~500-700 MB RAM)
- **Version Control**: Git for source control
- **Package Managers**: npm (Node.js), pip (Python)
- **Docker**: Local Docker daemon for containerized services

### 11.3 Development Database & Cache
- **MySQL**: Development instance (500 MB-1 GB)
- **Redis**: Development instance for testing real-time features (100-200 MB)
- **Test Database**: Separate test database for automated tests (500 MB)

### 11.4 Build & Watch Tools
- **Node.js Build Tools**: webpack, vite, or similar (300-500 MB)
- **Python Virtual Environments**: Multiple venvs for different services (500 MB-1 GB)
- **Hot Module Reloading (HMR)**: Frontend development server active during coding

### 11.5 Resource Sharing Strategy
- Development and production services run on same VM for cost efficiency
- Database connections properly isolated between dev and production datasets
- Redis instances kept separate (different ports) for dev and production
- Memory overcommit acceptable during development-only periods
- Production quiz operations prioritized; development tools may be throttled during active quizzes
- Aapanel UI (if running) deprioritized when production load detected

---

## 12. Compliance & Legal

### 12.1 Data Privacy
- No collection of personally identifiable information (PII) beyond email and name
- Clear privacy policy displayed during registration
- User data deletion capability (right to be forgotten)

### 12.2 Data Retention
- User accounts: Retained indefinitely unless user requests deletion
- Quiz sessions: Archived after 6 months
- Access logs: Retained for 90 days

---

## 13. Pilot-Specific Success Criteria

### 11.1 Performance Benchmarks (OCI Free Tier)
- Successfully run 3 concurrent quiz sessions with 150 participants each
- Maintain < 3s response time for quiz interactions under load
- Zero data loss during normal operation
- System restart in < 10 minutes

### 11.2 User Experience Benchmarks
- 90% of hosts successfully create and run a quiz without support
- 95% of participants successfully join and complete a quiz
- < 5% error rate for quiz submission

### 11.3 Operational Benchmarks
- Deployment succeeds on first attempt 90% of the time
- Critical bugs resolved within 48 hours
- System monitoring provides visibility into all key metrics

---

## 14. Development Environment Benchmarks

### 12.1 Development & Test Success Criteria
- Build time: < 2 minutes for full rebuild (backend + frontend)
- Hot reload time: < 3 seconds for code changes
- Test suite execution: < 5 minutes for full test run
- Database migration time: < 30 seconds
- Docker image build: < 5 minutes (with caching)

### 12.2 Concurrent Development & Production
- Development IDE and tools consume ≤ 1 GB memory
- Background development processes consume ≤ 2 GB memory
- Active quiz sessions have priority scheduling
- Memory reclamation from caches when production load increases

---

## 15. Known Limitations & Trade-offs

### 13.1 Pilot Phase Limitations
- Single point of failure (single VM deployment)
- No geographic redundancy or CDN
- Limited to 1000 concurrent users system-wide
- No SLA guarantees during pilot
- Development and production workloads on same hardware

### 13.2 Development Environment Limitations
- No container orchestration (Docker Compose only, no Kubernetes)
- Single database instance shared with development (separate schemas)
- No persistent log aggregation (local files only)
- No distributed tracing or advanced APM during development
- **Aapanel Compatibility**: Aapanel (server management UI) has known issues with Ubuntu 22.04 LTS and is not fully functional; use CLI/SSH for server configuration

### 13.3 Accepted Trade-offs
- **High Availability vs. Cost**: Single VM acceptable for pilot, no HA setup
- **Performance vs. Complexity**: Simpler architecture prioritized over maximum performance
- **Feature Completeness vs. Time**: MVP features only, advanced features deferred
- **Isolation vs. Cost**: Shared VM for dev+prod acceptable for pilot phase
- **Resource Utilization vs. Development Comfort**: Accept slower builds during active quiz sessions

---

## 16. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-27 | System | Initial NFR document created |
| 1.1 | 2026-01-27 | System | Updated for development environment; baseline metrics added (0.00 load, 20GB available) |
| 1.2 | 2026-01-27 | System | Added free/paid tiered SaaS model requirements; updated data growth projections for multi-tenancy |

---

## Next Steps

1. **Performance Testing**: Establish baseline performance metrics on OCI Ampere instance with concurrent development tools running
2. **Load Testing**: Validate concurrent user and session limits with build tools active
3. **Memory Profiling**: Profile production quiz services to optimize memory under development workload
4. **Monitoring Setup**: Implement basic monitoring and alerting with development environment separation
5. **Documentation**: Create operational runbook for pilot deployment and development workflow
6. **Container Strategy**: Define Docker resource limits to prevent development workloads from starving production services
