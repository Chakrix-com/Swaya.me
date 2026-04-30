import requests
import os
import urllib3
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1")
EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")

def start_session(quiz_id):
    s = requests.Session()
    s.verify = False
    
    # 1. Login
    r = s.post(f"{BASE_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    token = r.json()["access_token"]
    s.headers["Authorization"] = f"Bearer {token}"
    
    # 2. Start Session
    # Router prefix is /quizzes and endpoint is /sessions/start
    try:
        r = s.post(f"{BASE_URL}/quizzes/sessions/start", params={"quiz_id": int(quiz_id)})
        if r.status_code != 201:
            print(f"ERROR BODY: {r.text}")
        r.raise_for_status()
    except Exception as e:
        if hasattr(e, 'response'):
            print(f"ERROR BODY: {e.response.text}")
        raise
    
    session_data = r.json()
    session_id = session_data["id"]
    join_code = session_data["join_code"]
    
    # 3. Advance to first question to make it "live"
    s.post(f"{BASE_URL}/quizzes/sessions/{session_id}/advance").raise_for_status()
    
    print(f"QUIZ_ID={quiz_id}")
    print(f"SESSION_ID={session_id}")
    print(f"JOIN_CODE={join_code}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python start_quiz_session.py <quiz_id>")
        sys.exit(1)
    start_session(sys.argv[1])
