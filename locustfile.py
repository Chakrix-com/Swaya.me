"""
Swaya.me Load Test — Concurrent Participant Simulation
=======================================================
Tests the participant-facing API under concurrent load.

Flow per virtual user:
  1. Join a pre-started quiz session (POST /quizzes/sessions/join)
  2. Fetch current question (GET /quizzes/sessions/{id}/audience-results)
  3. Submit an MCQ answer (POST /quizzes/sessions/submit-answer)
  4. Poll for results 3× (simulates waiting for next question)

Run examples:
  # Headless run — 100 users, ramp 10/s, 60s duration
  locust -f locustfile.py --headless -u 100 -r 10 -t 60s --host https://test.swaya.me

  # Interactive web UI
  locust -f locustfile.py --host https://test.swaya.me

Environment variables:
  JOIN_CODE      6-digit code from a pre-started quiz session (required)
  SESSION_ID     session ID for audience-results polling (required)
  LOCUST_HOST    override host (default: https://test.swaya.me)
"""
import os
import random
from locust import HttpUser, task, between, events
from locust.exception import StopUser

JOIN_CODE = os.getenv("JOIN_CODE", "")
SESSION_ID = os.getenv("SESSION_ID", "")

if not JOIN_CODE or not SESSION_ID:
    raise SystemExit(
        "ERROR: Set JOIN_CODE and SESSION_ID environment variables.\n"
        "Example: JOIN_CODE=245978 SESSION_ID=575 locust -f locustfile.py ..."
    )


class QuizParticipant(HttpUser):
    """
    Simulates a participant joining and answering a live quiz question.
    wait_time: between 1–3 seconds between tasks (realistic think time)
    """
    wait_time = between(1, 3)

    def on_start(self):
        """Called once when the virtual user starts — join the session."""
        self.session_token = None
        self.participant_session_id = None
        self.question_id = None
        self.answered_questions = set()  # track answered question IDs

        name = f"LoadTester_{random.randint(10000, 99999)}"
        with self.client.post(
            "/api/v1/quizzes/sessions/join",
            json={"join_code": JOIN_CODE, "display_name": name},
            verify=False,
            catch_response=True,
            name="/api/v1/quizzes/sessions/join",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.session_token = data.get("session_token")
                self.participant_session_id = data.get("session_id")
                resp.success()
            elif resp.status_code == 429:
                resp.failure(f"Rate limited: {resp.status_code}")
                raise StopUser()
            else:
                resp.failure(f"Join failed: {resp.status_code} — {resp.text[:200]}")
                raise StopUser()

    @task(3)
    def get_current_question(self):
        """Poll current question — most frequent action (3× weight)."""
        if not self.session_token:
            return
        self.client.get(
            f"/api/v1/quizzes/sessions/{self.participant_session_id}/audience-results",
            params={"session_token": self.session_token},
            verify=False,
            name="/api/v1/quizzes/sessions/{id}/audience-results",
        )

    @task(1)
    def submit_answer(self):
        """Submit an MCQ answer — only once per question, 1× weight."""
        if not self.session_token:
            return

        # Fetch current question
        resp = self.client.get(
            f"/api/v1/quizzes/sessions/{self.participant_session_id}/audience-results",
            params={"session_token": self.session_token},
            verify=False,
            name="/api/v1/quizzes/sessions/{id}/audience-results [pre-submit]",
        )
        if resp.status_code != 200:
            return

        data = resp.json()
        question = data.get("current_question")
        if not question:
            return

        question_id = question.get("id")
        # Skip if already answered this question
        if question_id in self.answered_questions:
            return

        selected = random.randint(0, 3)
        with self.client.post(
            "/api/v1/quizzes/sessions/submit-answer",
            params={"session_token": self.session_token},
            json={"question_id": question_id, "selected_option_index": selected},
            verify=False,
            name="/api/v1/quizzes/sessions/submit-answer",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                self.answered_questions.add(question_id)
                r.success()
            elif r.status_code == 400 and "already" in r.text.lower():
                # Idempotent — already answered, not a real failure
                self.answered_questions.add(question_id)
                r.success()
            else:
                r.failure(f"Submit failed: {r.status_code}")


class QuizHost(HttpUser):
    """
    Simulates the host polling session results (1 host per run).
    Lower weight — host is just 1 person checking results.
    """
    wait_time = between(2, 5)
    weight = 1  # 1 host vs many participants

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": os.getenv("HOST_EMAIL", "demo@swaya.me"),
                  "password": os.getenv("HOST_PASSWORD", "Demo1234")},
            verify=False,
            name="/api/v1/auth/login",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
        else:
            raise StopUser()

    @task
    def get_session_results(self):
        self.client.get(
            f"/api/v1/quizzes/sessions/{SESSION_ID}/results",
            headers={"Authorization": f"Bearer {self.token}"},
            verify=False,
            name="/api/v1/quizzes/sessions/{id}/results [host]",
        )
