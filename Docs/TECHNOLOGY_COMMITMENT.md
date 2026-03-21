# Technology Commitment — 100% Open Source & Free

## Overview

**Swaya.me is built entirely on open source and free technologies.**

This document serves as a definitive reference for the technology philosophy and commitment that governs all architectural and implementation decisions.

---

## Core Principles

### 1. Zero Licensing Costs
- All software components are free to use with no licensing fees
- No per-user, per-seat, or usage-based charges
- No hidden costs or premium tiers for core functionality

### 2. Open Source Only
- All technologies use permissive open source licenses:
  - MIT License
  - Apache 2.0 License
  - BSD Licenses (2-Clause, 3-Clause)
  - GPL v2 (for MySQL)
  - Other OSI-approved licenses
- Source code availability for all dependencies
- No proprietary or closed-source components in the application stack

### 3. Vendor Neutrality
- No lock-in to proprietary platforms or services
- Application is fully portable across:
  - Cloud providers (AWS, GCP, Azure, DigitalOcean, etc.)
  - On-premises infrastructure
  - Hybrid environments
- Avoids vendor-specific APIs and services

### 4. Community-Driven
- All technologies have active open source communities
- Regular updates and security patches
- Long-term sustainability and support
- Transparent development processes

### 5. Production-Ready
- Battle-tested at scale by major organizations
- Proven reliability and performance characteristics
- Comprehensive documentation and ecosystem support
- Enterprise adoption track record

---

## Technology Stack Summary

### Backend Technologies

| Component | Technology | License | Purpose |
|-----------|-----------|---------|---------|
| **Application Framework** | FastAPI | MIT | Core backend runtime |
| **Data Validation** | Pydantic | MIT | Request/response schemas |
| **ORM** | SQLAlchemy 2.0 | MIT | Database abstraction layer |
| **Database Migrations** | Alembic | MIT | Schema version control |
| **Database** | MySQL 8.0+ | GPL v2 | Persistent data storage |
| **Cache** | Redis | BSD 3-Clause | In-memory state store |
| **JWT Authentication** | PyJWT | MIT | Token generation/validation |
| **Password Hashing** | bcrypt | Apache 2.0 | Secure password storage |
| **Python Runtime** | CPython 3.11+ | PSF License | Language runtime |

### Frontend Technologies

| Component | Technology | License | Purpose |
|-----------|-----------|---------|---------|
| **UI Framework** | React 18+ | MIT | Component-based UI |
| **UI Component Library** | Ant Design | MIT | Pre-built UI components |
| **State Management** | Redux Toolkit | MIT | Global application state |
| **Routing** | React Router v6 | MIT | Client-side navigation |
| **HTTP Client** | Axios | MIT | API communication |
| **Build Tool** | Vite or Create React App | MIT | Development and build |
| **JavaScript Runtime** | Node.js 18+ | MIT | Development environment |

### Infrastructure & DevOps

| Component | Technology | License | Purpose |
|-----------|-----------|---------|---------|
| **Operating System** | Ubuntu 24.04 LTS | Free & Open Source | Server OS |
| **Containerization** | Docker | Apache 2.0 | Application packaging |
| **Container Orchestration** | Docker Compose | Apache 2.0 | Multi-container management |
| **Reverse Proxy** | Nginx | BSD 2-Clause | HTTP routing and SSL termination |
| **Version Control** | Git | GPL v2 | Source code management |
| **Git Server** | Gitea | MIT | Self-hosted repository |

### Cloud Hosting Exception

| Component | Provider | Type | Rationale |
|-----------|----------|------|-----------|
| **Compute & Hosting** | Oracle Cloud Infrastructure (OCI) | Proprietary Cloud (Free Tier) | Cost-effective hosting with generous free tier |

**Note:** While OCI is proprietary, the application is **fully portable** and can run on any Linux environment. OCI is used purely for hosting, not as a dependency in the application architecture.

---

## What We Explicitly Avoid

### Proprietary Technologies ❌
- Proprietary databases (Oracle Database, Microsoft SQL Server)
- Proprietary application servers
- Closed-source frameworks or libraries
- Commercial licenses requiring payment

### Vendor Lock-In ❌
- AWS-specific services (Lambda, DynamoDB, Cognito, etc.)
- GCP-specific services (Cloud Functions, Firestore, etc.)
- Azure-specific services (Azure Functions, Cosmos DB, etc.)
- Platform-as-a-Service (PaaS) offerings that create dependencies

### Paid/Freemium Services ❌
- SaaS services with usage-based billing
- "Free tier" services that require payment at scale
- Third-party APIs with licensing costs
- Commercial monitoring or analytics platforms

### Enterprise "Open Core" Products ❌
- Products with paid enterprise features
- Open source projects with proprietary extensions
- Community editions with feature limitations

---

## Future Scaling Considerations

As the platform scales, all additional technologies must adhere to the same principles:

### Candidate Technologies (All Open Source)

**Container Orchestration:**
- Kubernetes (Apache 2.0)
- K3s (Apache 2.0) - lightweight Kubernetes

**CI/CD:**
- Jenkins (MIT)
- Drone CI (Apache 2.0)
- GitLab CI (MIT) - if using self-hosted GitLab

**Monitoring & Observability:**
- Prometheus (Apache 2.0)
- Grafana (AGPL v3)
- Loki (AGPL v3) - log aggregation
- Jaeger (Apache 2.0) - distributed tracing

**Storage:**
- MinIO (AGPL v3) - S3-compatible object storage
- Ceph (LGPL) - distributed storage

**Load Balancing:**
- HAProxy (GPL)
- Traefik (MIT)

**Message Queues (if needed):**
- RabbitMQ (MPL 2.0)
- Apache Kafka (Apache 2.0)
- Redis Streams (BSD 3-Clause)

**Search (if needed):**
- Elasticsearch (Elastic License 2.0 or SSPL)
- OpenSearch (Apache 2.0) - Elasticsearch fork
- Meilisearch (MIT)

---

## Benefits of This Approach

### For Development
- **Transparency:** Full visibility into all dependencies
- **Flexibility:** Freedom to modify and extend as needed
- **Community Support:** Large ecosystems and communities
- **Best Practices:** Well-documented patterns and examples

### For Operations
- **Cost Predictability:** No surprise licensing fees
- **Operational Freedom:** Deploy anywhere without restrictions
- **Longevity:** No risk of vendor discontinuation
- **Compliance:** Easier to audit and certify

### For Business
- **Zero Software Licensing Costs:** Eliminates a major cost category
- **Competitive Advantage:** More resources for features vs licenses
- **Market Flexibility:** Can offer competitive pricing
- **Strategic Independence:** Not dependent on vendor decisions

### For Users
- **Trust:** Transparent, auditable technology stack
- **Reliability:** Battle-tested, widely adopted technologies
- **Performance:** Industry-standard tools optimized over years
- **Security:** Community-reviewed, frequently patched

---

## Compliance & License Management

### License Compatibility
All chosen licenses are compatible with each other and with commercial use:
- MIT, Apache 2.0, BSD: Highly permissive, minimal restrictions
- GPL v2 (MySQL): Copyleft, but acceptable for server-side use
- AGPL v3 (future Grafana, MinIO): Strong copyleft, acceptable for self-hosted services

### Attribution Requirements
- All license files preserved in repositories
- Third-party notices included in distributions
- Copyright notices maintained

### No Viral Licensing Concerns
- Application code is not GPL-licensed (FastAPI is MIT)
- MySQL's GPL applies to the database server, not application code
- AGPL components (if used) are self-contained services

---

## Technology Decision Checklist

When evaluating any new technology or dependency:

- [ ] Is it open source with an OSI-approved license?
- [ ] Is it free to use at any scale with no usage-based fees?
- [ ] Does it have an active community and regular updates?
- [ ] Is it production-ready and battle-tested?
- [ ] Does it avoid vendor lock-in?
- [ ] Is it compatible with our existing license model?
- [ ] Can it run on any Linux environment (portability)?
- [ ] Does it have comprehensive documentation?

If all answers are "Yes," the technology is acceptable.

---

## Enforcement

This technology commitment is:
- **Non-negotiable** for MVP and V1
- **Documented** in all architectural specifications
- **Enforced** during code review
- **Reviewed** for all new dependencies
- **Auditable** through dependency manifests

Any exceptions require:
1. Documented justification
2. Architectural review
3. Explicit approval from technical leadership

---

## Conclusion

**Swaya.me's commitment to 100% open source and free technologies is foundational.**

This approach ensures:
- Sustainable long-term development
- Operational flexibility and portability
- Cost-effective scaling
- Community trust and transparency
- Strategic independence

This is not just a technical decision—it's a core business principle.

---

**Last Updated:** January 28, 2026  
**Maintained By:** Architecture Team  
**Review Frequency:** Quarterly or when evaluating new technologies
