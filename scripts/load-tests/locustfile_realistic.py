"""
Swaya.me Realistic Load Test
============================
Simulates the actual production scenario:
  - 1 host already logged in, running a quiz (pre-started before test)
  - 1000–1500 anonymous participants joining via join code (no login)

Participant flow:
  1. Join session anonymously (POST /sessions/join)
  2. Poll current question every 1–3s (GET /sessions/{id}/audience-results)
  3. Submit MCQ answer once per question
  4. Repeat polling

Host flow (1 user, weight=1 vs participant weight=1000):
  - Polls /sessions/{id}/results every 5–10s (as a logged-in host would)

Run:
  JOIN_CODE=<code> SESSION_ID=<id> locust -f locustfile_realistic.py \
    --headless -u 1000 -r 30 -t 90s --host https://www.swaya.me
"""
import os
import random
from locust import HttpUser, task, between, events
from locust.exception import StopUser

JOIN_CODE = os.getenv("JOIN_CODE", "")
SESSION_ID = os.getenv("SESSION_ID", "")

if not JOIN_CODE or not SESSION_ID:
    raise SystemExit(
        "ERROR: Set JOIN_CODE and SESSION_ID.\n"
        "Example: JOIN_CODE=123456 SESSION_ID=99 locust -f locustfile_realistic.py ..."
    )

# Pre-obtain a host token once at test start (simulates already-logged-in host)
_HOST_TOKEN = None

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global _HOST_TOKEN
    import requests
    resp = requests.post(
        f"{environment.host}/api/v1/auth/login",
        json={
            "email": os.getenv("HOST_EMAIL", "demo@swaya.me"),
            "password": os.getenv("HOST_PASSWORD", "Demo1234"),
        },
        verify=False,
    )
    if resp.status_code == 200:
        _HOST_TOKEN = resp.json().get("access_token")
        print(f"Host logged in. Token acquired.")
    else:
        print(f"WARNING: Host login failed ({resp.status_code}). Host polling disabled.")


class AnonParticipant(HttpUser):
    """
    Anonymous participant — joins with join code, polls, answers.
    weight=1000 ensures ~999 participants for every 1 host.
    """
    weight = 1000
    wait_time = between(1, 3)

    def on_start(self):
        self.session_token = None
        self.participant_session_id = None
        self.answered_questions = set()

        name = f"Guest_{random.randint(10000, 99999)}"
        with self.client.post(
            "/api/v1/quizzes/sessions/join",
            json={"join_code": JOIN_CODE, "display_name": name},
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
                resp.failure(f"Join failed {resp.status_code}: {resp.text[:100]}")
                raise StopUser()

    @task(3)
    def poll_question(self):
        """Poll current question — most frequent action."""
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
        """Submit answer — once per question."""
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
            json={"question_id": question_id, "selected_option_index": random.randint(0, 3)},
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


class QuizHost(HttpUser):
    """
    Single host polling results — weight=1 means ~1 host per 1000 participants.
    Uses the pre-acquired token (no bcrypt during the test).
    """
    weight = 1
    wait_time = between(5, 10)

    def on_start(self):
        if not _HOST_TOKEN:
            raise StopUser()
        self.token = _HOST_TOKEN

    @task
    def poll_results(self):
        self.client.get(
            f"/api/v1/quizzes/sessions/{SESSION_ID}/results",
            headers={"Authorization": f"Bearer {self.token}"},
            verify=False,
            name="GET /sessions/{id}/results [host]",
        )
