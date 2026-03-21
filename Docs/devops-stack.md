# DevOps & Infrastructure Stack

## Overview
This document describes the DevOps, infrastructure, and deployment technologies used for Swaya.me.

**All technologies are 100% open source and free**, with the exception of Oracle Cloud Infrastructure (OCI) used for cost-effective cloud hosting. The application remains fully portable to any Linux environment.

---

## Infrastructure Hosting

| Component | Provider | License/Cost | Configuration | Purpose |
|---|---|---|---|---|
| **Compute Instance** | Oracle Cloud Infrastructure (OCI) Free Tier | Free Tier (Proprietary) | AMD-based VM, Ubuntu 24.04 LTS | Hosts all application services and databases |
| **Operating System** | Ubuntu | Free (Open Source) | 24.04 LTS | Base Linux distribution |
| **Region** | OCI | Free Tier | ap-south-1 (or equivalent) | Primary deployment region |
| **Instance Type** | OCI | Free Tier | Ampere A1 (ARM) or AMD-based free tier | Cost-effective for MVP |

---

## Source Code Management

| Component | Tool | License | Configuration | Purpose |
|---|---|---|---|---|
| **Git Server** | Gitea | MIT (Open Source) | Self-hosted on separate OCI free tier instance (AMD, Ubuntu 24.04) | Centralized source code repository |
| **Repository Access** | SSH/HTTPS | Open Standards | Configured for team collaboration | Version control and CI/CD integration point |

---

## Deployment & Containerization

| Component | Technology | License | Usage |
|---|---|---|---|
| **Container Runtime** | Docker | Apache 2.0 (Open Source) | Package application and dependencies consistently across environments |
| **Container Orchestration** | Docker Compose | Apache 2.0 (Open Source) | Manage multi-container deployments on single VM |
| **Reverse Proxy** | Nginx | BSD 2-Clause (Open Source) | Route traffic to frontend and backend services |

---

## Database Hosting

| Component | Provider | License | Configuration | Purpose |
|---|---|---|---|---|
| **MySQL** | OCI VM (local) | GPL v2 (Open Source) | MySQL 8.0+ instance on same OCI VM | Persistent relational data storage |
| **Redis** | OCI VM (local) | BSD 3-Clause (Open Source) | In-memory cache service on same OCI instance | Session storage, real-time counters, rate limiting |

---

## Rationale

- **100% Open Source Stack:** All software components are open source, ensuring transparency, community support, and zero licensing costs
- **OCI Free Tier + Self-hosted Gitea:** Minimizes cloud costs while maintaining full control over source code
- **Self-hosted deployment:** Avoids vendor lock-in and supports MVP rapid iteration
- **Single VM strategy:** Simplifies infrastructure management for MVP phase
- **Separation of concerns:** Gitea on separate instance reduces attack surface and ensures git availability
- **Docker:** Enables consistent local development and reproducible deployments
- **Portability:** Application can run on any Linux environment (AWS, GCP, Azure, DigitalOcean, or on-premises)

---

## Future Scaling Considerations (All Open Source)

- **Kubernetes (Apache 2.0):** Migration for higher availability and auto-scaling
- **MinIO (AGPL v3):** S3-compatible object storage for quiz media and artifacts
- **Varnish or Nginx (BSD):** CDN/caching for frontend static assets
- **Drone CI (Apache 2.0) or Jenkins (MIT):** Self-hosted CI/CD pipeline
- **Prometheus (Apache 2.0) + Grafana (AGPL v3):** Monitoring and metrics
- **ELK Stack (Elastic License 2.0) or Loki (AGPL v3):** Centralized logging
- **Traefik (MIT) or HAProxy (GPL):** Advanced load balancing and routing
