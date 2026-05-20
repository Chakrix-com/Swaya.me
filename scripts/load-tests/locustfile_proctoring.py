"""
Swaya.me Realistic Load Test + Proctoring & AI
==============================================
Simulates a high-stakes exam scenario:
  - 1 host using AI features and monitoring results
  - 1000+ anonymous participants taking a proctored exam

New functionalities simulated:
  1. Participants:
     - Proctoring session initialization
     - Periodic violation reporting (simulating tab switches, etc.)
     - Periodic biometric sample uploads
     - Periodic webcam snapshot uploads
  2. Hosts:
     - AI question generation
     - AI distractor generation
     - AI rewrite
     - Viewing proctoring reports

Run:
  JOIN_CODE=<code> SESSION_ID=<id> QUIZ_ID=<qid> locust -f locustfile_proctoring.py \
    --headless -u 1000 -r 30 -t 90s --host https://www.swaya.me
"""
import os
import random
import time
import io
from locust import HttpUser, task, between, events
from locust.exception import StopUser

JOIN_CODE = os.getenv("JOIN_CODE", "")
SESSION_ID = os.getenv("SESSION_ID", "")
QUIZ_ID = os.getenv("QUIZ_ID", "")

if not all([JOIN_CODE, SESSION_ID, QUIZ_ID]):
    raise SystemExit(
        "ERROR: Set JOIN_CODE, SESSION_ID, and QUIZ_ID.\n"
        "Example: JOIN_CODE=123456 SESSION_ID=99 QUIZ_ID=13 locust -f locustfile_proctoring.py ..."
    )

# Pre-obtain a host token
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
        print(f"WARNING: Host login failed ({resp.status_code}). Host tasks may fail.")


class ProctoredParticipant(HttpUser):
    """
    Anonymous participant taking a proctored exam.
    Simulates high frequency of proctoring-related pings.
    """
    weight = 1000
    wait_time = between(1, 3)

    def on_start(self):
        self.session_token = None
        self.participant_session_id = None
        self.answered_questions = set()
        self.proctoring_initialized = False

        name = f"Proctor_{random.randint(10000, 99999)}"
        with self.client.post(
            "/api/v1/quizzes/sessions/join",
            json={"join_code": JOIN_CODE, "display_name": name},
            verify=False,
            catch_response=True,
            name="PART: POST /sessions/join",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.session_token = data.get("session_token")
                self.participant_session_id = data.get("session_id")
                resp.success()
                self.init_proctoring()
            elif resp.status_code == 429:
                resp.failure("Rate limited on join")
                raise StopUser()
            else:
                resp.failure(f"Join failed {resp.status_code}")
                raise StopUser()

    def init_proctoring(self):
        """Initialize proctoring session."""
        if not self.session_token:
            return
        
        headers = {"X-Session-Token": self.session_token}
        with self.client.post(
            "/api/v1/proctoring/session/init",
            headers=headers,
            json={
                "quiz_id": int(QUIZ_ID),
                "browser_fingerprint": f"fp_{random.getrandbits(64)}",
                "webcam_granted": True
            },
            verify=False,
            catch_response=True,
            name="PROCTOR: POST /session/init"
        ) as resp:
            if resp.status_code == 200:
                self.proctoring_initialized = True

    @task(5)
    def poll_question(self):
        """Poll current question."""
        if not self.session_token: return
        self.client.get(
            f"/api/v1/quizzes/sessions/{self.participant_session_id}/audience-results",
            params={"session_token": self.session_token},
            verify=False,
            name="PART: GET /audience-results",
        )

    @task(1)
    def report_violation(self):
        """Simulate occasional background violations (tab switch, etc.)"""
        if not self.proctoring_initialized: return
        
        # Only 5% of pings are violations to keep it realistic
        if random.random() > 0.05: return

        rules = ["tab_switch_detect", "copy_paste_block", "right_click_block", "fullscreen_enforce"]
        events = ["TAB_SWITCHED", "COPY_PASTE_ATTEMPTED", "RIGHT_CLICK", "FULLSCREEN_EXITED"]
        idx = random.randint(0, len(rules)-1)

        self.client.post(
            "/api/v1/proctoring/event",
            json={
                "session_token": self.session_token,
                "rule_id": rules[idx],
                "event_type": events[idx],
                "metadata": {"load_test": True}
            },
            verify=False,
            name="PROCTOR: POST /event (violation)"
        )

    @task(2)
    def upload_biometrics(self):
        """Simulate periodic behavioral biometrics upload."""
        if not self.proctoring_initialized: return
        
        self.client.post(
            "/api/v1/proctoring/biometrics",
            json={
                "session_token": self.session_token,
                "mouse_path": [{"x": random.randint(0, 1000), "y": random.randint(0, 1000), "t": time.time()} for _ in range(5)],
                "keystroke_intervals": [random.randint(100, 300) for _ in range(5)],
                "backspace_count": random.randint(0, 2),
                "scroll_events": [{"y": random.randint(0, 500), "t": time.time()}],
                "time_to_first_interaction_ms": random.randint(1000, 5000)
            },
            verify=False,
            name="PROCTOR: POST /biometrics"
        )

    @task(1)
    def upload_snapshot(self):
        """Simulate periodic webcam snapshots (high bandwidth/disk IO task)."""
        if not self.proctoring_initialized: return
        
        # Fake image data
        image_data = b"\xff\xd8\xff\xe0" + os.urandom(1024) + b"\xff\xd9"
        files = {
            "file": ("snapshot.jpg", io.BytesIO(image_data), "image/jpeg")
        }
        headers = {"X-Session-Token": self.session_token}
        
        self.client.post(
            "/api/v1/proctoring/snapshot",
            headers=headers,
            files=files,
            verify=False,
            name="PROCTOR: POST /snapshot"
        )

    @task(1)
    def submit_answer(self):
        """Submit answer with timing validation."""
        if not self.session_token: return

        # 2. Actual submission
        # We need a valid question_id for this session to avoid 400.
        # But in a simple load test without fetching full state, we might hit 400 if ID is wrong.
        # Let's try to fetch state once to get a real ID.
        if not hasattr(self, 'current_question_id'):
            with self.client.get(
                f"/api/v1/quizzes/sessions/{self.participant_session_id}/audience-results",
                params={"session_token": self.session_token},
                verify=False,
                name="PART: GET /audience-results",
            ) as resp:
                if resp.status_code == 200:
                    cq = resp.json().get("current_question")
                    if cq:
                        self.current_question_id = cq.get("id")

        if hasattr(self, 'current_question_id'):
            # 1. Answer timing validation ping
            self.client.post(
                "/api/v1/proctoring/answer-timing",
                json={
                    "session_token": self.session_token,
                    "question_id": self.current_question_id, 
                    "question_type": "mcq",
                    "question_word_count": 10,
                    "elapsed_ms": random.randint(5000, 15000)
                },
                verify=False,
                name="PROCTOR: POST /answer-timing"
            )

            self.client.post(
                "/api/v1/quizzes/sessions/submit-answer",
                params={"session_token": self.session_token},
                json={"question_id": self.current_question_id, "selected_option_index": random.randint(0, 3)},
                verify=False,
                name="PART: POST /submit-answer",
            )

    @task(1)
    def fetch_state(self):
        """Periodically fetch state to refresh question_id."""
        if not self.session_token: return
        with self.client.get(
            f"/api/v1/quizzes/sessions/{self.participant_session_id}/audience-results",
            params={"session_token": self.session_token},
            verify=False,
            catch_response=True,
            name="PART: GET /audience-results",
        ) as resp:
            if resp.status_code == 200:
                cq = resp.json().get("current_question")
                if cq:
                    self.current_question_id = cq.get("id")


class AIHost(HttpUser):
    """
    Host using AI features and proctoring reports.
    Simulates high CPU/GPU load on backend.
    """
    weight = 10 # Increased weight for visibility
    wait_time = between(5, 15)

    def on_start(self):
        if not _HOST_TOKEN:
            raise StopUser()
        self.headers = {"Authorization": f"Bearer {_HOST_TOKEN}"}

    @task(5)
    def view_reports(self):
        """Monitor results and proctoring violations."""
        # 1. Session results
        self.client.get(
            f"/api/v1/quizzes/sessions/{SESSION_ID}/results",
            headers=self.headers,
            verify=False,
            timeout=300,
            name="HOST: GET /session-results",
        )
        # 2. Proctoring violation report
        self.client.get(
            f"/api/v1/proctoring/report/{QUIZ_ID}",
            headers=self.headers,
            verify=False,
            timeout=300,
            name="HOST: GET /proctoring-report",
        )

    @task(1)
    def use_ai_generation(self):
        """Stress the local LLM endpoints."""
        action = random.choice(["questions", "options", "rewrite"])
        
        if action == "questions":
            self.client.post(
                "/api/v1/ai/generate/questions",
                headers=self.headers,
                json={"topic": "General Knowledge", "count": 2},
                timeout=300,
                verify=False,
                name="AI: POST /generate/questions"
            )
        elif action == "options":
            self.client.post(
                "/api/v1/ai/generate/options",
                headers=self.headers,
                json={"question": "What is 2+2?", "correct_answer": "4", "count": 3},
                timeout=300,
                verify=False,
                name="AI: POST /generate/options"
            )
        elif action == "rewrite":
            self.client.post(
                "/api/v1/ai/rewrite",
                headers=self.headers,
                json={"text": "This is a test question for rewriting", "context": "quiz question"},
                timeout=300,
                verify=False,
                name="AI: POST /rewrite"
            )
