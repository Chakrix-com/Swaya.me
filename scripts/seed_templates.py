"""Seed global templates across all categories and quiz types."""
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

TEMPLATES = [
    # ── CLASSROOM ─────────────────────────────────────────────────────────────
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
    {
        'title': 'World War II — Key Events',
        'description': '8 questions on major WWII events, leaders, and turning points — suitable for Class 9–12.',
        'quiz_type': QuizType.QUIZ,
        'category': 'classroom',
        'questions': [
            ('In which year did World War II begin?', ['1939', '1941', '1937', '1945'], 0),
            ('Which event brought the USA into WWII?', ['Attack on Pearl Harbor', 'Fall of France', 'Battle of Britain', 'D-Day'], 0),
            ('The D-Day landings took place on which beach?', ['Normandy', 'Dunkirk', 'Gallipoli', 'Omaha only'], 0),
            ('Who was the Prime Minister of Britain during most of WWII?', ['Winston Churchill', 'Neville Chamberlain', 'Clement Attlee', 'Anthony Eden'], 0),
            ('The Battle of Stalingrad was a turning point for which front?', ['Eastern Front', 'Western Front', 'Pacific Front', 'North African Front'], 0),
            ('Which two Japanese cities were hit by atomic bombs?', ['Hiroshima & Nagasaki', 'Tokyo & Osaka', 'Kyoto & Hiroshima', 'Nagasaki & Tokyo'], 0),
            ('The Holocaust was the genocide of primarily which group?', ['Jewish people', 'Romani people', 'Soviet civilians', 'Polish Catholics'], 0),
            ('WWII officially ended in Europe on what date?', ['8 May 1945', '2 September 1945', '6 June 1944', '1 September 1939'], 0),
        ],
    },
    {
        'title': 'Class 10 Algebra Basics',
        'description': 'Assess foundational algebra skills — linear equations, quadratics, and factorisation.',
        'quiz_type': QuizType.EXAM,
        'category': 'classroom',
        'questions': [
            ('Solve: 2x + 5 = 13. What is x?', ['4', '3', '6', '9'], 0),
            ('Which is the correct factorisation of x² − 9?', ['(x+3)(x−3)', '(x−3)²', '(x+3)²', '(x+9)(x−1)'], 0),
            ('What is the degree of the polynomial 3x³ + 2x − 7?', ['3', '2', '1', '0'], 0),
            ('If y = 2x + 4, what is y when x = −1?', ['2', '−2', '6', '0'], 0),
            ('Which value of x satisfies x² = 25?', ['±5', '5 only', '−5 only', '±25'], 0),
            ('Simplify: (3x²)(4x³)', ['12x⁵', '12x⁶', '7x⁵', '7x⁶'], 0),
            ('What is the slope of y = 3x − 7?', ['3', '−7', '7', '−3'], 0),
            ('Expand: (x + 2)²', ['x² + 4x + 4', 'x² + 4', 'x² + 2x + 4', 'x² + 2x + 2'], 0),
        ],
    },
    {
        'title': 'English Reading Comprehension',
        'description': '6 questions testing inference, vocabulary, and understanding from short prose passages.',
        'quiz_type': QuizType.EXAM,
        'category': 'classroom',
        'questions': [
            ('The author\'s primary purpose in the passage is to:', ['Inform the reader about a topic', 'Entertain with a fictional story', 'Persuade using emotional appeals', 'Describe a personal experience'], 0),
            ('The word "ubiquitous" most closely means:', ['Found everywhere', 'Rare and precious', 'Confusing', 'Ancient'], 0),
            ('Which best describes the tone of the passage?', ['Objective and informative', 'Angry and confrontational', 'Humorous and light', 'Melancholy and nostalgic'], 0),
            ('What can be inferred from the final paragraph?', ['The situation is improving', 'The situation is worsening', 'The author is uncertain', 'No change has occurred'], 0),
            ('The phrase "a double-edged sword" suggests:', ['Something with both benefits and drawbacks', 'A dangerous weapon', 'A simple solution', 'A historical reference'], 0),
            ('Which literary device is used in "The wind whispered through the trees"?', ['Personification', 'Simile', 'Metaphor', 'Hyperbole'], 0),
        ],
    },
    {
        'title': 'Classroom Ice-Breaker',
        'description': 'Light-hearted poll for the first day of class — helps students feel comfortable and builds community.',
        'quiz_type': QuizType.POLL,
        'category': 'classroom',
        'questions': [
            ('How are you feeling about this course?', ['Excited and ready', 'Curious but a bit nervous', 'Neutral — let\'s see', 'Slightly overwhelmed'], 0),
            ('What is your preferred way to learn new things?', ['Watching videos', 'Reading', 'Hands-on practice', 'Group discussion'], 0),
            ('How do you usually handle a topic you find difficult?', ['Ask for help immediately', 'Research on my own first', 'Work with a classmate', 'Take a break and come back'], 0),
            ('What do you hope to get most from this class?', ['Practical skills', 'A good grade', 'New connections', 'Deeper understanding of the subject'], 0),
        ],
    },

    # ── ALL-HANDS ─────────────────────────────────────────────────────────────
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
    {
        'title': 'Town Hall Sentiment Check',
        'description': 'Quick live pulse at the end of a town hall to gauge mood and clarity.',
        'quiz_type': QuizType.POLL,
        'category': 'all-hands',
        'questions': [
            ('How would you rate today\'s all-hands?', ['Very valuable', 'Useful', 'Could be shorter', 'Too long / not relevant'], 0),
            ('How clear is the company direction after today?', ['Very clear', 'Clearer than before', 'Still some questions', 'Unclear'], 0),
            ('How motivated do you feel going into the next quarter?', ['Very motivated', 'Motivated', 'Neutral', 'Concerned'], 0),
            ('What topic deserves more time in future all-hands?', ['Strategy & vision', 'Team wins & recognition', 'Product updates', 'People & culture'], 0),
        ],
    },
    {
        'title': 'Remote Work Experience Survey',
        'description': 'Offline poll to understand how the team feels about remote/hybrid work — submit anytime.',
        'quiz_type': QuizType.OFFLINE_POLL,
        'category': 'all-hands',
        'questions': [
            ('How productive are you working remotely compared to the office?', ['More productive', 'About the same', 'Less productive', 'Depends on the day'], 0),
            ('What is your biggest challenge working remotely?', ['Communication gaps', 'Lack of social connection', 'Home distractions', 'Tech / equipment issues'], 0),
            ('How many days per week would you prefer to be in the office?', ['0 — fully remote', '1–2 days', '3–4 days', '5 — fully in-office'], 0),
            ('How well does the company support remote workers?', ['Very well', 'Well', 'Could be better', 'Not well'], 0),
            ('Which would improve your remote experience most?', ['Better async tools', 'More virtual socials', 'Clearer communication norms', 'Home office stipend'], 0),
        ],
    },
    {
        'title': 'Company Trivia — Know Your Org',
        'description': 'Fun quiz on company history, milestones, and fun facts — a great all-hands warm-up.',
        'quiz_type': QuizType.QUIZ,
        'category': 'all-hands',
        'questions': [
            ('In what year was the company founded?', ['2018', '2016', '2020', '2014'], 0),
            ('What was the company\'s first product or service?', ['The core SaaS platform', 'A consulting service', 'A mobile app', 'A hardware device'], 0),
            ('How many countries do we operate in today?', ['12', '5', '20', '30'], 0),
            ('Which department grew the fastest last year?', ['Engineering', 'Sales', 'Customer Success', 'Marketing'], 0),
            ('What is our company\'s biggest market by revenue?', ['North America', 'Europe', 'Asia Pacific', 'South Asia'], 0),
            ('Who is our longest-serving team member?', ['The CEO', 'The CTO', 'A support engineer', 'The Head of Sales'], 0),
        ],
    },

    # ── TRAINING ──────────────────────────────────────────────────────────────
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
    {
        'title': 'Cybersecurity Awareness',
        'description': 'Essential cybersecurity training — phishing, password hygiene, and safe browsing for all employees.',
        'quiz_type': QuizType.EXAM,
        'category': 'training',
        'questions': [
            ('What is phishing?', ['A fraudulent attempt to obtain sensitive information via deceptive emails', 'A type of firewall', 'A network monitoring tool', 'Encrypting data in transit'], 0),
            ('Which is the strongest password?', ['P@ssw0rd!2024#Zq7', 'password123', 'MyName1990', 'qwerty'], 0),
            ('What should you do if you receive a suspicious email?', ['Report it to IT and do not click links', 'Delete it immediately', 'Forward to colleagues to warn them', 'Reply to verify the sender'], 0),
            ('Two-factor authentication (2FA) adds security by:', ['Requiring a second verification step beyond password', 'Encrypting all data', 'Scanning for viruses', 'Blocking all external logins'], 0),
            ('What is a VPN used for?', ['Encrypting your internet connection', 'Speeding up your internet', 'Blocking ads', 'Storing passwords'], 0),
            ('Which of these is a sign your device may be infected?', ['Unusually slow performance and unexpected pop-ups', 'Faster boot times', 'Fewer emails', 'Better battery life'], 0),
            ('Social engineering attacks target:', ['Human psychology and trust', 'Software vulnerabilities', 'Network firewalls', 'Database encryption'], 0),
            ('What does "HTTPS" indicate about a website?', ['The connection is encrypted', 'The site is government-run', 'The site is free from malware', 'The site is authenticated by Google'], 0),
        ],
    },
    {
        'title': 'Customer Service Fundamentals',
        'description': 'Assess understanding of customer service best practices, de-escalation, and communication skills.',
        'quiz_type': QuizType.EXAM,
        'category': 'training',
        'questions': [
            ('When a customer is angry, the best first step is to:', ['Listen and acknowledge their frustration', 'Transfer the call immediately', 'Offer a discount straight away', 'Explain company policy'], 0),
            ('Active listening involves:', ['Paraphrasing and confirming understanding', 'Waiting silently for your turn to speak', 'Taking notes without responding', 'Giving your opinion quickly'], 0),
            ('CSAT stands for:', ['Customer Satisfaction Score', 'Customer Service Assessment Test', 'Call Support and Timing', 'Customer Support Audit Tool'], 0),
            ('Which tone is most appropriate in a support email?', ['Professional, warm, and clear', 'Casual and informal', 'Formal and distant', 'Short and technical'], 0),
            ('When you cannot resolve an issue immediately, you should:', ['Set a clear follow-up time and keep the promise', 'Tell the customer to try again later', 'Escalate without informing the customer', 'Close the ticket'], 0),
            ('First call resolution (FCR) measures:', ['Resolving an issue in the first interaction', 'The average call length', 'Number of calls per day', 'Customer wait time'], 0),
        ],
    },
    {
        'title': 'Onboarding Day-1 Pulse',
        'description': 'A quick live poll at the end of day one — gauge new-hire energy and surface early questions.',
        'quiz_type': QuizType.POLL,
        'category': 'training',
        'questions': [
            ('How would you describe your first day overall?', ['Exciting and welcoming', 'Informative but a lot to take in', 'Slightly overwhelming', 'Not sure yet'], 0),
            ('How clear is your role and what\'s expected of you?', ['Very clear', 'Mostly clear', 'Somewhat unclear', 'Not clear at all'], 0),
            ('How welcome did the team make you feel?', ['Extremely welcome', 'Pretty welcome', 'Neutral', 'Could be warmer'], 0),
            ('What would have made today even better?', ['More 1-on-1 time', 'A clearer schedule', 'More tools access', 'Nothing — it was great'], 0),
        ],
    },
    {
        'title': 'Post-Training Feedback',
        'description': 'Offline feedback form to collect honest reactions after any training session.',
        'quiz_type': QuizType.OFFLINE_POLL,
        'category': 'training',
        'questions': [
            ('How would you rate this training overall?', ['Excellent', 'Good', 'Average', 'Needs improvement'], 0),
            ('How relevant was the content to your day-to-day work?', ['Very relevant', 'Mostly relevant', 'Somewhat relevant', 'Not relevant'], 0),
            ('How would you rate the trainer / facilitator?', ['Excellent', 'Good', 'Average', 'Poor'], 0),
            ('Would you recommend this training to a colleague?', ['Definitely yes', 'Probably yes', 'Probably not', 'Definitely not'], 0),
        ],
    },

    # ── HIRING ────────────────────────────────────────────────────────────────
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
    {
        'title': 'JavaScript Fundamentals Screen',
        'description': 'Screen for junior-to-mid JavaScript knowledge — closures, async, DOM, and ES6+ syntax.',
        'quiz_type': QuizType.EXAM,
        'category': 'hiring',
        'questions': [
            ('What does "===" check vs "=="?', ['Strict equality (type + value) vs loose equality (value only)', 'Value only vs type only', 'Both check the same thing', 'None of the above'], 0),
            ('What is a closure in JavaScript?', ['A function that captures variables from its outer scope', 'A way to close a browser tab', 'A method to end a loop', 'A type of event listener'], 0),
            ('Which keyword declares a block-scoped variable?', ['let', 'var', 'scope', 'local'], 0),
            ('What does "async/await" simplify?', ['Working with Promises', 'DOM manipulation', 'Array methods', 'Module imports'], 0),
            ('What is the output of typeof null?', ['"object"', '"null"', '"undefined"', '"string"'], 0),
            ('Which method creates a new array from a transformed existing array?', ['Array.map()', 'Array.filter()', 'Array.reduce()', 'Array.forEach()'], 0),
            ('Arrow functions differ from regular functions in that they:', ['Do not bind their own "this"', 'Cannot take parameters', 'Always return undefined', 'Cannot be assigned to variables'], 0),
            ('What does the spread operator (...) do?', ['Expands an iterable into individual elements', 'Merges two functions', 'Declares a rest parameter only', 'Clones a class'], 0),
        ],
    },
    {
        'title': 'Project Manager Situational Judgement',
        'description': 'Scenario-based assessment for PM candidates — tests prioritisation, stakeholder management, and risk.',
        'quiz_type': QuizType.EXAM,
        'category': 'hiring',
        'questions': [
            ('A key stakeholder requests a major scope change 2 weeks before launch. You should:', ['Assess impact, document it, and discuss trade-offs with the team and stakeholder', 'Accept the change to keep the stakeholder happy', 'Reject it outright to protect the timeline', 'Implement it quietly without telling the team'], 0),
            ('Your top developer says the sprint goal is unrealistic. You:', ['Facilitate a team discussion to adjust scope or get more resources', 'Tell them to work overtime', 'Ignore the concern and push forward', 'Replace the developer'], 0),
            ('The best way to track project health is:', ['Regular status updates + risk register + milestone burn-down', 'Weekly email to the CEO', 'Counting closed tickets only', 'Daily standups alone'], 0),
            ('A dependency from another team is delayed by 2 weeks. You:', ['Identify workarounds, escalate early, and update the project plan', 'Wait and see if they catch up', 'Blame the other team in the status report', 'Extend the deadline without informing stakeholders'], 0),
            ('When prioritising the backlog, you primarily consider:', ['Business value, urgency, and technical risk', 'What the loudest stakeholder asks for', 'The easiest items first', 'Alphabetical order'], 0),
            ('A retrospective is most useful for:', ['Continuous improvement based on what worked and what didn\'t', 'Assigning blame for project failures', 'Reporting to senior management', 'Closing the project formally'], 0),
        ],
    },
    {
        'title': 'Culture Fit — Take-Home Survey',
        'description': 'Offline survey for candidates to complete before their final interview — covers values and work style.',
        'quiz_type': QuizType.OFFLINE_POLL,
        'category': 'hiring',
        'questions': [
            ('What type of company culture do you thrive in?', ['Fast-paced and ambiguous', 'Structured and process-driven', 'Collaborative and flat', 'Independent and autonomous'], 0),
            ('How do you prefer to receive feedback?', ['Frequently and directly', 'In scheduled 1-on-1s', 'In writing after reflection', 'From peers rather than managers'], 0),
            ('What motivates you most at work?', ['Solving challenging problems', 'Seeing customer impact', 'Career growth', 'Financial reward'], 0),
            ('How do you handle competing priorities?', ['Prioritise by impact and communicate trade-offs', 'Ask my manager to decide', 'Work on everything in parallel', 'Focus on the quickest wins first'], 0),
            ('What does work-life balance mean to you?', ['Clear boundaries between work and personal time', 'Flexibility to manage both as needed', 'Results over hours — I work when needed', 'A company benefit I have not thought much about'], 0),
        ],
    },

    # ── GENERAL ───────────────────────────────────────────────────────────────
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
    {
        'title': 'General Knowledge Trivia',
        'description': '10 questions spanning science, geography, history, and pop culture — great for any group.',
        'quiz_type': QuizType.QUIZ,
        'category': 'general',
        'questions': [
            ('What is the chemical symbol for gold?', ['Au', 'Ag', 'Fe', 'Cu'], 0),
            ('Which planet is closest to the Sun?', ['Mercury', 'Venus', 'Earth', 'Mars'], 0),
            ('How many sides does a hexagon have?', ['6', '5', '7', '8'], 0),
            ('Who wrote "Romeo and Juliet"?', ['William Shakespeare', 'Charles Dickens', 'Jane Austen', 'Leo Tolstoy'], 0),
            ('What is the largest ocean on Earth?', ['Pacific', 'Atlantic', 'Indian', 'Arctic'], 0),
            ('How many bones are in the adult human body?', ['206', '189', '215', '300'], 0),
            ('The Great Wall of China was built primarily to:', ['Defend against northern invasions', 'Mark trade routes', 'Support irrigation', 'Define province borders'], 0),
            ('What is the speed of light (approx)?', ['300,000 km/s', '150,000 km/s', '30,000 km/s', '3,000 km/s'], 0),
            ('Which country invented the printing press in the 15th century?', ['Germany', 'China (modern press)', 'France', 'England'], 0),
            ('What year did the Berlin Wall fall?', ['1989', '1991', '1987', '1993'], 0),
        ],
    },
    {
        'title': 'Team Fun Friday Quiz',
        'description': '8 light-hearted questions for a Friday team session — movies, food, sports, and pop culture.',
        'quiz_type': QuizType.QUIZ,
        'category': 'general',
        'questions': [
            ('Which film won Best Picture at the 2020 Oscars?', ['Parasite', 'Joker', '1917', 'Once Upon a Time in Hollywood'], 0),
            ('How many players are on a standard basketball team on court?', ['5', '6', '7', '4'], 0),
            ('Which country is pizza originally from?', ['Italy', 'Greece', 'France', 'Spain'], 0),
            ('What is the most streamed song on Spotify of all time (as of 2024)?', ['Blinding Lights — The Weeknd', 'Shape of You — Ed Sheeran', 'Dance Monkey — Tones and I', 'Despacito — Luis Fonsi'], 0),
            ('Which animal is the fastest on land?', ['Cheetah', 'Lion', 'Greyhound', 'Pronghorn'], 0),
            ('How many time zones does Russia have?', ['11', '9', '6', '13'], 0),
            ('What is the capital of Iceland?', ['Reykjavik', 'Oslo', 'Helsinki', 'Tallinn'], 0),
            ('"To be or not to be" is from which Shakespeare play?', ['Hamlet', 'Macbeth', 'Othello', 'King Lear'], 0),
        ],
    },
    {
        'title': 'Weekly Team Pulse',
        'description': 'A 3-question weekly check-in to keep a finger on team morale and workload.',
        'quiz_type': QuizType.POLL,
        'category': 'general',
        'questions': [
            ('How are you feeling heading into this week?', ['Energised and ready', 'Focused and calm', 'A bit stretched', 'Struggling — need support'], 0),
            ('How manageable is your workload right now?', ['Very manageable', 'Manageable', 'A bit much', 'Overwhelmed'], 0),
            ('Anything blocking you that the team should know about?', ['Yes — I\'ll flag it separately', 'Minor things I\'m handling', 'No blockers', 'Not sure yet'], 0),
        ],
    },
    {
        'title': 'Event Feedback Form',
        'description': 'Offline feedback form for any company event — conference, workshop, offsite, or team outing.',
        'quiz_type': QuizType.OFFLINE_POLL,
        'category': 'general',
        'questions': [
            ('How would you rate this event overall?', ['Excellent', 'Good', 'Average', 'Poor'], 0),
            ('How well was the event organised?', ['Very well', 'Well', 'Could be better', 'Poorly'], 0),
            ('How relevant was the content / agenda to your work?', ['Very relevant', 'Mostly relevant', 'Somewhat relevant', 'Not relevant'], 0),
            ('How likely are you to attend a similar event again?', ['Definitely', 'Probably', 'Unlikely', 'Definitely not'], 0),
            ('What would make future events better?', ['More networking time', 'Better speakers / content', 'Shorter duration', 'Different format (virtual/hybrid)'], 0),
        ],
    },
]


async def main():
    async with AsyncSessionLocal() as db:
        # Find super_admin from any tenant (robust across test/live DBs)
        result = await db.execute(
            select(User).filter(User.role == 'super_admin').limit(1)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            print('No super_admin user found in the database')
            return
        print(f'Using super_admin: id={admin.id}, tenant_id={admin.tenant_id}')

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
                tenant_id=admin.tenant_id,
                creator_id=admin.id,
                title=f"Template Event - {tmpl['title']}",
                description=None,
                join_code=None,
            )
            db.add(event)
            await db.flush()

            quiz = Quiz(
                tenant_id=admin.tenant_id,
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
            print(f'  CREATED [{tmpl["category"]}] {tmpl["quiz_type"].value}: {tmpl["title"]} ({len(tmpl["questions"])}q)')

        await db.commit()
        print(f'\nDone. Created {created} new templates.')


if __name__ == '__main__':
    asyncio.run(main())
