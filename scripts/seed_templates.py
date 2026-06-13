"""Seed 10 global templates across classroom / all-hands / training / hiring verticals."""
import sys, os
BACKEND = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from persistence.models.quiz import Quiz, QuizStatus, QuizType, TemplateScope
from persistence.models.quiz import Question
from persistence.models.core import Event, Tenant, User
from core.config.settings import settings

db_cfg = settings.db
DATABASE_URL = f"mysql+asyncmy://{db_cfg.user}:{db_cfg.password}@{db_cfg.host}:{db_cfg.port}/{db_cfg.name}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Super-admin lives in tenant_id=2 on the test DB
SUPER_ADMIN_TENANT_ID = 2

TEMPLATES = [
    # Classroom vertical
    {
        'title': 'Photosynthesis — Class 9 Science',
        'description': '10 MCQs on photosynthesis covering light reactions, Calvin cycle, and chloroplasts.',
        'quiz_type': QuizType.QUIZ,
        'category': 'classroom',
        'questions': [
            ('What is the primary pigment responsible for photosynthesis?', ['Chlorophyll', 'Carotenoid', 'Xanthophyll', 'Phycocyanin'], 0),
            ('Where does the light-dependent reaction occur?', ['Thylakoid membrane', 'Stroma', 'Cytoplasm', 'Mitochondria'], 0),
            ('What gas is produced as a by-product of photosynthesis?', ['Oxygen', 'Carbon dioxide', 'Nitrogen', 'Hydrogen'], 0),
            ('Which molecule carries energy in the cell?', ['ATP', 'DNA', 'RNA', 'Glucose'], 0),
            ('The Calvin cycle is also known as:', ['Dark reaction', 'Light reaction', 'Krebs cycle', 'Glycolysis'], 0),
            ('What is the role of NADPH in photosynthesis?', ['Electron carrier', 'Enzyme', 'Pigment', 'Hormone'], 0),
            ('Stomata help in:', ['Gas exchange', 'Photosynthesis only', 'Respiration only', 'Water absorption'], 0),
            ('Chloroplasts are found in:', ['Plant cells only', 'Animal cells only', 'Both', 'Neither'], 0),
            ('How many ATP molecules are produced per glucose in photosynthesis?', ['0', '2', '36', '38'], 0),
            ('The equation for photosynthesis is:', ['6CO₂+6H₂O→C₆H₁₂O₆+6O₂', 'C₆H₁₂O₆+6O₂→6CO₂+6H₂O', '6O₂+6H₂O→6CO₂+C₆H₁₂O₆', 'H₂O+CO₂→O₂'], 0),
        ],
    },
    {
        'title': 'World Capitals Quiz',
        'description': '8 questions about world capitals — a fun geography warm-up for any age group.',
        'quiz_type': QuizType.QUIZ,
        'category': 'classroom',
        'questions': [
            ('What is the capital of Australia?', ['Canberra', 'Sydney', 'Melbourne', 'Brisbane'], 0),
            ('Capital of Brazil?', ['Brasília', 'São Paulo', 'Rio de Janeiro', 'Salvador'], 0),
            ('Capital of Canada?', ['Ottawa', 'Toronto', 'Vancouver', 'Montreal'], 0),
            ('Capital of Japan?', ['Tokyo', 'Osaka', 'Kyoto', 'Hiroshima'], 0),
            ('Capital of Germany?', ['Berlin', 'Munich', 'Frankfurt', 'Hamburg'], 0),
            ('Capital of South Africa?', ['Pretoria', 'Cape Town', 'Johannesburg', 'Durban'], 0),
            ('Capital of India?', ['New Delhi', 'Mumbai', 'Kolkata', 'Chennai'], 0),
            ('Capital of Egypt?', ['Cairo', 'Alexandria', 'Luxor', 'Giza'], 0),
        ],
    },
    # All-hands vertical
    {
        'title': 'Company Values Check-In',
        'description': 'A live poll to pulse-check how well the team embodies company values — great for all-hands.',
        'quiz_type': QuizType.POLL,
        'category': 'all-hands',
        'questions': [
            ('How well does our team demonstrate "Customer First" this quarter?', ['Very well', 'Well', 'Needs improvement', 'Not sure'], 0),
            ('Which value do you feel we live best?', ['Integrity', 'Innovation', 'Collaboration', 'Excellence'], 0),
            ('How connected do you feel to the company mission?', ['Very connected', 'Somewhat connected', 'Not very connected', 'Unsure'], 0),
            ('What would most improve team culture?', ['More recognition', 'Clearer goals', 'Better communication', 'More autonomy'], 0),
        ],
    },
    {
        'title': 'Product Roadmap Feedback',
        'description': 'Gather anonymous team input on the upcoming roadmap priorities.',
        'quiz_type': QuizType.POLL,
        'category': 'all-hands',
        'questions': [
            ('Which feature should we prioritize next quarter?', ['Mobile app', 'API integrations', 'Analytics dashboard', 'Performance improvements'], 0),
            ('How satisfied are you with our current release cadence?', ['Very satisfied', 'Satisfied', 'Neutral', 'Unsatisfied'], 0),
            ('What is the biggest blocker to shipping faster?', ['Technical debt', 'Resource constraints', 'Unclear requirements', 'Process overhead'], 0),
        ],
    },
    # Training vertical
    {
        'title': 'Python Basics — L1 Training',
        'description': 'Entry-level Python assessment for onboarding or L1 certification.',
        'quiz_type': QuizType.EXAM,
        'category': 'training',
        'questions': [
            ('Which keyword defines a function in Python?', ['def', 'func', 'function', 'define'], 0),
            ('What does len([1,2,3]) return?', ['3', '2', '1', '0'], 0),
            ('How do you create a list in Python?', ['[]', '{}', '()', '<>'], 0),
            ('Which operator is used for integer division?', ['//', '/', '%', '**'], 0),
            ('What is the output of print(type(3.14))?', ["<class 'float'>", "<class 'int'>", "<class 'str'>", "float"], 0),
            ('How do you add an element to a list?', ['list.append(x)', 'list.add(x)', 'list.insert(x)', 'list.push(x)'], 0),
            ('Which is used for exception handling?', ['try/except', 'catch/throw', 'begin/rescue', 'if/else'], 0),
            ('Python is:', ['Interpreted', 'Compiled only', 'Neither', 'Both interpreted and compiled always'], 0),
        ],
    },
    {
        'title': 'Data Privacy & GDPR Awareness',
        'description': 'Compliance training quiz on data privacy principles and GDPR basics.',
        'quiz_type': QuizType.EXAM,
        'category': 'training',
        'questions': [
            ('What does GDPR stand for?', ['General Data Protection Regulation', 'Global Data Privacy Rules', 'Government Data Privacy Regulation', 'General Digital Privacy Rules'], 0),
            ('Under GDPR, personal data must be:', ['Stored only as long as necessary', 'Stored indefinitely', 'Always anonymised', 'Never collected'], 0),
            ('A data breach must be reported to authorities within:', ['72 hours', '24 hours', '7 days', '30 days'], 0),
            ('What is a "data subject" under GDPR?', ['An identified or identifiable natural person', 'Any company that holds data', 'A government body', 'A database server'], 0),
            ('Which legal basis is NOT valid for processing personal data?', ['Revenue generation', 'Consent', 'Legal obligation', 'Legitimate interest'], 0),
            ('What right allows a person to request deletion of their data?', ['Right to erasure', 'Right to access', 'Right to portability', 'Right to object'], 0),
        ],
    },
    # Hiring vertical
    {
        'title': 'SQL Screening — Data Analyst',
        'description': 'Quick SQL skills screen for data analyst candidates.',
        'quiz_type': QuizType.EXAM,
        'category': 'hiring',
        'questions': [
            ('Which SQL clause filters rows after grouping?', ['HAVING', 'WHERE', 'FILTER', 'GROUP BY'], 0),
            ('What does SELECT DISTINCT do?', ['Returns unique rows', 'Selects all rows', 'Sorts results', 'Joins tables'], 0),
            ('Which join returns all rows from both tables?', ['FULL OUTER JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN'], 0),
            ('What is the correct order of SQL clauses?', ['SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY', 'FROM → WHERE → SELECT → GROUP BY', 'WHERE → FROM → SELECT', 'SELECT → WHERE → FROM'], 0),
            ('Which aggregate function counts non-NULL values?', ['COUNT(column)', 'COUNT(*)', 'SUM(column)', 'AVG(column)'], 0),
            ('What does a subquery in the FROM clause produce?', ['A derived table', 'A view', 'An index', 'A constraint'], 0),
        ],
    },
    {
        'title': 'Problem-Solving Style (Ice-breaker)',
        'description': 'A fun live poll to understand candidate or new-hire work styles — use in interviews or onboarding.',
        'quiz_type': QuizType.POLL,
        'category': 'hiring',
        'questions': [
            ('When facing a complex problem, you prefer to:', ['Break it into small pieces', 'Tackle the hardest part first', 'Research extensively before starting', 'Collaborate immediately'], 0),
            ('Your ideal work environment is:', ['Deep focus, minimal interruptions', 'Collaborative and open', 'Flexible — varies by task', 'Remote and async'], 0),
            ('When you receive critical feedback, you:', ['Reflect and iterate', 'Seek clarification first', 'Take action immediately', 'Discuss with peers'], 0),
        ],
    },
    # General
    {
        'title': 'Tech Trivia — Team Energiser',
        'description': '8 fun technology questions for a team warm-up or icebreaker.',
        'quiz_type': QuizType.QUIZ,
        'category': 'general',
        'questions': [
            ('Who co-founded Apple in 1976?', ['Steve Jobs & Steve Wozniak', 'Bill Gates & Paul Allen', 'Larry Page & Sergey Brin', 'Mark Zuckerberg & Eduardo Saverin'], 0),
            ('What does "HTTP" stand for?', ['HyperText Transfer Protocol', 'High Transfer Text Protocol', 'Hyper Transfer Text Process', 'HyperText Transport Program'], 0),
            ('Which company created the Python programming language?', ['Guido van Rossum (individual)', 'Google', 'Microsoft', 'Apple'], 0),
            ('What year was the first iPhone released?', ['2007', '2005', '2008', '2010'], 0),
            ('Git was created by:', ['Linus Torvalds', 'Dennis Ritchie', 'James Gosling', 'Bjarne Stroustrup'], 0),
            ('Which protocol is used for secure web browsing?', ['HTTPS', 'HTTP', 'FTP', 'SSH'], 0),
            ('What does "AI" stand for?', ['Artificial Intelligence', 'Automated Intelligence', 'Advanced Integration', 'Algorithmic Input'], 0),
            ('The "cloud" in cloud computing refers to:', ['Remote servers on the internet', 'Actual clouds in the sky', 'Local network storage', 'A type of database'], 0),
        ],
    },
    {
        'title': 'Meeting Effectiveness Poll',
        'description': 'Quick pulse poll to measure meeting culture — use after any company-wide meeting.',
        'quiz_type': QuizType.POLL,
        'category': 'general',
        'questions': [
            ('How would you rate today\'s meeting?', ['Excellent — very productive', 'Good', 'Average', 'Could have been an email'], 0),
            ('Did the meeting have a clear agenda?', ['Yes, fully', 'Somewhat', 'Not really', 'No agenda at all'], 0),
            ('Will you leave with clear action items?', ['Yes, very clear', 'Mostly yes', 'Uncertain', 'No'], 0),
        ],
    },
]


async def main():
    async with AsyncSessionLocal() as db:
        # Get super-admin user
        result = await db.execute(select(User).filter(User.tenant_id == SUPER_ADMIN_TENANT_ID, User.role == 'super_admin').limit(1))
        admin = result.scalar_one_or_none()
        if not admin:
            print('No super_admin found in tenant 1')
            return

        # Check existing global templates to avoid duplicates
        result = await db.execute(
            select(Quiz).filter(Quiz.is_template == True, Quiz.template_scope == TemplateScope.GLOBAL)
        )
        existing = {q.title for q in result.scalars().all()}
        print(f'Existing global templates: {len(existing)}')

        created = 0
        for tmpl in TEMPLATES:
            if tmpl['title'] in existing:
                print(f'  SKIP (exists): {tmpl["title"]}')
                continue

            event = Event(
                tenant_id=SUPER_ADMIN_TENANT_ID,
                creator_id=admin.id,
                title=f"Template Event - {tmpl['title']}",
                description=None,
                join_code=None,
            )
            db.add(event)
            await db.flush()

            quiz = Quiz(
                tenant_id=SUPER_ADMIN_TENANT_ID,
                event_id=event.id,
                title=tmpl['title'],
                description=tmpl['description'],
                quiz_type=tmpl['quiz_type'],
                status=QuizStatus.READY,
                is_template=True,
                template_scope=TemplateScope.GLOBAL,
                template_category=tmpl['category'],
                template_use_count=0,
            )
            db.add(quiz)
            await db.flush()

            for i, (text, options, correct) in enumerate(tmpl['questions']):
                db.add(Question(
                    quiz_id=quiz.id,
                    question_type='mcq',
                    text=text,
                    order=i,
                    options=options,
                    correct_answer_index=correct,
                    points=100,
                    max_time_seconds=30,
                ))

            created += 1
            print(f'  CREATED [{tmpl["category"]}]: {tmpl["title"]} ({len(tmpl["questions"])} questions)')

        await db.commit()
        print(f'\nDone. Created {created} new templates.')


if __name__ == '__main__':
    asyncio.run(main())
