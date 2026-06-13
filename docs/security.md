# Security

This document covers the security architecture of Swaya: how authentication works, how tokens are managed, what protections are in place against common web vulnerabilities, and what to consider when contributing.

---

## Authentication

### Primary: HttpOnly Cookie JWT

After a successful login, the server sets an `access_token` cookie with these attributes:

```
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=28800
```

| Attribute | Effect |
|---|---|
| `HttpOnly` | JavaScript cannot read the cookie — eliminates XSS token theft |
| `Secure` | Cookie is only sent over HTTPS |
| `SameSite=Lax` | Cookie is not sent on cross-site POST requests — mitigates CSRF |
| `Max-Age=28800` | 8-hour session |

### Secondary: Bearer Header

API clients (scripts, integrations) can authenticate with `Authorization: Bearer <token>` instead of cookies. The token is the same JWT; the backend accepts either.

---

## JWT Token Revocation

Standard JWTs are stateless — they are valid until expiry even after logout. Swaya makes logout immediate via a Redis-backed blocklist.

Each JWT contains a unique `jti` (JWT ID) claim (a UUID generated at token creation).

**On logout:**
1. The `jti` is added to Redis with a TTL equal to the remaining lifetime of the token.
2. `POST /api/v1/auth/logout` clears the cookie and adds the jti to the blocklist.

**On every authenticated request:**
1. `get_current_user` decodes the JWT.
2. Checks Redis: `EXISTS jti:<jti-value>`.
3. If found → 401. If not found → proceed.

This means a stolen token is invalidated the moment the legitimate user logs out.

---

## Google OAuth CSRF Protection

The OAuth 2.0 authorization code flow is vulnerable to CSRF if the `state` parameter is not validated. Swaya:

1. On `GET /auth/google/login`: generates a cryptographically random state token (`secrets.token_urlsafe(32)`), stores it in Redis with a 10-minute TTL, includes it in the redirect URL.
2. On `GET /auth/google/callback`: validates that the returned `state` matches the stored value, then deletes it from Redis.

A missing or mismatched state → HTTP 400, request rejected.

---

## Rate Limiting

SlowAPI rate limiting (via `slowapi`, a FastAPI wrapper around `limits`) is applied on all sensitive endpoints:

| Endpoint group | Limit |
|---|---|
| Auth endpoints (login, register) | 10/minute |
| Exam OTP request + start | 10/minute |
| AI generation endpoints | 20/minute |
| Quiz join/submit | 60/minute |
| Analytics beacon | 120/minute |

Limits are applied per IP address. A 429 response is returned when the limit is exceeded.

---

## Input Sanitization

### Rich Text (HTML)

Question text supports a limited subset of HTML (bold, italic, lists, links). All HTML is sanitized through an allowlist-based sanitizer (`shared/utils/html_sanitizer.py`) using the `bleach` library before storage:

```python
ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br', 'p', 'span']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title'], 'span': ['style']}
```

Any tag or attribute not in the allowlist is stripped.

### Plain Text Fields

Fields that should not contain HTML (option text, display names, quiz titles) are sanitized with `sanitize_plain()` which strips all HTML tags via `bleach.clean(..., tags=[])`.

### Email Templates

User-controlled values in HTML email templates (display names, quiz titles) are escaped with `html.escape()` before interpolation.

### Excel Import

All text imported from uploaded `.xlsx` files passes through the same HTML and plain-text sanitizers before DB insertion.

---

## File Upload Security

### Image Uploads

- MIME type validated server-side (not trusting the `Content-Type` header alone).
- Files stored with a UUID-based filename — original filename is never used.
- Served from `/api/uploads/images/` (public static mount).

### Proctoring Snapshots

- Stored in `backend/uploads/proctoring/` — this directory is **not** statically mounted.
- Served only through an authenticated API endpoint (`GET /api/v1/proctoring/snapshot-file/{quiz_id}/{participant_id}/{filename}`).
- The endpoint verifies the requesting user owns the tenant that owns the quiz.
- Path traversal is prevented by rejecting filenames containing `/` or `..`.

---

## SQL Injection

All database queries use SQLAlchemy ORM or parameterized `text()` with `:param` syntax. Raw string interpolation into SQL queries is never used.

---

## Tenant Isolation

Every service function filters by `tenant_id`. A user from tenant A cannot access data from tenant B regardless of knowing the IDs of tenant B's resources. See [multi-tenancy.md](multi-tenancy.md) for the full model.

---

## Dependency Security

- `python-jose` (which had active CVEs CVE-2024-33664 and CVE-2024-33663) was removed and replaced with `PyJWT` + `cryptography`.
- `cryptography` is pinned to a recent version without known vulnerabilities.
- Run `pip audit` periodically to check for new vulnerabilities in Python dependencies.
- Run `npm audit` for frontend dependencies.

---

## Security Headers

Add these headers in Nginx for defense in depth:

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self';" always;
```

Adjust the CSP `connect-src` if you use a third-party analytics or error tracking service.

---

## Session Storage vs localStorage

- Authentication tokens are in HttpOnly cookies — inaccessible to JavaScript.
- Exam `session_token` (participant, not a JWT) is stored in `sessionStorage` — scoped to the browser tab, cleared on tab close, not accessible from other origins.
- No sensitive data is written to `localStorage`.

---

## Reporting Vulnerabilities

If you discover a security vulnerability, please do **not** open a public GitHub issue. Email the maintainer directly at the address in the GitHub profile. Include a description of the vulnerability, reproduction steps, and the potential impact.
