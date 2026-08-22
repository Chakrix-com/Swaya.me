# Security Policy

Swaya.me takes the security of its users seriously — hosts, exam candidates, and audience
participants trust the platform with authentication data, exam content, and in some cases
webcam/biometric proctoring data. We appreciate the work of security researchers who help
keep that trust intact.

## Supported Versions

Swaya.me is a continuously-deployed web application, not a versioned release train. The
`main` branch and the live deployment at [www.swaya.me](https://www.swaya.me) are always
the only supported target — there are no older versions to report against.

Self-hosted deployments (see [`docs/self-hosting/`](docs/self-hosting/)) should track `main`
and apply security fixes promptly once released.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Email **meetnishant@gmail.com** with:

- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal repro is ideal — proof-of-concept code, request/response
  examples, or a short screen recording all help)
- The affected component (backend endpoint, frontend page, self-hosting config, etc.) and,
  if known, the relevant file/line
- Whether you've tested against `www.swaya.me` directly or a local/self-hosted instance

### What to expect

- **Acknowledgement** within 3 business days.
- We'll work with you to understand impact and severity, and keep you updated as a fix is
  developed. Critical issues (authentication bypass, cross-tenant data exposure, remote code
  execution) are prioritized for immediate remediation; lower-severity issues are scheduled
  into the normal release cycle.
- Once a fix ships, we'll credit you in the fix's release notes/commit message unless you'd
  prefer to stay anonymous — let us know your preference when you report.

### Scope

In scope:
- The backend API and frontend at `www.swaya.me` / `test.swaya.me`
- Authentication, tenant isolation, and authorization logic
- Exam proctoring and candidate-data handling
- Self-hosting deployment configuration where a default/example setup is itself insecure

Out of scope:
- Findings that require physical access to a user's device
- Denial-of-service via sheer traffic volume (report application-level DoS — e.g. an
  unauthenticated endpoint with no rate limit — which *is* in scope)
- Social engineering against Swaya.me staff or users
- Issues in third-party dependencies with no Swaya.me-specific exploitation path (report
  those upstream instead; we do track and update dependencies, see
  [`docs/security.md`](docs/security.md))

### Safe harbor

We will not pursue legal action against researchers who report vulnerabilities in good
faith, in accordance with this policy, and who avoid privacy violations, data destruction,
and service disruption while investigating. Please give us a reasonable window to remediate
before any public disclosure.

## Security Architecture

For details on how authentication, tenant isolation, and data protection actually work in
the codebase, see [`docs/security.md`](docs/security.md).
