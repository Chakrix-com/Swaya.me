#!/usr/bin/env python3
"""
Translate new/updated legal and About page keys to all 10 non-English locales.
One Gemini API call per language — sends all changed keys as a batch.
"""

import json, time, urllib.request, sys, os

GEMINI_KEY = '***REMOVED***'
GEMINI_MODEL = 'gemini-2.5-flash'
LOCALES_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'src', 'locales')

LANGUAGE_NAMES = {
    'hi': 'Hindi',
    'ta': 'Tamil',
    'te': 'Telugu',
    'ka': 'Kannada',
    'bn': 'Bengali',
    'gu': 'Gujarati',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'ru': 'Russian',
}

# All strings to translate. Keys use dot-notation matching the JSON path.
# Value is the English source text.
STRINGS_TO_TRANSLATE = {
    # Date (simple)
    'pages.legal.lastUpdated': 'Last updated: June 2026',

    # About — updated existing
    'pages.about.whatBody2': (
        'Create Online Quizzes, Polls, and Tests with six question types: MCQ (up to 10 options), '
        'Word Cloud, Scale (1–5), Single-line, Paragraph, and One-word — all with rich text and optional '
        'image per question. Results are visualised live as participants respond, with leaderboard scoring '
        'and time-based tiebreaking. AI-powered question generation, reusable templates, and folder-based '
        'organisation are built in. Full session reports can be exported as PDF, Word, PowerPoint, or Excel.'
    ),
    'pages.about.feature1': (
        'Six question types: MCQ (up to 10 options), Word Cloud, Scale (1–5), Single-line, Paragraph, '
        'and One-word — with rich text editing and optional image per question'
    ),
    'pages.about.feature2': (
        'Three activity modes: Online Quiz (auto-scored leaderboard), Online Poll (no scoring), '
        'and Test/Exam (negative marking and LLM semantic grading)'
    ),
    'pages.about.feature6': 'Export session results as PDF, Word, PowerPoint, or Excel',
    'pages.about.feature7': 'Offline Poll mode — share a poll link without hosting a live session',
    'pages.about.feature10': (
        'Tier-based plans: FREE, BASIC, PRO, and ENTERPRISE — upgrade for higher participant and question limits'
    ),

    # About — new keys
    'pages.about.feature11': (
        'AI question generation — describe a topic and Gemini AI creates ready-to-use questions instantly'
    ),
    'pages.about.feature12': (
        'Exam proctoring — optional webcam monitoring, fullscreen enforcement, and violation detection for Test sessions'
    ),
    'pages.about.feature13': (
        'Templates and folder organisation — reuse content from the platform library and keep your activities neatly grouped'
    ),
    'pages.about.openSourceTitle': 'Open Source',
    'pages.about.openSourceBody': (
        'Swaya.me is open source, released under the Apache License 2.0. The full source code is publicly '
        'available on GitHub — you are free to self-host, fork, contribute, or build on it. '
        'Contributions and bug reports are welcome.'
    ),
    'pages.about.openSourceGithub': 'Source code on GitHub:',
    'pages.about.openSourceLicense': 'License:',

    # Privacy — new keys
    'pages.privacy.s1Body4Label': 'Proctoring data (Exam sessions only):',
    'pages.privacy.s1Body4': (
        'When a host enables proctoring on an Exam (Test) session, periodic webcam snapshots are captured '
        'from participants\' devices during the session for exam integrity purposes. Participants are shown '
        'an explicit notice and must grant camera access before joining a proctored session. These images '
        'are stored securely, are accessible only to the session host, and are not shared with any third party. '
        'They are deleted when the host removes the session history.'
    ),
    'pages.privacy.s2li1': 'To operate and deliver the Swaya.me quiz, poll, and exam platform',
    'pages.privacy.s2li6': (
        'To support exam integrity where proctoring is enabled '
        '(webcam snapshots made available to the session host only)'
    ),

    # Terms — updated + new
    'pages.terms.s1Body1': (
        'Swaya.me is a live audience engagement platform. It allows registered hosts to create and run '
        'interactive sessions — including Online Quizzes, Online Polls, Offline Polls, and proctored '
        'Exam (Test) sessions — and allows audience members to participate anonymously via a 6-digit join code.'
    ),
    'pages.terms.s1Body3': (
        'Certain Exam sessions may use optional proctoring features (webcam monitoring, fullscreen enforcement, '
        'and violation detection). Participants are shown an explicit notice and must grant camera access before '
        'joining a proctored session. By doing so, participants consent to the capture of periodic webcam snapshots '
        'for exam integrity purposes. Hosts are solely responsible for informing their participants about proctoring '
        'in advance and for complying with applicable laws regarding monitoring.'
    ),
    'pages.terms.s8Body': (
        'The Swaya.me platform source code is released under the Apache License 2.0 and is freely available '
        'on GitHub. You may use, copy, modify, and distribute the source code in accordance with that licence. '
        'The Swaya.me name, logo, and branding are trademarks of Chakrix and may not be used without prior '
        'written permission, regardless of the open-source licence on the underlying code.'
    ),
}


def gemini_translate(texts_dict: dict, target_language: str) -> dict:
    """Send all strings in one batch request. Returns {key: translated_text}."""
    lines = '\n'.join(f'{k}|||{v}' for k, v in texts_dict.items())
    prompt = (
        f'Translate the following UI strings from English to {target_language}. '
        'These are interface strings for a web application — some are feature descriptions, '
        'some are legal/privacy policy text, and some are terms of service text. '
        'Keep proper nouns (Swaya.me, Gemini AI, GitHub, Apache License 2.0, Chakrix, PDF, Word, '
        'PowerPoint, Excel, MCQ, JWT, HTTPS) unchanged. '
        'Keep HTML/markdown formatting and punctuation style consistent with the original. '
        'Preserve the "|||" separator exactly. '
        'Return ONLY the translated lines in the same KEY|||TRANSLATION format, one per line, no extra text.\n\n'
        + lines
    )

    url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}'
    body = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.2},
    }).encode()

    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
            resp = urllib.request.urlopen(req, timeout=60)
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
            if e.code == 429:
                wait = 20 * (attempt + 1)
                print(f'  Rate limited, waiting {wait}s…', flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f'Failed after retries for {target_language}')


def set_nested(d: dict, dotkey: str, value: str):
    keys = dotkey.split('.')
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def get_nested(d: dict, dotkey: str):
    for k in dotkey.split('.'):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def process_locale(lang: str, lang_name: str):
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
            updated += 1
        else:
            # Fallback: use English
            set_nested(data, key, en_val)
            missing.append(key)
            updated += 1

    if missing:
        print(f'  ⚠ {len(missing)} keys fell back to English: {missing[:3]}…', flush=True)

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
            time.sleep(5)  # brief pause between languages

    print('\nDone.')
