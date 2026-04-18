# Translation Maintenance Guide

This document provides instructions for maintaining translations whenever UI elements are added or modified in Swaya.me.

**When**: Every time you add or modify user-facing text in the frontend  
**Where**: All 11 translation JSON files in `frontend/src/locales/`  
**Who**: Any developer adding UI elements  
**Why**: To ensure all supported languages remain synchronised and up-to-date

---

## Supported Languages

| Code | Language | Status |
|------|----------|--------|
| `en` | English | Default, required |
| `hi` | हिन्दी (Hindi) | Required |
| `ta` | தமிழ் (Tamil) | Required |
| `te` | తెలుగు (Telugu) | Required |
| `ka` | ಕನ್ನಡ (Kannada) | Required |
| `bn` | বাঙ্গালি (Bengali) | Required |
| `gu` | ગુજરાતી (Gujarati) | Required |
| `es` | Español (Spanish) | Required |
| `fr` | Français (French) | Required |
| `de` | Deutsch (German) | Required |
| `ru` | Русский (Russian) | Required |

---

## Translation File Structure

Each locale has one file: `frontend/src/locales/{code}/translation.json`

Top-level sections:

```
common          → General UI (Save, Delete, Cancel, Update, Create, Loading…)
auth            → Login, Register, Verify Email, Forgot/Reset Password
quiz            → Quiz creation, editing, management, question types
audience        → Participant/audience-facing strings
dashboard       → Dashboard page including upgrade banner and tier tooltip strings
admin           → Admin panel (statistics, user management, tier management, feedback)
admin.users     → User management table and edit form labels (including tier)
admin.userForm  → Edit/create user modal labels
tooltip         → Header tooltips (language switcher, theme toggle, logout)
navigation      → Menu items, page titles
pages           → Legal, help, about pages
home            → Public landing page
```

---

## Step-by-Step Process

### Step 1: Add keys to English first

Open `frontend/src/locales/en/translation.json` and add new keys under the appropriate section.

### Step 2: Translate to all 10 other languages

Use a Python script to efficiently update all 11 files simultaneously:

```python
import json, os

locales_dir = 'frontend/src/locales'
translations = {
    'en': 'English value',
    'hi': 'हिंदी मूल्य',
    'ta': 'தமிழ் மதிப்பு',
    'te': 'తెలుగు విలువ',
    'ka': 'ಕನ್ನಡ ಮೌಲ್ಯ',
    'bn': 'বাংলা মান',
    'gu': 'ગુજરાતી મૂલ્ય',
    'es': 'Valor en español',
    'fr': 'Valeur en français',
    'de': 'Deutschen Wert',
    'ru': 'Русское значение',
}

for lang, value in translations.items():
    path = f'{locales_dir}/{lang}/translation.json'
    with open(path) as f:
        data = json.load(f)
    data.setdefault('section', {})['keyName'] = value
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Updated {lang}')
```

### Step 3: Use `t()` in the component

```jsx
import { useTranslation } from 'react-i18next'

function MyComponent() {
  const { t } = useTranslation()
  return <button>{t('section.keyName')}</button>
}
```

### Step 4: Build and verify

```bash
cd frontend && npm run build
# Check the browser in multiple languages before deploying
```

---

## Common Mistakes to Avoid

| Mistake | Fix |
|---------|-----|
| Adding keys only to `en` | Always update all 11 files |
| Leaving non-English values as the English string | Provide real translations, not copies |
| Using `t()` for keys that don't exist yet | Add the key to all locales before using it |
| Adding keys at wrong JSON path | Verify the path matches what `t()` expects |
| Skipping the build after locale changes | Always rebuild; locale files are bundled at build time |

---

## Verifying Translations

Quick audit via Python — finds missing and untranslated keys:

```python
import json

locales_dir = 'frontend/src/locales'

def flatten(d, prefix=''):
    out = {}
    for k, v in d.items():
        key = f'{prefix}.{k}' if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v
    return out

with open(f'{locales_dir}/en/translation.json') as f:
    en_flat = flatten(json.load(f))

for lang in ['hi','ta','te','ka','bn','gu','es','fr','de','ru']:
    with open(f'{locales_dir}/{lang}/translation.json') as f:
        other_flat = flatten(json.load(f))
    missing    = [k for k in en_flat if k not in other_flat]
    untranslated = [k for k in en_flat if other_flat.get(k) == en_flat[k]]
    print(f'{lang}: {len(missing)} missing, {len(untranslated)} untranslated')
```

---

## Key Sections Reference

### `dashboard` — Upgrade banner and tier tooltip

```json
"dashboard": {
  "upgradeBannerNearLimit": "You're using {{pct}}% of your quiz quota",
  "upgradeBannerOnPlan": "You're on the",
  "upgradeBannerPlan": "plan",
  "upgradeBannerNextTier": "Upgrade to {{tier}} for {{participants}} participants, {{questions}} questions, {{sessions}} concurrent sessions",
  "upgradeBannerCta": "Upgrade to {{tier}}",
  "upgradeBannerQuizUsage": "{{used}} / {{max}} quizzes used",
  "tierTooltipParticipants": "Participants / session",
  "tierTooltipQuestions": "Questions / quiz",
  "tierTooltipSessions": "Concurrent sessions"
}
```

### `admin.users` + `admin.userForm` — User management

```json
"admin": {
  "users": {
    "tier": "Tier",
    "role": "Role",
    "status": "Status"
  },
  "userForm": {
    "editUserTitle": "Edit User",
    "createUserTitle": "Create User",
    "email": "Email",
    "fullName": "Full Name",
    "password": "Password",
    "role": "Role",
    "active": "Active"
  }
}
```

### `common` — Shared action labels

```json
"common": {
  "save": "Save",
  "create": "Create",
  "update": "Update",
  "delete": "Delete",
  "cancel": "Cancel",
  "edit": "Edit",
  "submit": "Submit"
}
```

---

## Deployment

After updating locale files:

1. Build: `cd frontend && npm run build`
2. Test on `test.swaya.me` in relevant languages
3. Deploy to production: `echo "y" | ./deploy.sh promote-live`
