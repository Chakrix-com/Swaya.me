#!/usr/bin/env python3
import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1").rstrip("/")
EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")


def fail(msg: str):
    print(f"FAIL: {msg}")
    sys.exit(1)


def expect(cond: bool, msg: str):
    if not cond:
        fail(msg)


def main():
    login = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        verify=False,
        timeout=20,
    )
    expect(login.status_code == 200, f"login failed: {login.status_code} {login.text[:200]}")
    token = login.json().get("access_token")
    expect(bool(token), "missing access token")
    host_headers = {"Authorization": f"Bearer {token}"}

    quizzes = requests.get(f"{BASE_URL}/quizzes/", headers=host_headers, verify=False, timeout=20)
    expect(quizzes.status_code == 200 and quizzes.json(), "no quiz available for negative checks")
    quiz_list = quizzes.json()

    # End any open sessions across all quizzes to avoid concurrent session limit
    for q in quiz_list:
        sess_r = requests.get(f"{BASE_URL}/quizzes/{q['id']}/sessions",
                              headers=host_headers, verify=False, timeout=20)
        if sess_r.status_code == 200:
            for s in sess_r.json().get("sessions", []):
                if s.get("status") in ("active", "created"):
                    requests.post(f"{BASE_URL}/quizzes/sessions/{s['id']}/end",
                                  headers=host_headers, verify=False, timeout=20)

    ready = next((q for q in quiz_list if str(q.get("status", "")).lower() == "ready"), None)
    expect(ready is not None, "no READY quiz available for negative checks")
    quiz_id = ready["id"]

    started = requests.post(
        f"{BASE_URL}/quizzes/sessions/start",
        params={"quiz_id": quiz_id},
        headers=host_headers,
        verify=False,
        timeout=20,
    )
    expect(started.status_code in (200, 201), f"session start failed: {started.status_code}")
    session_id = started.json()["id"]
    join_code = started.json()["join_code"]

    joined = requests.post(
        f"{BASE_URL}/quizzes/sessions/join",
        json={"join_code": join_code, "display_name": "negative-check-user"},
        verify=False,
        timeout=20,
    )
    expect(joined.status_code == 200, f"join failed: {joined.status_code}")
    participant_token = joined.json()["session_token"]

    # Host-only endpoint should reject anonymous calls.
    anon_host_results = requests.get(
        f"{BASE_URL}/quizzes/sessions/{session_id}/results",
        verify=False,
        timeout=20,
    )
    expect(anon_host_results.status_code in (401, 403), "host results endpoint exposed without auth")

    # Participant-safe endpoint should require token.
    no_token_results = requests.get(
        f"{BASE_URL}/quizzes/sessions/{session_id}/audience-results",
        verify=False,
        timeout=20,
    )
    expect(no_token_results.status_code in (400, 401, 422), "audience-results accepted request without token")

    # Token/session mismatch should be denied.
    mismatch = requests.get(
        f"{BASE_URL}/quizzes/sessions/{session_id + 999999}/audience-results",
        params={"session_token": participant_token},
        verify=False,
        timeout=20,
    )
    expect(mismatch.status_code in (403, 404), "audience-results allowed mismatched token/session")

    print("OK: negative checks passed")


if __name__ == "__main__":
    main()
