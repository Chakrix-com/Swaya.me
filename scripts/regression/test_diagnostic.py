#!/usr/bin/env python3
"""
Comprehensive diagnostic test for Swaya.me
Tests both host and viewer flows with detailed output
"""
import requests
import json
import time
import sys

BASE_URL = "https://www.swaya.me"
API_BASE = f"{BASE_URL}/api/v1"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_step(msg):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"📝 {msg}")
    print(f"{'='*60}{Colors.END}")

def log_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def log_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def log_info(msg):
    print(f"{Colors.YELLOW}ℹ️  {msg}{Colors.END}")

def test_complete_flow():
    """Test complete quiz flow"""
    
    log_step("STEP 1: Host Login")
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": "demo@swaya.me", "password": "Demo1234"},
        verify=False
    )
    
    if response.status_code != 200:
        log_error(f"Login failed: {response.status_code}")
        return False
    
    token = response.json()["access_token"]
    log_success(f"Host logged in successfully")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get quiz
    log_step("STEP 2: Get Quiz")
    response = requests.get(f"{API_BASE}/quizzes/", headers=headers, verify=False)
    quizzes = response.json()
    quiz_id = quizzes[0]["id"]
    log_success(f"Found quiz ID: {quiz_id}")
    
    # Start session
    log_step("STEP 3: Start Session")
    response = requests.post(
        f"{API_BASE}/quizzes/sessions/start?quiz_id={quiz_id}",
        headers=headers,
        verify=False
    )
    session_data = response.json()
    session_id = session_data["id"]
    join_code = session_data["join_code"]
    log_success(f"Session started: ID={session_id}, Join Code={join_code}")
    
    # Advance to question
    log_step("STEP 4: Advance to First Question")
    response = requests.post(
        f"{API_BASE}/quizzes/sessions/{session_id}/advance",
        headers=headers,
        verify=False
    )
    log_success("Advanced to question 1")
    
    # Check host results BEFORE participant joins
    log_step("STEP 5: Check Host Results (Before Participant)")
    response = requests.get(
        f"{API_BASE}/quizzes/sessions/{session_id}/results",
        headers=headers,
        verify=False
    )
    results = response.json()
    log_info(f"Status: {results['status']}")
    log_info(f"Current Question Index: {results['current_question_index']}")
    log_info(f"Total Answers: {results['current_question']['total_answers']}")
    log_info(f"Distribution: {results['current_question']['answer_distribution']}")
    
    # Participant joins
    log_step("STEP 6: Participant Joins")
    response = requests.post(
        f"{API_BASE}/quizzes/sessions/join",
        json={"join_code": join_code, "display_name": "Test User"},
        verify=False
    )
    participant_data = response.json()
    participant_token = participant_data["session_token"]
    participant_session_id = participant_data["session_id"]
    log_success(f"Participant joined session {participant_session_id}")
    
    # Participant gets question
    log_step("STEP 7: Participant Gets Question")
    response = requests.get(
        f"{API_BASE}/quizzes/sessions/{participant_session_id}/results",
        params={"session_token": participant_token},
        verify=False
    )
    participant_results = response.json()
    
    if not participant_results.get("current_question"):
        log_error("Participant cannot see question!")
        log_info(f"Response: {json.dumps(participant_results, indent=2)}")
        return False
    
    question = participant_results["current_question"]
    question_id = question["id"]
    log_success(f"Participant sees question: '{question['text']}'")
    log_info(f"Question ID: {question_id}")
    log_info(f"Options: A={question['option_a']}, B={question['option_b']}, C={question['option_c']}, D={question['option_d']}")
    
    # Participant submits answer
    log_step("STEP 8: Participant Submits Answer (A = Index 0)")
    response = requests.post(
        f"{API_BASE}/quizzes/sessions/submit-answer",
        params={"session_token": participant_token},
        json={"question_id": question_id, "selected_option_index": 0},
        verify=False
    )
    
    if response.status_code != 200:
        log_error(f"Answer submission failed: {response.status_code}")
        log_info(f"Response: {response.text}")
        return False
    
    submit_response = response.json()
    log_success(f"Answer submitted: {submit_response}")
    
    # Wait a moment for aggregation
    time.sleep(2)
    
    # Check host results AFTER answer
    log_step("STEP 9: Check Host Results (After Answer)")
    response = requests.get(
        f"{API_BASE}/quizzes/sessions/{session_id}/results",
        headers=headers,
        verify=False
    )
    results_after = response.json()
    
    print(f"\n{Colors.YELLOW}HOST RESULTS DETAILS:{Colors.END}")
    current_q = results_after['current_question']
    print(json.dumps({
        "total_answers": current_q['total_answers'],
        "answer_distribution": current_q['answer_distribution'],
        "question_text": current_q['question_text'],
        "correct_answer": current_q['correct_answer'],
        "correct_answer_index": current_q['correct_answer_index']
    }, indent=2))
    
    total_answers = current_q['total_answers']
    if total_answers == 0:
        log_error(f"HOST STILL SHOWS 0 ANSWERS! Expected 1.")
        log_error("This indicates a problem with answer aggregation or API data format")
        return False
    elif total_answers == 1:
        log_success(f"HOST CORRECTLY SHOWS 1 ANSWER!")
        distribution = current_q['answer_distribution']
        log_success(f"Distribution: A={distribution[0]}, B={distribution[1]}, C={distribution[2]}, D={distribution[3]}")
        
        if distribution[0] == 1:
            log_success("Answer correctly recorded for option A!")
        else:
            log_error(f"Answer distribution wrong! Expected [1,0,0,0], got {distribution}")
            return False
    
    # Check participant results
    log_step("STEP 10: Check Participant Results (After Submit)")
    response = requests.get(
        f"{API_BASE}/quizzes/sessions/{participant_session_id}/results",
        params={"session_token": participant_token},
        verify=False
    )
    participant_results_after = response.json()
    
    print(f"\n{Colors.YELLOW}PARTICIPANT VIEW DETAILS:{Colors.END}")
    part_q = participant_results_after['current_question']
    print(json.dumps({
        "total_answers": part_q['total_answers'],
        "answer_distribution": part_q['answer_distribution'],
        "participant_answer": part_q.get('participant_answer'),
    }, indent=2))
    
    log_step("FINAL VERIFICATION")
    
    # Verify everything
    checks = [
        ("Session created", session_id is not None),
        ("Question advanced", results['current_question_index'] == 0),
        ("Participant joined", participant_session_id == session_id),
        ("Participant sees question", question_id is not None),
        ("Answer submitted", submit_response.get('success') == True),
        ("Host sees 1 answer", total_answers == 1),
        ("Distribution correct", distribution[0] == 1),
    ]
    
    all_passed = True
    for check_name, result in checks:
        if result:
            log_success(check_name)
        else:
            log_error(check_name)
            all_passed = False
    
    if all_passed:
        print(f"\n{Colors.GREEN}{'='*60}")
        print("🎉 ALL TESTS PASSED - QUIZ FLOW WORKING PERFECTLY!")
        print(f"{'='*60}{Colors.END}\n")
        return True
    else:
        print(f"\n{Colors.RED}{'='*60}")
        print("❌ SOME TESTS FAILED - SEE DETAILS ABOVE")
        print(f"{'='*60}{Colors.END}\n")
        return False

if __name__ == "__main__":
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    success = test_complete_flow()
    sys.exit(0 if success else 1)
