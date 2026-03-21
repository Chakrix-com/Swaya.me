#!/usr/bin/env python3
"""
Test script to debug word cloud question creation
"""
import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from features.quiz.schemas import QuestionCreate, QuestionTypeEnum
from pydantic import ValidationError
import json

print("=" * 60)
print("Testing Word Cloud Question Creation")
print("=" * 60)

# Test 1: Create MCQ question (should work)
print("\n1. Testing MCQ question creation...")
try:
    mcq_data = {
        "question_type": "mcq",
        "text": "What is 2+2?",
        "options": ["1", "2", "3", "4"],
        "correct_answer_index": 3
    }
    mcq_question = QuestionCreate(**mcq_data)
    print("✅ MCQ question created successfully")
    print(f"   Data: {mcq_question.model_dump()}")
except ValidationError as e:
    print(f"❌ MCQ question failed: {e}")

# Test 2: Create word cloud question (should work)
print("\n2. Testing word cloud question creation...")
try:
    wc_data = {
        "question_type": "word_cloud",
        "text": "What is your favorite color?"
    }
    wc_question = QuestionCreate(**wc_data)
    print("✅ Word cloud question created successfully")
    print(f"   Data: {wc_question.model_dump()}")
except ValidationError as e:
    print(f"❌ Word cloud question failed:")
    print(f"   {json.dumps(json.loads(e.json()), indent=2)}")

# Test 3: Word cloud with options (should fail)
print("\n3. Testing word cloud with options (should fail)...")
try:
    wc_bad_data = {
        "question_type": "word_cloud",
        "text": "What is your favorite color?",
        "options": ["Red", "Blue", "Green", "Yellow"]
    }
    wc_bad_question = QuestionCreate(**wc_bad_data)
    print("❌ Should have failed but didn't!")
except ValidationError as e:
    print("✅ Correctly rejected (as expected)")
    print(f"   Error: {e.errors()[0]['msg']}")

# Test 4: MCQ without options (should fail)
print("\n4. Testing MCQ without options (should fail)...")
try:
    mcq_bad_data = {
        "question_type": "mcq",
        "text": "What is 2+2?"
    }
    mcq_bad_question = QuestionCreate(**mcq_bad_data)
    print("❌ Should have failed but didn't!")
except ValidationError as e:
    print("✅ Correctly rejected (as expected)")
    print(f"   Error: {e.errors()[0]['msg']}")

# Test 5: Simulate frontend payload
print("\n5. Testing frontend payload format...")
try:
    frontend_data = {
        "question_type": "word_cloud",
        "text": "Describe this session in one word"
    }
    frontend_question = QuestionCreate(**frontend_data)
    print("✅ Frontend payload works")
    print(f"   Will send to backend: {frontend_question.model_dump(exclude_none=True)}")
except ValidationError as e:
    print(f"❌ Frontend payload failed:")
    print(f"   {json.dumps(json.loads(e.json()), indent=2)}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
