# Translation Update Checklist

**Quick reference for developers adding or modifying UI elements.**

Use this checklist every time you add user-facing text to the frontend.

---

## Pre-Development

- [ ] Identified all user-facing strings (buttons, labels, messages, etc.)
- [ ] Determined the translation category (common, auth, quiz, audience, navigation)
- [ ] Planned key names (use camelCase, be descriptive)

## English Translation (Required)

- [ ] Added new keys to `frontend/src/locales/en/translation.json`
- [ ] Verified JSON syntax is valid (brackets, commas, quotes)
- [ ] English text is clear and grammatically correct

## All Language Translations (Required)

- [ ] Added same keys to `hi/translation.json` (Hindi)
- [ ] Added same keys to `ta/translation.json` (Tamil)
- [ ] Added same keys to `te/translation.json` (Telugu)
- [ ] Added same keys to `ka/translation.json` (Kannada)
- [ ] Added same keys to `bn/translation.json` (Bengali)
- [ ] Added same keys to `gu/translation.json` (Gujarati)
- [ ] JSON syntax valid in all 7 files
- [ ] All translations are contextually accurate (not machine-translated)

## Component Implementation

- [ ] Imported `useTranslation` hook: `import { useTranslation } from 'react-i18next'`
- [ ] Destructured `t` function: `const { t } = useTranslation()`
- [ ] Replaced all hardcoded strings with `t('section.key')` calls
- [ ] No hardcoded English strings remain in component
- [ ] Error/validation messages use translation keys

## Testing & Verification

- [ ] Started dev server: `npm run dev`
- [ ] Tested English (en) - no placeholder text
- [ ] Tested Hindi (hi) - special characters display correctly
- [ ] Tested Tamil (ta) - no text truncation
- [ ] Tested Telugu (te) - proper alignment
- [ ] Tested Kannada (ka) - full character support
- [ ] Tested Bengali (bn) - conjuncts render properly
- [ ] Tested Gujarati (gu) - all characters visible
- [ ] No "section.key" placeholders appear in any language
- [ ] UI layout looks good in all languages (no overflow)

## Code Review

- [ ] Translation keys follow naming convention (camelCase, descriptive)
- [ ] All 7 language files updated together
- [ ] No file accidentally missed
- [ ] Keys are consistent across all language files
- [ ] Component uses only i18n keys, no hardcoded strings

## Commit & Merge

- [ ] Commit message mentions translation updates
- [ ] All translation files included in commit
- [ ] Component file included in commit
- [ ] PR description links to [TRANSLATION_MAINTENANCE.md](../../../Docs/TRANSLATION_MAINTENANCE.md)

---

## Common Pitfalls (Avoid These!)

❌ Updating only English file  
❌ Forgetting to import `useTranslation`  
❌ Using hardcoded strings instead of `t()`  
❌ Inconsistent key naming  
❌ Skipping testing in non-English languages  
❌ Not validating JSON syntax  
❌ Leaving placeholder text in keys  

## Quick Links

| Resource | Link |
|----------|------|
| Translation Maintenance Guide | [TRANSLATION_MAINTENANCE.md](../../../Docs/TRANSLATION_MAINTENANCE.md) |
| i18n Implementation Details | [I18N_IMPLEMENTATION.md](./I18N_IMPLEMENTATION.md) |
| Translation Files Directory | `frontend/src/locales/` |
| Language Switcher Component | `frontend/src/components/LanguageSwitcher.jsx` |
| Main App Integration | `frontend/src/App.jsx` |

## Need Help?

1. **Missing key error?** Add key to all 7 translation files
2. **Special characters not showing?** Check font supports the script (Indian scripts require specific fonts)
3. **Text overflowing?** Test responsive design, may need CSS adjustments
4. **Translation quality?** Consult native speakers, avoid machine translation
5. **Build failing?** Validate JSON syntax with a JSON linter

---

**Where's the full guide?** See [TRANSLATION_MAINTENANCE.md](../../../Docs/TRANSLATION_MAINTENANCE.md)
