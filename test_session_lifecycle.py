#!/usr/bin/env python3
"""
Test session lifecycle to ensure demo can run repeatedly
Tests: Start → Advance → Answer → End → Start Again
"""
import requests
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.swaya.me/api/v1"

def print_step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")

def test_full_lifecycle():
    """Test complete session lifecycle multiple times"""
    
    print_step("LOGGING IN")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "demo@swaya.me", "password": "Demo1234"},
        verify=False
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Logged in successfully")
    
    # Get quiz
    response = requests.get(f"{BASE_URL}/quizzes/", headers=headers, verify=False)
    quiz_id = response.json()[0]["id"]
    print(f"✅ Found quiz ID: {quiz_id}")
    
    # Run 3 complete cycles
    for cycle in range(1, 4):
        print_step(f"CYCLE {cycle}: Full Session Lifecycle")
        
        # 1. Start session
        print(f"\n{cycle}.1 Starting session...")
        response = requests.post(
            f"{BASE_URL}/quizzes/sessions/start?quiz_id={quiz_id}",
            headers=headers,
            verify=False
        )
        assert response.status_code in [200, 201], f"Failed to start: {response.status_code}"
        session = response.json()
        session_id = session["id"]
        join_code = session["join_code"]
        print(f"    ✅ Session {session_id} started (code: {join_code})")
        
        # 2. Advance to question
        print(f"\n{cycle}.2 Advancing to question...")
        response = requests.post(
            f"{BASE_URL}/quizzes/sessions/{session_id}/advance",
            headers=headers,
            verify=False
        )
        assert response.status_code == 200, f"Failed to advance: {response.status_code}"
        print(f"    ✅ Advanced to question")
        
        # 3. Participant joins
        print(f"\n{cycle}.3 Participant joining...")
        response = requests.post(
            f"{BASE_URL}/quizzes/sessions/join",
            json={"join_code": join_code, "display_name": f"Tester {cycle}"},
            verify=False
        )
        assert response.status_code == 200, f"Join failed: {response.status_code}"
        participant_token = response.json()["session_token"]
        print(f"    ✅ Participant joined")
        
        # 4. Submit answer
        print(f"\n{cycle}.4 Submitting answer...")
        response = requests.get(
            f"{BASE_URL}/quizzes/sessions/{session_id}/results",
            params={"session_token": participant_token},
            verify=False
        )
        question_id = response.json()["current_question"]["id"]
        
        response = requests.post(
            f"{BASE_URL}/quizzes/sessions/submit-answer",
            params={"session_token": participant_token},
            json={"question_id": question_id, "selected_option_index": cycle % 4},
            verify=False
        )
        assert response.status_code == 200, f"Submit failed: {response.status_code}"
        print(f"    ✅ Answer submitted")
        
        # 5. Verify host sees answer
        print(f"\n{cycle}.5 Verifying host sees answer...")
        time.sleep(1)
        response = requests.get(
            f"{BASE_URL}/quizzes/sessions/{session_id}/results",
            headers=headers,
            verify=False
        )
        results = response.json()
        assert results["total_participants"] == 1, "Participant count wrong"
        assert results["current_question"]["total_answers"] == 1, "Answer not recorded"
        print(f"    ✅ Host sees 1 participant and 1 answer")
        
        # 6. End session
        print(f"\n{cycle}.6 Ending session...")
        response = requests.post(
            f"{BASE_URL}/quizzes/sessions/{session_id}/end",
            headers=headers,
            verify=False
        )
        assert response.status_code == 200, f"End failed: {response.status_code}"
        print(f"    ✅ Session ended")
        
        # 7. Verify session is ended
        print(f"\n{cycle}.7 Verifying session status...")
        response = requests.get(
            f"{BASE_URL}/quizzes/sessions/{session_id}/results",
            headers=headers,
            verify=False
        )
        final_status = response.json()["status"]
        assert final_status == "ended", f"Status should be 'ended', got '{final_status}'"
        print(f"    ✅ Session status: {final_status}")
        
        print(f"\n✅ CYCLE {cycle} COMPLETED SUCCESSFULLY\n")
    
    print_step("🎉 ALL TESTS PASSED!")
    print("""
✅ Session lifecycle works correctly
✅ Can start multiple sessions on same quiz
✅ Each session maintains independent state
✅ Participants can join each session
✅ Answers are tracked correctly
✅ Sessions can be ended cleanly
✅ Demo can run repeatedly without issues

The demo is ready for continuous use!
    """)
    return True

if __name__ == "__main__":
    try:
        test_full_lifecycle()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
