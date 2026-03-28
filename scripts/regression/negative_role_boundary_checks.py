#!/usr/bin/env python3
"""
Role Boundary Checks
Verifies that all admin-only endpoints return 403 when called by a regular user (role=user, tier=FREE).
"""
import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
EMAIL = os.getenv("REGULAR_USER_EMAIL", "regression-free@swaya.me")
PASSWORD = os.getenv("REGULAR_USER_PASSWORD", "RegTest2026!")


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    s = requests.Session()
    s.verify = False

    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    if r.status_code != 200:
        fail(f"login failed: {r.status_code} {r.text[:200]}")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    print("OK: login as regular user")

    admin_endpoints = [
        ("GET",  f"{BASE_URL}/admin/stats",            "admin stats"),
        ("GET",  f"{BASE_URL}/admin/feedback",         "admin feedback"),
        ("GET",  f"{BASE_URL}/admin/organizations",    "admin organizations"),
        ("GET",  f"{BASE_URL}/admin/tier-configs",     "admin tier-configs"),
        ("GET",  f"{BASE_URL}/admin/language-stats",   "admin language-stats"),
        ("GET",  f"{BASE_URL}/admin/app-feedback",     "admin app-feedback"),
        ("GET",  f"{BASE_URL}/admin/quizzes",          "admin quizzes"),
    ]

    errors = []
    for method, url, label in admin_endpoints:
        r = s.request(method, url, timeout=20)
        if r.status_code not in (403, 401):
            errors.append(f"{label} ({method} {url}) returned {r.status_code} — expected 401/403")
            print(f"FAIL: {label} → {r.status_code}")
        else:
            print(f"OK: {label} → {r.status_code} (blocked as expected)")

    if errors:
        fail("Role boundary violations:\n  " + "\n  ".join(errors))

    print("\nOK: negative_role_boundary_checks — all admin endpoints blocked for regular user")


if __name__ == "__main__":
    main()
