import asyncio
import os
import sys

# Add backend to path for imports
sys.path.append(os.path.join(os.getcwd(), "backend"))

from persistence.database_async import AsyncSessionLocal
from persistence.models.quiz import Quiz
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Quiz).order_by(Quiz.id.desc()).limit(10))
        quizzes = res.scalars().all()
        print(f"{'ID':<5} | {'Type':<12} | {'Title'}")
        print("-" * 40)
        for q in quizzes:
            print(f"{q.id:<5} | {q.quiz_type.value if hasattr(q.quiz_type, 'value') else q.quiz_type:<12} | {q.title}")

if __name__ == "__main__":
    asyncio.run(run())
