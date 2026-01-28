# DevOps & Infrastructure Stack

## Overview
This document describes the DevOps, infrastructure, and deployment technologies used for Swaya.me.

---

## Infrastructure Hosting

| Component | Provider | Configuration | Purpose |
|---|---|---|---|
| **Compute Instance** | Oracle Cloud Infrastructure (OCI) Free Tier | AMD-based VM, Ubuntu 24.04 LTS | Hosts all application services and databases |
| **Region** | OCI | ap-south-1 (or equivalent) | Primary deployment region |
| **Instance Type** | OCI | Ampere A1 (ARM) or AMD-based free tier | Cost-effective for MVP |

---

## Source Code Management

| Component | Tool | Configuration | Purpose |
|---|---|---|---|
| **Git Server** | Gitea | Self-hosted on separate OCI free tier instance (AMD, Ubuntu 24.04) | Centralized source code repository |
| **Repository Access** | SSH/HTTPS | Configured for team collaboration | Version control and CI/CD integration point |

---

## Deployment & Containerization

| Component | Technology | Usage |
|---|---|---|
| **Container Runtime** | Docker | Package application and dependencies consistently across environments |
| **Container Orchestration** | Docker Compose (Manual) | Manage multi-container deployments on single VM |
| **Reverse Proxy** | Nginx | Route traffic to frontend and backend services |

---

## Database Hosting

| Component | Provider | Configuration | Purpose |
|---|---|---|---|
| **MySQL** | OCI VM (local) | MySQL 8.0+ instance on same OCI VM | Persistent relational data storage |
| **Redis** | OCI VM (local) | In-memory cache service on same OCI instance | Session storage, real-time counters, rate limiting |

---

## Rationale

- **OCI Free Tier + Self-hosted Gitea:** Minimizes cloud costs while maintaining full control over source code
- **Self-hosted deployment:** Avoids vendor lock-in and supports MVP rapid iteration
- **Single VM strategy:** Simplifies infrastructure management for MVP phase
- **Separation of concerns:** Gitea on separate instance reduces attack surface and ensures git availability
- **Docker:** Enables consistent local development and reproducible deployments

---

## Future Scaling Considerations

- Kubernetes migration for higher availability and auto-scaling
- Separate storage service (S3-compatible) for quiz media and artifacts
- CDN for frontend static assets
- Dedicated CI/CD pipeline (GitHub Actions, GitLab CI, or self-hosted)
- Monitoring and logging infrastructure (Prometheus, ELK, etc.)
