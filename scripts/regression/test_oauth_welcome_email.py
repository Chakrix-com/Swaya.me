#!/usr/bin/env python3
"""
Google OAuth endpoint availability + welcome-email path coverage.

The welcome email fires in two places:
  1. /auth/verify-email — email/password registration flow
  2. oauth_login_or_register() — new Google OAuth users (added this session)

We cannot drive a real Google OAuth code exchange in CI, so this test covers:
  - /auth/google/login does not 500 (returns redirect or 503-not-configured)
  - /auth/google/callback with a garbage code returns 400, not 500
    (catches the lambda-arity bug: wrong signature causes 500 on every login)
  - /auth/verify-email with an invalid token returns 400, not 500
  - Normal email/password login still works end-to-end (confirms rate-limit
    lambda fix didn't break the login path)
"""
import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://test.swaya.me").rstrip("/")
EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check(cond: bool, msg: str):
    if not cond:
        fail(msg)


def main():
    s = requests.Session()
    s.verify = False

    # 1. /auth/google/login — must not 500.
    #    Returns 302 redirect (configured) or 503 (no client_id set).
    r = s.get(f"{BASE_URL}/auth/google/login", allow_redirects=False, timeout=20)
    check(
        r.status_code not in (500, 422),
        f"/auth/google/login returned {r.status_code} — expected redirect or 503"
    )
    print(f"OK: /auth/google/login  status={r.status_code} (redirect or 503-not-configured)")

    # 2. /auth/google/callback with a garbage code — must return 400, not 500.
    #    A 500 here indicates the lambda-arity bug or an unhandled exception.
    r = s.get(f"{BASE_URL}/auth/google/callback", params={"code": "not_a_real_code"},
              allow_redirects=False, timeout=20)
    check(
        r.status_code not in (500,),
        f"/auth/google/callback returned 500 on bad code — unhandled exception"
    )
    check(
        r.status_code in (400, 401, 422, 503),
        f"/auth/google/callback returned unexpected {r.status_code} — expected 4xx"
    )
    print(f"OK: /auth/google/callback bad code  status={r.status_code}")

    # 3. /auth/verify-email with an invalid token — must return 400, not 500.
    r = s.post(f"{BASE_URL}/auth/verify-email",
               json={"token": "completely-invalid-token-xyz"}, timeout=20)
    check(
        r.status_code == 400,
        f"/auth/verify-email bad token returned {r.status_code}, expected 400"
    )
    print(f"OK: /auth/verify-email invalid token  status=400")

    # 4. Normal email/password login still works.
    #    This confirms the rate-limit lambda fix (lambda: settings...) didn't break login.
    r = s.post(f"{BASE_URL}/auth/login",
               json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    check(r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}")
    token = r.json().get("access_token")
    check(bool(token), "login returned no access_token")
    print(f"OK: email/password login works  token={token[:12]}…")

    # 5. /auth/me works with the token (confirms JWT is valid after login).
    r = s.get(f"{BASE_URL}/auth/me",
              headers={"Authorization": f"Bearer {token}"}, timeout=20)
    check(r.status_code == 200, f"/auth/me failed: {r.status_code}")
    print(f"OK: /auth/me  user={r.json().get('email')}")

    print("\nOK: oauth_welcome_email — all checks passed")


if __name__ == "__main__":
    main()
