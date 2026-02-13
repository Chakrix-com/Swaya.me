#!/usr/bin/env python3
"""
Test script to verify question creation and display flow
"""
import requests
import json
import sys

API_BASE_URL = 'http://localhost:8000/api/v1'

def test_flow():
    print("=" * 80)
    print("Testing Complete Quiz & Question Flow")
    print("=" * 80)
    
    # Step 1: Login
    print("\n[1/6] Logging in...")
    login_response = requests.post(
        f'{API_BASE_URL}/auth/login',
        json={'email': 'demo@swaya.me', 'password': 'Demo1234'}
    )
    if login_response.status_code != 200:
        print(f"  ❌ Login failed: {login_response.text}")
        return False
    
    token = login_response.json()['access_token']
    print(f"  ✓ Logged in successfully. Token: {token[:20]}...")
    headers = {'Authorization': f'Bearer {token}'}
    
    # Step 2: Create a new quiz
    print("\n[2/6] Creating a new quiz...")
    quiz_data = {
        'title': 'Test Quiz - ' + str(int(__import__('time').time())),
        'description': 'This is a test quiz for question display'
    }
    quiz_response = requests.post(
        f'{API_BASE_URL}/quizzes/',
        json=quiz_data,
        headers=headers
    )
    if quiz_response.status_code != 201:
        print(f"  ❌ Quiz creation failed: {quiz_response.text}")
        return False
    
    quiz = quiz_response.json()
    quiz_id = quiz['id']
    print(f"  ✓ Quiz created. ID: {quiz_id}, Title: {quiz['title']}")
    
    # Step 3: Add a question
    print("\n[3/6] Adding a question...")
    question_data = {
        'text': 'What is the capital of France?',
        'options': ['London', 'Paris', 'Berlin', 'Madrid'],
        'correct_answer_index': 1
    }
    question_response = requests.post(
        f'{API_BASE_URL}/quizzes/{quiz_id}/questions',
        json=question_data,
        headers=headers
    )
    if question_response.status_code != 201:
        print(f"  ❌ Question creation failed: {question_response.text}")
        return False
    
    question = question_response.json()
    question_id = question['id']
    print(f"  ✓ Question added. ID: {question_id}, Text: {question['text']}")
    
    # Step 4: Fetch the quiz and verify questions are returned
    print("\n[4/6] Fetching quiz details to verify questions...")
    get_response = requests.get(
        f'{API_BASE_URL}/quizzes/{quiz_id}',
        headers=headers
    )
    if get_response.status_code != 200:
        print(f"  ❌ Get quiz failed: {get_response.text}")
        return False
    
    fetched_quiz = get_response.json()
    print(f"  ✓ Quiz fetched successfully")
    print(f"    - Quiz ID: {fetched_quiz['id']}")
    print(f"    - Title: {fetched_quiz['title']}")
    print(f"    - Status: {fetched_quiz['status']}")
    print(f"    - Question count: {fetched_quiz['question_count']}")
    
    # Step 5: Verify questions array contains our question
    print("\n[5/6] Verifying questions array...")
    questions = fetched_quiz.get('questions', [])
    if not questions:
        print(f"  ❌ Questions array is empty!")
        print(f"    Full response: {json.dumps(fetched_quiz, indent=2)}")
        return False
    
    print(f"  ✓ Questions array contains {len(questions)} question(s)")
    for i, q in enumerate(questions):
        print(f"    - Question {i+1}:")
        print(f"      ID: {q['id']}")
        print(f"      Text: {q['text']}")
        print(f"      Options: {q['options']}")
        print(f"      Correct Answer Index: {q['correct_answer_index']}")
        print(f"      Order: {q['order']}")
    
    # Step 6: Verify transformation logic
    print("\n[6/6] Simulating frontend transformation...")
    for q in questions:
        transformed = {
            'id': q['id'],
            'text': q['text'],
            'option_a': q['options'][0],
            'option_b': q['options'][1],
            'option_c': q['options'][2],
            'option_d': q['options'][3],
            'correct_answer': ['A', 'B', 'C', 'D'][q['correct_answer_index']],
            'order': q['order']
        }
        print(f"  ✓ Transformed question {q['id']}:")
        print(f"    {json.dumps(transformed, indent=6)}")
    
    print("\n" + "=" * 80)
    print("✓ All tests passed! Questions are properly created and returned.")
    print("=" * 80)
    return True

if __name__ == '__main__':
    try:
        success = test_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
