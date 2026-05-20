"""
Swaya.me Load Test - Quiz Participant Flow
Tests concurrent participants joining a quiz and submitting answers
"""
from locust import HttpUser, task, between, events
import random
import string
import time

# Configuration
BASE_URL = "https://www.swaya.me"
API_BASE = "/api/v1"

# You'll need to set these from an actual quiz session
QUIZ_ID = 13  # Update this with actual quiz ID
SESSION_ID = 344  # Session ID from join endpoint
JOIN_CODE = "106643"  # Join code from URL
CURRENT_QUESTION_ID = None  # Will be updated during test


class QuizParticipant(HttpUser):
    """
    Simulates a quiz participant:
    1. Joins quiz session with code
    2. Waits for question
    3. Submits answer
    4. Views results
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_token = None
        self.display_name = None
        self.participant_joined = False
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Generate random display name
        self.display_name = f"User_{random.randint(1000, 9999)}"
        
        # Join the quiz session
        self.join_quiz()
    
    def join_quiz(self):
        """Join quiz session with join code"""
        if not JOIN_CODE:
            print("⚠️  JOIN_CODE not set - skipping join")
            return
        
        try:
            response = self.client.post(
                f"{API_BASE}/quizzes/sessions/join",
                json={
                    "join_code": JOIN_CODE,
                    "display_name": self.display_name
                },
                name="/api/v1/quizzes/sessions/join"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_token = data.get("session_token")
                self.participant_joined = True
                print(f"✅ {self.display_name} joined successfully")
            else:
                print(f"❌ {self.display_name} failed to join: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Join error for {self.display_name}: {e}")
    
    @task(3)
    def get_session_results(self):
        """Check current quiz state and question (participant-safe)"""
        if not self.participant_joined or not SESSION_ID:
            return
        
        try:
            # Use participant-safe audience-results endpoint to avoid 403
            response = self.client.get(
                f"{API_BASE}/quizzes/sessions/{SESSION_ID}/audience-results",
                params={"session_token": self.session_token},
                name="/api/v1/quizzes/sessions/[id]/audience-results"
            )
            
            if response.status_code == 200:
                data = response.json()
                current_q = data.get("current_question")
                
                if current_q and current_q.get("id"):
                    # Use local variable for current question to avoid global contention issues
                    self.current_q_id = current_q["id"]
                    
        except Exception as e:
            print(f"⚠️  Results check error: {e}")
    
    @task(2)
    def submit_answer(self):
        """Submit answer to current question"""
        # Ensure we have a question ID from our own results check
        q_id = getattr(self, 'current_q_id', None)
        if not self.participant_joined or not q_id:
            return
        
        try:
            # Random answer (0, 1, 2, or 3 for A, B, C, D)
            answer = random.randint(0, 3)
            
            response = self.client.post(
                f"{API_BASE}/quizzes/sessions/submit-answer",
                params={"session_token": self.session_token},
                json={
                    "question_id": q_id,
                    "selected_option_index": answer
                },
                name="/api/v1/quizzes/sessions/submit-answer"
            )
            
            if response.status_code == 200:
                pass  # Success
            elif response.status_code == 400:
                # Might be duplicate answer or question not open
                pass
            else:
                print(f"⚠️  Submit answer failed: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Answer submit error: {e}")


class QuizHost(HttpUser):
    """
    Simulates the quiz host:
    1. Creates session
    2. Starts quiz
    3. Advances through questions
    4. Ends quiz
    """
    
    wait_time = between(5, 10)  # Host actions are slower
    weight = 1  # Only 1 host per test
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_token = None
        self.current_question_index = 0
    
    def on_start(self):
        """Login as host and create session"""
        # For now, we'll assume session is already created
        # In production test, you'd implement actual login + session creation
        pass
    
    @task
    def advance_question(self):
        """Advance to next question"""
        if not SESSION_ID:
            return
        
        # This would require host authentication
        # Skipping for now as it needs admin token
        pass


# Events for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("\n" + "="*60)
    print("🚀 Starting Swaya.me Load Test")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print(f"Quiz ID: {QUIZ_ID}")
    print(f"Session ID: {SESSION_ID}")
    print(f"Join Code: {JOIN_CODE}")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("\n" + "="*60)
    print("📊 Load Test Complete")
    print("="*60)
    stats = environment.stats
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.current_rps:.2f}")
    print("="*60 + "\n")
