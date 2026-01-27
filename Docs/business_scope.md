# 1. Business Scope Statement

## 1.1 Product Business Scope

The product is a **real-time audience interaction platform** designed to enable presenters, trainers, event organizers, and enterprises to **run interactive sessions at scale**.

The platform provides **live Q&A, polling, quizzes, surveys, moderation, and analytics** to transform one-way presentations into **two-way, measurable engagement** across **in-person, remote, and hybrid environments**.

The system acts as an **engagement layer** that integrates with existing presentation and conferencing workflows, without replacing them.

---

## 1.2 Business Objectives

1. Enable **real-time audience participation** with minimal friction.
2. Provide **structured interaction workflows** for Q&A and polling.
3. Deliver **high-performance and low-latency experience** at scale.
4. Ensure **enterprise-grade moderation, governance, and safety**.
5. Generate **actionable engagement insights and analytics**.
6. Support **future extensibility** for integrations and advanced features.

---

## 1.3 Business Scope

- Audience Q&A
- Live polling and quizzes
- Surveys and feedback capture
- Presenter mode (live display)
- Moderation and governance
- Analytics and exports
- Role-based access (Host, Moderator, Audience)
- Enterprise-grade scalability and performance

---

## 1.4 Product Scope Strategy

The product will aim for **full functional parity with Slido in the long term**.

Development will follow a **phased delivery model**, starting with a **high-quality MVP** that:
- Serves **one complete end-to-end user flow**
- Delivers **excellent performance and reliability**
- Is **architected for full parity expansion**

---

## 1.5 MVP Scope Philosophy

The MVP will:
- Solve **one core problem completely**.
- Serve **one primary user journey end-to-end**.
- Deliver **best-in-class UX, performance, and reliability**.
- Avoid partial or fragmented feature delivery.

The MVP will prioritize:
- Q&A
- MCQ polling
- Presenter mode
- Moderation
- Real-time performance

All architecture and data models must **support seamless expansion to full parity features** without rework.

---

## 1.6 Long-Term Scope 

The platform will evolve into a **full-featured enterprise-grade engagement system** supporting:
- Advanced poll types
- Quizzes and leaderboards
- Surveys and workflows
- Deep analytics
- Integrations with presentation and conferencing platforms
- Enterprise authentication and governance

---

# 2. User Roles & Responsibilities

| Role | Definition | Core Responsibility | In Scope | Out of Scope |
|------|------------|---------------------|----------|--------------|
| Host | Session owner | Run and control the session | Event setup, polls, presenter mode, settings | Content moderation only |
| Moderator / Co-Host | Content governor | Ensure safe and relevant audience content | Approve/hide questions, highlight content, moderation | Event setup, poll control, presenter mode |
| Audience | Participant | Engage in the session | Ask questions, vote, respond to polls | Any session or content control |

---

## 2.1 Core User Journey Supported per Phase

| Phase | User Journey |
|------|--------------|
| MVP | • **Host:** Login → Create Session → Dashboard → Launch Q&A / MCQ → Presenter Mode → End Session → View Results<br>• **Audience:** Join via Link/Code → (Optional Name) → Participate (Q&A / Poll) → View Live Updates<br>• **Moderator:** Dashboard → Review Content → Approve / Hide / Highlight |
| Release 1 (R1) | • **Host:** Create Session → Configure Multiple Interactions → Switch Live Interactions → View Leaderboards → Analytics<br>• **Audience:** Join → Participate (Polls / Quiz / Word Cloud) → View Results<br>• **Moderator:** Dashboard → Manage Multiple Queues → Support Live Session |
| Full Parity | • **Host:** Create / Reuse Template → Assign Moderators → Run Integrated Session → Export Analytics<br>• **Audience:** Join via Embedded / External Platform → Participate → Complete Surveys<br>• **Moderator:** Dashboard → Enforce Policies → Review Audit Logs |
