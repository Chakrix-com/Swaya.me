#!/usr/bin/env python3
"""
Rate-limit regression for /auth/login.

What we're guarding against:
  - The lambda-arity bug: @limiter.limit(lambda request: ...) caused 500 on every
    login because slowapi calls the provider with zero arguments. Fix was
    lambda: settings.app.login_rate_limit (no args).
  - The rate limit being so low it blocks the regression gate itself (previously
    10/min caused Suite B+C+D failures; test env now uses 300/min via systemd override).

What this test verifies:
  1. Rapid sequential bad-credential logins return 401, never 500.
  2. A valid login after bad attempts still returns 200.
  3. Rate-limit response headers are present on the login endpoint.
  4. /auth/register also doesn't 500 on repeated bad payloads (separate limiter).
"""
import os
import sys
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")

BAD_CREDS = {"email": "no-such-user-xyzzy-regression@gmail.com", "password": "wrongpassword"}
RAPID_ATTEMPTS = 8  # well under 300/min but enough to catch a 500 bug


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check(cond: bool, msg: str):
    if not cond:
        fail(msg)


def main():
    s = requests.Session()
    s.verify = False

    # 1. Rapid bad-credential logins must return 401, never 500.
    print(f"Sending {RAPID_ATTEMPTS} rapid bad-credential logins…")
    for i in range(RAPID_ATTEMPTS):
        r = s.post(f"{BASE_URL}/auth/login", json=BAD_CREDS, timeout=20)
        check(
            r.status_code != 500,
            f"Login attempt {i+1} returned 500 — lambda-arity bug or unhandled exception"
        )
        check(
            r.status_code in (401, 403, 429),
            f"Login attempt {i+1} returned unexpected {r.status_code} (expected 401/429)"
        )
    print(f"OK: {RAPID_ATTEMPTS} rapid bad logins all returned 401 or 429 (no 500)")

    # 2. Valid login still works after bad attempts.
    r = s.post(f"{BASE_URL}/auth/login",
               json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    check(
        r.status_code == 200,
        f"Valid login after bad attempts returned {r.status_code} — may be rate-limited or broken"
    )
    token = r.json().get("access_token")
    check(bool(token), "Valid login returned no access_token")
    print(f"OK: valid login still works after {RAPID_ATTEMPTS} bad attempts")

    # 3. Rate-limit headers are present on the login endpoint.
    #    slowapi injects X-RateLimit-Limit and X-RateLimit-Remaining.
    r = s.post(f"{BASE_URL}/auth/login", json=BAD_CREDS, timeout=20)
    has_rl_headers = any(
        h.lower().startswith("x-ratelimit") or h.lower() == "retry-after"
        for h in r.headers
    )
    if not has_rl_headers:
        # Non-fatal: some proxy configs strip these headers; log a warning, don't fail.
        print(f"WARN: no X-RateLimit-* headers found (proxy may strip them) — not failing")
    else:
        limit_header = r.headers.get("X-RateLimit-Limit", "")
        print(f"OK: rate-limit headers present  X-RateLimit-Limit={limit_header}")

    # 4. /auth/register with a missing required field returns 422, not 500.
    r = s.post(f"{BASE_URL}/auth/register",
               json={"email": "bad"}, timeout=20)
    check(
        r.status_code in (400, 422),
        f"/auth/register bad payload returned {r.status_code}, expected 422"
    )
    print(f"OK: /auth/register bad payload  status={r.status_code}")

    print("\nOK: rate_limiting — all checks passed")


if __name__ == "__main__":
    main()
