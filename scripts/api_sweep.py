"""
Comprehensive API smoke sweep — exercises auth, quiz CRUD (all 5 types), questions,
folders, publish/session/join/participants/end lifecycle, coding-challenge invites,
and the tier_override admin flow. Creates only ephemeral data under the given
super_admin account and deletes everything it creates.

Safe to run against either test.swaya.me or www.swaya.me — set SWAYA_API_BASE and
SWAYA_TOKEN. Does NOT provision a real Coder workspace (no POST .../start call) —
that's a separate, slower, infra-touching check, not part of this smoke sweep.

Usage:
    TOKEN=$(cd backend && source .venv/bin/activate && \\
        python /home/vinay/Swaya.me/scripts/generate_selenium_token.py meetnishant@gmail.com \\
        [--env /www/wwwroot/swaya-live/backend/.env])
    SWAYA_API_BASE=https://test.swaya.me/api/v1 SWAYA_TOKEN="$TOKEN" \\
        python scripts/api_sweep.py
"""
import os
import random
import string
import sys

import requests

BASE = os.environ.get("SWAYA_API_BASE", "https://test.swaya.me/api/v1")
TOKEN = os.environ.get("SWAYA_TOKEN", "").strip()
if not TOKEN:
    print("FATAL: SWAYA_TOKEN env var not set")
    sys.exit(1)

H = {"Authorization": f"Bearer {TOKEN}"}
findings = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        findings.append({"name": name, "detail": detail})


def rid(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def cleanup(s, created):
    """Always run, even if the sweep above raised — an uncaught exception (a real
    network error, not just a failed check()) must never leave sweep-* quizzes
    orphaned and visible on a real account, live in particular."""
    for qtype, qid in created["quiz_ids"].items():
        if not qid:
            continue
        try:
            r = s.delete(f"{BASE}/quizzes/{qid}")
            check(f"DELETE /quizzes/{{id}} ({qtype}) cleanup", r.status_code in (200, 204), f"status={r.status_code}")
        except Exception as e:
            check(f"DELETE /quizzes/{{id}} ({qtype}) cleanup", False, f"exception: {e}")
    if created["folder_id"]:
        try:
            r = s.delete(f"{BASE}/quizzes/folders/{created['folder_id']}")
            check("DELETE /quizzes/folders/{id} cleanup", r.status_code in (200, 204), f"status={r.status_code}")
        except Exception as e:
            check("DELETE /quizzes/folders/{id} cleanup", False, f"exception: {e}")


def run_sweep(s, created):
    print(f"Target: {BASE}\n")

    r = s.get(f"{BASE}/auth/me")
    check("GET /auth/me", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
    me = r.json() if r.status_code == 200 else {}

    r = s.get(f"{BASE}/auth/tier-plans")
    check("GET /auth/tier-plans", r.status_code == 200, f"status={r.status_code}")

    # Written into created["quiz_ids"] directly (same dict object) so cleanup()
    # sees every quiz created so far even if a later step raises.
    quiz_ids = created["quiz_ids"]
    for qtype in ["quiz", "poll", "offline_poll", "exam", "coding_challenge"]:
        payload = {"title": f"sweep-{qtype}-{rid()}", "quiz_type": qtype}
        r = s.post(f"{BASE}/quizzes/", json=payload)
        ok = r.status_code in (200, 201)
        check(f"POST /quizzes/ type={qtype}", ok, f"status={r.status_code} body={r.text[:300]}")
        if ok:
            quiz_ids[qtype] = r.json().get("id")

    r = s.get(f"{BASE}/quizzes/")
    check("GET /quizzes/ (list)", r.status_code == 200, f"status={r.status_code}")

    for qtype, qid in quiz_ids.items():
        if not qid:
            continue
        r = s.get(f"{BASE}/quizzes/{qid}")
        check(f"GET /quizzes/{{id}} ({qtype})", r.status_code == 200, f"status={r.status_code}")
        r = s.put(f"{BASE}/quizzes/{qid}", json={"title": f"sweep-{qtype}-renamed-{rid()}"})
        check(f"PUT /quizzes/{{id}} ({qtype})", r.status_code == 200, f"status={r.status_code} body={r.text[:300]}")

    lq_id = quiz_ids.get("quiz")
    question_id = None
    if lq_id:
        payload = {
            "question_type": "mcq",
            "text": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
            "correct_answer_index": 1,
            "max_time_seconds": 20,
        }
        r = s.post(f"{BASE}/quizzes/{lq_id}/questions", json=payload)
        ok = r.status_code in (200, 201)
        check("POST /quizzes/{id}/questions (mcq)", ok, f"status={r.status_code} body={r.text[:300]}")
        if ok:
            question_id = r.json().get("id")

    r = s.post(f"{BASE}/quizzes/folders", json={"name": f"sweep-folder-{rid()}"})
    folder_ok = r.status_code in (200, 201)
    check("POST /quizzes/folders", folder_ok, f"status={r.status_code} body={r.text[:300]}")
    folder_id = r.json().get("id") if folder_ok else None
    created["folder_id"] = folder_id
    if folder_id and lq_id:
        r = s.put(f"{BASE}/quizzes/{lq_id}/folder", json={"folder_id": folder_id})
        check("PUT /quizzes/{id}/folder", r.status_code == 200, f"status={r.status_code} body={r.text[:300]}")

    session_id = None
    join_code = None
    if lq_id and question_id:
        r = s.post(f"{BASE}/quizzes/{lq_id}/publish")
        check("POST /quizzes/{id}/publish", r.status_code == 200, f"status={r.status_code} body={r.text[:300]}")

        r = s.post(f"{BASE}/quizzes/sessions/start", params={"quiz_id": lq_id})
        ok = r.status_code in (200, 201)
        check("POST /quizzes/sessions/start", ok, f"status={r.status_code} body={r.text[:300]}")
        if ok:
            sd = r.json()
            session_id = sd.get("id")
            join_code = sd.get("join_code")

    if join_code:
        anon = requests.Session()
        r = anon.post(f"{BASE}/quizzes/sessions/join", json={"join_code": join_code, "display_name": "SweepBot"})
        ok = r.status_code in (200, 201)
        check("POST /quizzes/sessions/join (anonymous participant)", ok, f"status={r.status_code} body={r.text[:300]}")

        if session_id:
            r = s.get(f"{BASE}/quizzes/sessions/{session_id}/participants-list")
            check("GET /quizzes/sessions/{id}/participants-list", r.status_code == 200, f"status={r.status_code}")

    if session_id:
        r = s.post(f"{BASE}/quizzes/sessions/{session_id}/end")
        check("POST /quizzes/sessions/{id}/end", r.status_code in (200, 204), f"status={r.status_code} body={r.text[:300]}")

    # Coding-challenge invite flow (no workspace provisioning — invite/list only)
    cc_id = quiz_ids.get("coding_challenge")
    if cc_id:
        payload = {
            "question_type": "coding_challenge",
            "text": "Implement fizzbuzz",
            "git_repo_url": "https://github.com/octocat/Hello-World",
            "test_command": "pytest",
        }
        r = s.post(f"{BASE}/quizzes/{cc_id}/questions", json=payload)
        check("POST /quizzes/{id}/questions (coding_challenge)", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:300]}")

        r = s.post(f"{BASE}/quizzes/{cc_id}/coding-challenge/invite", json={"candidate_emails": [f"sweep-{rid()}@example.com"]})
        check("POST /quizzes/{id}/coding-challenge/invite", r.status_code == 200, f"status={r.status_code} body={r.text[:300]}")

        r = s.get(f"{BASE}/quizzes/{cc_id}/coding-challenge/invites")
        check("GET /quizzes/{id}/coding-challenge/invites", r.status_code == 200, f"status={r.status_code}")

    # Admin: tier_override set/clear on a non-self, non-super_admin user (skip if none found)
    r = s.get(f"{BASE}/users")
    users_ok = r.status_code == 200
    check("GET /users (admin list)", users_ok, f"status={r.status_code} body={r.text[:200]}")
    target_user_id = None
    if users_ok:
        for u in r.json().get("users", []):
            if u.get("email") != me.get("email") and u.get("role") != "super_admin":
                target_user_id = u.get("id")
                break

    if target_user_id:
        r = s.patch(f"{BASE}/users/{target_user_id}", json={"tier_override": "coding_challenge_pro"})
        check("PATCH /users/{id} set tier_override", r.status_code == 200, f"status={r.status_code} body={r.text[:300]}")
        ok_populated = r.status_code == 200 and r.json().get("tier") is not None
        check("PATCH /users/{id} response has non-null tier (regression check)", ok_populated, f"tier={r.json().get('tier') if r.status_code == 200 else None}")
        r = s.patch(f"{BASE}/users/{target_user_id}", json={"tier_override": None})
        check("PATCH /users/{id} clear tier_override", r.status_code == 200, f"status={r.status_code} body={r.text[:300]}")
    else:
        print("[SKIP] no non-super_admin user found to test tier_override on")

    # Negative/security checks — no state created
    r = requests.get(f"{BASE}/auth/me")
    check("unauthenticated GET /auth/me -> 401", r.status_code == 401, f"status={r.status_code}")
    r = requests.get(f"{BASE}/users")
    check("unauthenticated GET /users -> 401", r.status_code == 401, f"status={r.status_code}")


def main():
    s = requests.Session()
    s.headers.update(H)
    created = {"quiz_ids": {}, "folder_id": None}

    try:
        run_sweep(s, created)
    except Exception as e:
        check("run_sweep (uncaught exception)", False, f"{type(e).__name__}: {e}")
    finally:
        # Runs even if run_sweep raised — no orphaned sweep-* data left behind,
        # live in particular.
        cleanup(s, created)

    print("\n==== SUMMARY ====")
    print(f"Target: {BASE}")
    print(f"Total failures: {len(findings)}")
    for f_ in findings:
        print(f" - {f_['name']}: {f_['detail']}")
    if findings:
        sys.exit(1)


if __name__ == "__main__":
    main()
