#!/usr/bin/env python3
"""
Translate 67 home.v2.* and tooltip.themePicker keys to all 10 non-English locales.
One Gemini API call per language.
"""

import json, time, urllib.request, sys, os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))
GEMINI_KEY = os.environ['GEMINI_KEY']
GEMINI_MODEL = os.environ.get('GEMINI_MODEL_FAST', 'gemini-2.5-flash')
LOCALES_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'locales')

LANGUAGE_NAMES = {
    'hi': 'Hindi', 'ta': 'Tamil', 'te': 'Telugu', 'ka': 'Kannada',
    'bn': 'Bengali', 'gu': 'Gujarati', 'es': 'Spanish', 'fr': 'French',
    'de': 'German', 'ru': 'Russian',
}

STRINGS_TO_TRANSLATE = {
    'tooltip.themePicker': 'Choose a UI theme',
    'home.v2.kicker': 'Live · quizzes · polls · tests',
    'home.v2.heroTitle1': 'One room.',
    'home.v2.heroTitle2': 'Every voice.',
    'home.v2.lede': 'Swaya turns any audience into participants. Run a quiz when you want energy, a poll when you want honesty, a test when it counts — everyone joins from their phone with one code.',
    'home.v2.ctaPrimary': 'Create your first session — free',
    'home.v2.ctaSecondary': 'See it live',
    'home.v2.joinLabel': 'Got a code from a host? Type it here — no app, no account. That\'s the whole onboarding.',
    'home.v2.startFree': 'Start free',
    'home.v2.forLabel': 'For',
    'home.v2.ctaButton': 'Create a session — it\'s free',
    'home.v2.tab_quiz': 'Quiz',
    'home.v2.tab_poll': 'Poll',
    'home.v2.tab_test': 'Test',
    'home.v2.demoQuizPill': 'LIVE QUIZ',
    'home.v2.demoQuizQuestion': 'Which planet has the shortest day?',
    'home.v2.demoQuizMeta': 'Question 3 of 10',
    'home.v2.demoQuizAnswering': 'answering',
    'home.v2.demoPollPill': 'LIVE POLL',
    'home.v2.demoPollQuestion': 'One word for how this term went?',
    'home.v2.demoPollMeta': 'Word cloud',
    'home.v2.demoPollLive': 'updating live',
    'home.v2.demoPollResponses': 'responses',
    'home.v2.demoTestPill': 'TEST REPORT',
    'home.v2.demoTestTitle': 'Unit 4 — Screening results',
    'home.v2.demoTestMeta': 'Auto-scored · 42 candidates',
    'home.v2.demoTestAvg': 'avg score',
    'home.v2.demoTestExport': 'export: PDF · Excel',
    'home.v2.modesEyebrow': 'Three instruments',
    'home.v2.modesTitle1': 'Same room, same code —',
    'home.v2.modesTitle2': 'different jobs',
    'home.v2.modesSub': 'One platform, three modes. Pick the one the moment needs.',
    'home.v2.quizCardTitle': 'When you want energy',
    'home.v2.quizCardDesc': 'Timed questions, points for speed and accuracy, a leaderboard that reshuffles live. Revision classes and quiz nights run like a show.',
    'home.v2.quizCardFor': 'teachers, trainers, event hosts',
    'home.v2.pollCardTitle': 'When you want honesty',
    'home.v2.pollCardDesc': 'Opinion polls, word clouds, pulse checks — anonymous by default, visualised as they arrive. Replace "any questions?" silence with real answers.',
    'home.v2.pollCardFor': 'team leads, town halls, webinars',
    'home.v2.testCardTitle': 'When it counts',
    'home.v2.testCardDesc': 'Timed assessments with auto-grading, webcam snapshots, per-question analytics and exportable reports. Calm, focused, fair.',
    'home.v2.testCardFor': 'institutes, hiring rounds, certification',
    'home.v2.howEyebrow': 'How it works',
    'home.v2.howTitle1': 'Five minutes from idea to',
    'home.v2.howTitle2': 'everyone in',
    'home.v2.step1Title': 'Build',
    'home.v2.step1Desc': 'Write questions in the editor, import a spreadsheet, or let AI draft them. Timers, points and order — set in minutes.',
    'home.v2.step2Title': 'Share',
    'home.v2.step2DescA': 'Every session gets a short code like',
    'home.v2.step2DescB': 'On the projector, in the chat, on the wall. Any browser joins instantly.',
    'home.v2.step3Title': 'Run',
    'home.v2.step3Desc': 'Answers stream in live. Quizzes get a leaderboard, polls get a picture of the room, tests get a full report when time\'s up.',
    'home.v2.trustEyebrow': 'When it counts',
    'home.v2.trustTitle1': 'Built to be',
    'home.v2.trustTitle2': 'trusted',
    'home.v2.trustTitle3': ', not just enjoyed',
    'home.v2.trust1b': 'Auto-scoring with per-question analytics',
    'home.v2.trust1': 'see exactly where a class or candidate pool struggled.',
    'home.v2.trust2b': 'Webcam snapshots during tests',
    'home.v2.trust2': 'light-touch proctoring for screenings and exams.',
    'home.v2.trust3b': 'Exportable evidence',
    'home.v2.trust3': 'PDF, Excel, Word and PowerPoint reports the moment a session ends.',
    'home.v2.trust4b': 'Eleven languages',
    'home.v2.trust4': 'English, हिन्दी, தமிழ், తెలుగు, ಕನ್ನಡ, বাংলা, ગુજરાતী, Español, Français, Deutsch, Русский.',
    'home.v2.quote': '"The quiz got them excited. The report is why we kept the subscription."',
    'home.v2.quoteCite': '— What we build for: both halves of that sentence',
    'home.v2.ctaTitle': 'The next session could be yours',
    'home.v2.ctaSub': 'Create a quiz, a poll, or a test now. Share the code. Watch the room light up — or settle down and focus. Free to start.',
}


def gemini_translate(texts_dict: dict, target_language: str) -> dict:
    lines = '\n'.join(f'{k}|||{v}' for k, v in texts_dict.items())
    prompt = (
        f'Translate the following UI strings from English to {target_language}. '
        'These are marketing and interface labels for a live quiz/poll/test web application. '
        'Keep proper nouns (Swaya, PDF, Excel, Word, PowerPoint, QR, AI) unchanged. '
        'Keep "Quiz", "Poll", "Test" as recognisable terms — borrow or transliterate if no natural equivalent. '
        'The string home.v2.trust4 lists language names in their own native scripts; keep it exactly as-is (do not translate those script names). '
        'Preserve {{variableName}} placeholders exactly. '
        'Preserve the "|||" separator exactly. '
        'Return ONLY the translated lines in the same KEY|||TRANSLATION format, one per line, no extra text.\n\n'
        + lines
    )
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}'
    body = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.2},
    }).encode()

    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
            resp = urllib.request.urlopen(req, timeout=90)
            data = json.loads(resp.read())
            raw = data['candidates'][0]['content']['parts'][0]['text'].strip()
            result = {}
            for line in raw.splitlines():
                line = line.strip()
                if '|||' in line:
                    k, _, v = line.partition('|||')
                    result[k.strip()] = v.strip()
            return result
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 500):
                wait = 20 * (attempt + 1)
                print(f'  HTTP {e.code}, waiting {wait}s…', flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f'Failed after retries for {target_language}')


def set_nested(d, dotkey, value):
    keys = dotkey.split('.')
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def process_locale(lang, lang_name):
    path = os.path.join(LOCALES_DIR, lang, 'translation.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    print(f'\n[{lang}] {lang_name} — translating {len(STRINGS_TO_TRANSLATE)} strings…', flush=True)
    translated = gemini_translate(STRINGS_TO_TRANSLATE, lang_name)

    updated = 0
    missing = []
    for key, en_val in STRINGS_TO_TRANSLATE.items():
        if key in translated:
            set_nested(data, key, translated[key])
        else:
            set_nested(data, key, en_val)
            missing.append(key)
        updated += 1

    if missing:
        print(f'  ⚠ {len(missing)} fell back to English: {missing[:5]}', flush=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(f'  ✓ {updated} keys written', flush=True)


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    langs = {target: LANGUAGE_NAMES[target]} if target else LANGUAGE_NAMES

    for lang, name in langs.items():
        process_locale(lang, name)
        if len(langs) > 1:
            time.sleep(5)

    print('\nDone.')
