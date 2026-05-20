"""
Swaya.me Multi-Host Load Test
==============================
Scenario:
  - 5 hosts, each independently logged in, each running a different quiz
  - 2000 anonymous participants randomly distributed across the 5 sessions
  - All active simultaneously for 5 minutes

Host behaviour: polls /sessions/{id}/results every 5-10s (active host screen)
Participant behaviour: joins random session, polls every 1-3s, submits once per question

User class weights:
  QuizHost   weight=1  → ~5 users  at spawn target 2005
  AnonParticipant weight=400 → ~2000 users at spawn target 2005
"""
import os
import random
from locust import HttpUser, task, between, events
from locust.exception import StopUser

# ── Session config (5 quizzes) ──────────────────────────────────────────────
SESSIONS = [
    {"name": "Geography", "session_id": 1107, "join_code": "254754"},
    {"name": "Science",   "session_id": 1108, "join_code": "450164"},
    {"name": "History",   "session_id": 1109, "join_code": "261251"},
    {"name": "Sports",    "session_id": 1110, "join_code": "893996"},
    {"name": "Technology","session_id": 1111, "join_code": "357971"},
]

HOST_CREDENTIALS = [
    {"email": "host.geography@loadtest.me",  "password": "Load1234!", "session_id": 1107},
    {"email": "host.science@loadtest.me",    "password": "Load1234!", "session_id": 1108},
    {"email": "host.history@loadtest.me",    "password": "Load1234!", "session_id": 1109},
    {"email": "host.sports@loadtest.me",     "password": "Load1234!", "session_id": 1110},
    {"email": "host.technology@loadtest.me", "password": "Load1234!", "session_id": 1111},
]

# Pre-acquired tokens — populated at test_start, one per host
_host_tokens = {}   # session_id → access_token


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Login all 5 hosts once before ramp-up. No bcrypt during the test."""
    import requests, urllib3
    urllib3.disable_warnings()
    for cred in HOST_CREDENTIALS:
        resp = requests.post(
            f"{environment.host}/api/v1/auth/login",
            json={"email": cred["email"], "password": cred["password"]},
            verify=False,
        )
        if resp.status_code == 200:
            _host_tokens[cred["session_id"]] = resp.json()["access_token"]
            print(f"  Host logged in: {cred['email']}")
        else:
            print(f"  WARNING: Host login failed for {cred['email']}: {resp.status_code}")

    if len(_host_tokens) < 5:
        print(f"WARNING: Only {len(_host_tokens)}/5 hosts authenticated")
    else:
        print("All 5 hosts authenticated. Starting ramp-up.")


# ── Host user ────────────────────────────────────────────────────────────────
_host_cred_index = 0
_host_cred_lock = __import__("threading").Lock()

class QuizHost(HttpUser):
    """
    One host per quiz. Cycles through the 5 host credentials round-robin.
    weight=1 → at 2005 users: ~5 QuizHost instances.
    """
    weight = 1
    wait_time = between(5, 10)

    def on_start(self):
        global _host_cred_index
        with _host_cred_lock:
            idx = _host_cred_index % 5
            _host_cred_index += 1
        cred = HOST_CREDENTIALS[idx]
        self.session_id = cred["session_id"]
        self.token = _host_tokens.get(self.session_id)
        if not self.token:
            raise StopUser()

    @task
    def poll_results(self):
        """Host polls their session results dashboard."""
        self.client.get(
            f"/api/v1/quizzes/sessions/{self.session_id}/results",
            headers={"Authorization": f"Bearer {self.token}"},
            verify=False,
            name="GET /sessions/{id}/results [host]",
        )


# ── Anonymous participant ────────────────────────────────────────────────────
class AnonParticipant(HttpUser):
    """
    Anonymous participant. Randomly joins one of the 5 sessions.
    weight=400 → at 2005 users: ~2000 AnonParticipant instances.
    """
    weight = 400
    wait_time = between(1, 3)

    def on_start(self):
        self.session_token = None
        self.participant_session_id = None
        self.answered_questions = set()

        # Random session assignment
        session = random.choice(SESSIONS)
        self.assigned_session = session["name"]

        name = f"Guest_{random.randint(10000, 99999)}"
        with self.client.post(
            "/api/v1/quizzes/sessions/join",
            json={"join_code": session["join_code"], "display_name": name},
            verify=False,
            catch_response=True,
            name="POST /sessions/join",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.session_token = data.get("session_token")
                self.participant_session_id = data.get("session_id")
                resp.success()
            elif resp.status_code == 429:
                resp.failure("Rate limited on join")
                raise StopUser()
            else:
                resp.failure(f"Join failed {resp.status_code}: {resp.text[:120]}")
                raise StopUser()

    @task(3)
    def poll_question(self):
        """Poll current question state — most frequent action."""
        if not self.session_token:
            return
        self.client.get(
            f"/api/v1/quizzes/sessions/{self.participant_session_id}/audience-results",
            params={"session_token": self.session_token},
            verify=False,
            name="GET /sessions/{id}/audience-results",
        )

    @task(1)
    def submit_answer(self):
        """Fetch question then submit answer — once per question."""
        if not self.session_token:
            return

        resp = self.client.get(
            f"/api/v1/quizzes/sessions/{self.participant_session_id}/audience-results",
            params={"session_token": self.session_token},
            verify=False,
            name="GET /sessions/{id}/audience-results [pre-submit]",
        )
        if resp.status_code != 200:
            return

        question = resp.json().get("current_question")
        if not question:
            return

        question_id = question.get("id")
        if question_id in self.answered_questions:
            return

        with self.client.post(
            "/api/v1/quizzes/sessions/submit-answer",
            params={"session_token": self.session_token},
            json={
                "question_id": question_id,
                "selected_option_index": random.randint(0, 3),
            },
            verify=False,
            catch_response=True,
            name="POST /sessions/submit-answer",
        ) as r:
            if r.status_code == 200:
                self.answered_questions.add(question_id)
                r.success()
            elif r.status_code == 400 and "already" in r.text.lower():
                self.answered_questions.add(question_id)
                r.success()
            else:
                r.failure(f"Submit failed: {r.status_code}")
