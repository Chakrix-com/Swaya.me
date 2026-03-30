
import requests
import os
import sys

# Ensure we can import from common/utils if needed, but we'll use requests direct
BASE_URL = os.getenv("BASE_URL", "https://test.swaya.me/api/v1")
HOST_EMAIL = os.getenv("HOST_EMAIL", "demo@swaya.me")
HOST_PASSWORD = os.getenv("HOST_PASSWORD", "Demo1234")

def get_token():
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": HOST_EMAIL,
        "password": HOST_PASSWORD
    })
    resp.raise_for_status()
    return resp.json()["access_token"]

def test_quiz_type_persistence():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create a quiz as 'exam' (Test)
    print("Step 1: Creating a quiz with type='exam'...")
    create_payload = {
        "title": "Regression Persistence Test (Exam)",
        "quiz_type": "exam"
    }
    resp = requests.post(f"{BASE_URL}/quizzes/", json=create_payload, headers=headers)
    resp.raise_for_status()
    quiz = resp.json()
    quiz_id = quiz["id"]
    
    assert quiz["quiz_type"] == "exam", f"Expected exam, got {quiz['quiz_type']}"
    print(f"✓ Created as {quiz['quiz_type']}")

    # 2. Update the quiz (e.g. change title) and verify type remains 'exam'
    print("Step 2: Updating quiz title and verifying type persistence...")
    update_payload = {
        "title": "UPDATED Regression Persistence Test (Exam)"
    }
    resp = requests.put(f"{BASE_URL}/quizzes/{quiz_id}", json=update_payload, headers=headers)
    resp.raise_for_status()
    updated_quiz = resp.json()
    
    assert updated_quiz["quiz_type"] == "exam", f"Type changed to {updated_quiz['quiz_type']} after update!"
    print(f"✓ Type persisted as {updated_quiz['quiz_type']} after update")

    # 3. Explicitly send 'quiz' in update and verify it changes to 'quiz'
    print("Step 3: Explicitly changing type to 'quiz'...")
    update_type_payload = {
        "quiz_type": "quiz"
    }
    resp = requests.put(f"{BASE_URL}/quizzes/{quiz_id}", json=update_type_payload, headers=headers)
    resp.raise_for_status()
    quiz_changed = resp.json()
    
    assert quiz_changed["quiz_type"] == "quiz", f"Failed to change type to quiz"
    print(f"✓ Type changed to {quiz_changed['quiz_type']}")

    # 4. Change back to 'exam'
    print("Step 4: Changing back to 'exam'...")
    update_back_payload = {
        "quiz_type": "exam"
    }
    resp = requests.put(f"{BASE_URL}/quizzes/{quiz_id}", json=update_back_payload, headers=headers)
    resp.raise_for_status()
    final_quiz = resp.json()
    
    assert final_quiz["quiz_type"] == "exam", "Failed to change back to exam"
    print(f"✓ Type reverted to {final_quiz['quiz_type']}")

    # Cleanup
    requests.delete(f"{BASE_URL}/quizzes/{quiz_id}", headers=headers)
    print("✓ Cleanup done")

if __name__ == "__main__":
    try:
        test_quiz_type_persistence()
        print("\nSUMMARY: Quiz Type Persistence Regression PASSED")
    except Exception as e:
        print(f"\nSUMMARY: Quiz Type Persistence Regression FAILED: {str(e)}")
        sys.exit(1)
