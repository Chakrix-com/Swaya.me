#!/usr/bin/env python3
"""
Direct database query to check word cloud questions
"""
import sys
sys.path.insert(0, '/home/vinay/Swaya.me/backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config.settings import settings
from persistence.models.quiz import Question, Quiz

print("=" * 60)
print("Database Check: Word Cloud Questions")
print("=" * 60)

# Create engine
engine = create_engine(settings.db.url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Query all questions
    questions = db.query(Question).order_by(Question.created_at.desc()).limit(10).all()
    
    print(f"\nTotal questions in database: {db.query(Question).count()}")
    print("\nLast 10 questions:")
    print("-" * 60)
    
    word_cloud_count = 0
    mcq_count = 0
    
    for q in questions:
        qtype = q.question_type.value if hasattr(q.question_type, 'value') else q.question_type
        icon = "🌥️" if qtype == 'word_cloud' else "📝"
        
        if qtype == 'word_cloud':
            word_cloud_count += 1
        else:
            mcq_count += 1
        
        print(f"{icon} ID: {q.id} | Type: {qtype} | Quiz ID: {q.quiz_id}")
        print(f"   Text: {q.text[:50]}...")
        print(f"   Options: {q.options}")
        print(f"   Correct Index: {q.correct_answer_index}")
        print()
    
    print("-" * 60)
    print(f"MCQ Questions: {mcq_count}")
    print(f"Word Cloud Questions: {word_cloud_count}")
    
    if word_cloud_count > 0:
        print("\n✅ Word cloud questions FOUND in database!")
        
        # Get a word cloud question and check quiz relationship
        wc_question = db.query(Question).filter(
            Question.question_type == 'word_cloud'
        ).first()
        
        if wc_question:
            quiz = db.query(Quiz).filter(Quiz.id == wc_question.quiz_id).first()
            if quiz:
                print(f"\nWord cloud question belongs to quiz:")
                print(f"  Quiz ID: {quiz.id}")
                print(f"  Quiz Title: {quiz.title}")
                print(f"  Total questions in quiz: {len(quiz.questions)}")
                
                print(f"\n  Questions in quiz {quiz.id}:")
                for q in sorted(quiz.questions, key=lambda x: x.order):
                    qtype = q.question_type.value if hasattr(q.question_type, 'value') else q.question_type
                    print(f"    - Order {q.order}: [{qtype}] {q.text[:40]}...")
    else:
        print("\n❌ NO word cloud questions found in database!")
        print("   Word cloud questions are not being saved.")
    
finally:
    db.close()

print("\n" + "=" * 60)
