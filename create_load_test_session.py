import requests
import os
import urllib3
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1")
EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")

def create_session():
    s = requests.Session()
    s.verify = False
    
    # 1. Login
    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    token = r.json()["access_token"]
    s.headers["Authorization"] = f"Bearer {token}"
    
    # 2. Create Proctored Quiz
    now = datetime.now(timezone.utc)
    quiz_data = {
        "title": f"Load Test Quiz {now.strftime('%Y%m%d_%H%M%S')}",
        "quiz_type": "quiz",
        "proctoring_policy": {
            "enabled": True,
            "rules": {
                "fullscreen_enforce": {"enabled": True},
                "tab_switch_detect": {"enabled": True},
                "webcam_monitoring": {"enabled": True}
            }
        }
    }
    r = s.post(f"{BASE_URL}/quizzes/", json=quiz_data)
    r.raise_for_status()
    quiz_id = r.json()["id"]
    
    # 3. Add questions
    for i in range(3):
        s.post(f"{BASE_URL}/quizzes/{quiz_id}/questions", json={
            "text": f"Load test question {i+1}?",
            "question_type": "mcq",
            "options": ["A", "B", "C", "D"],
            "correct_answer_index": 0,
            "points": 1
        }).raise_for_status()
    
    # 4. Start Session
    r = s.post(f"{BASE_URL}/quizzes/{quiz_id}/publish")
    r.raise_for_status()
    
    # Check if there are other fields needed, but the schema said only quiz_id.
    # Wait, maybe the API uses a different schema or has a bug. 
    # Let's try to just print the error if it fails again.
    try:
        r = s.post(f"{BASE_URL}/quizzes/sessions/start", params={"quiz_id": quiz_id})
        r.raise_for_status()
    except Exception as e:
        if hasattr(e, 'response'):
            print(f"ERROR BODY: {e.response.text}")
        raise
    
    session_data = r.json()
    session_id = session_data["id"]
    join_code = session_data["join_code"]
    
    # 5. Start the quiz (move to first question)
    s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance").raise_for_status()
    
    print(f"QUIZ_ID={quiz_id}")
    print(f"SESSION_ID={session_id}")
    print(f"JOIN_CODE={join_code}")

if __name__ == "__main__":
    create_session()
