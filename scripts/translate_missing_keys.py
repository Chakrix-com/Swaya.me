#!/usr/bin/env python3
"""
Translate 57 UI keys that were missing from all locale files (had only inline defaultValues).
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
    'audience.enterWordCloudAnswer': 'Enter your answer (max 100 characters)',
    'common.back': 'Back',
    'common.next': 'Next',
    'common.responses': 'responses',
    'common.typeHere': 'Type your answer here...',
    'dashboard.archivedDesc': 'Completed activities',
    'dashboard.createActivityTitle': 'What would you like to create today?',
    'dashboard.createNew': 'Create New',
    'dashboard.created': 'Created',
    'dashboard.draftDesc': 'Draft activities',
    'dashboard.folderAssignFailed': 'Failed to update folder',
    'dashboard.folderAssigned': 'Folder updated',
    'dashboard.folderCreateFailed': 'Failed to create folder',
    'dashboard.folderCreated': 'Folder created',
    'dashboard.folderDeleteFailed': 'Failed to delete folder',
    'dashboard.folderDeleted': 'Folder deleted',
    'dashboard.folderName': 'Folder name',
    'dashboard.folderNameRequired': 'Folder name is required',
    'dashboard.folderRenameFailed': 'Failed to rename folder',
    'dashboard.folderRenamed': 'Folder renamed',
    'dashboard.heroSubtitle': 'Create quizzes, polls and assessments in minutes.',
    'dashboard.inTheWorks': 'In the Works',
    'dashboard.newFolder': 'New Folder',
    'dashboard.noParentRoot': 'No parent (root)',
    'dashboard.parentFolder': 'Parent folder',
    'dashboard.pastSessions': 'Past Sessions',
    'dashboard.plansSubtitle': 'Active subscription and feature limits',
    'dashboard.readyDesc': 'Activities ready to run',
    'dashboard.renameFolder': 'Rename Folder',
    'exam.noParticipantsYet': 'No one has started this exam yet.',
    'home.quickJoin.freeTagline': 'Free forever. No credit card required.',
    'offlinePoll.required': 'Required',
    'offlinePoll.requiredTooltip': 'Participants must answer this question before they can proceed.',
    'offlinePoll.requiredWarning': 'This question is required. Please answer it to continue.',
    'quiz.activities': 'activities',
    'quiz.continue': 'Continue',
    'quiz.editPoll': 'Edit Poll',
    'quiz.openRoom': 'Open Room',
    'quiz.optionPlaceholder': 'Enter option text',
    'quiz.optionRequired': 'Option cannot be empty',
    'quiz.started': 'Started',
    'quiz.timerEndOverrideDescription': 'A timer is currently running for this question. Ending now will override the timer and end the session.',
    'quiz.timerOverrideDescription': 'This question has an active timer. Continue only if you want to override it now.',
    'quiz.timerOverrideOk': 'Yes, continue',
    'quiz.timerOverrideTitle': 'Skip this timed question early?',
    'quiz.untitled': 'Untitled',
    'quiz.validationError': 'Please check all required fields before publishing',
    'quizPresent.brushColor': 'Brush color',
    'quizPresent.brushSize': 'Brush size',
    'quizPresent.clear': 'Clear',
    'quizPresent.clearWhiteboard': 'Clear whiteboard',
    'quizPresent.eraser': 'Eraser',
    'quizPresent.expandQr': 'Click to enlarge QR code',
    'quizPresent.selectColor': 'Select color',
    'quizPresent.toggleWhiteboard': 'Toggle whiteboard',
    'quizPresent.whiteboard': 'Whiteboard',
}


def gemini_translate(texts_dict: dict, target_language: str) -> dict:
    lines = '\n'.join(f'{k}|||{v}' for k, v in texts_dict.items())
    prompt = (
        f'Translate the following UI strings from English to {target_language}. '
        'These are interface labels for a web quiz/poll application — buttons, placeholders, '
        'status messages, and short descriptions. '
        'Keep proper nouns (Swaya.me, Gemini AI, QR) unchanged. '
        'Preserve {{variableName}} placeholders exactly as-is. '
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
            if e.code in (429, 503, 500):
                wait = 20 * (attempt + 1)
                print(f'  HTTP {e.code}, waiting {wait}s…', flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f'Failed after retries for {target_language}')


def set_nested(d, dotkey, value):
    keys = dotkey.split('.')
    for k in keys[:-1]: d = d.setdefault(k, {})
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
        print(f'  ⚠ {len(missing)} fell back to English: {missing[:3]}', flush=True)

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
