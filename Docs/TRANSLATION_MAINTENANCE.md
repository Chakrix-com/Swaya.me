# Translation Maintenance Guide

This document provides step-by-step instructions for maintaining translations whenever UI elements are added or modified in Swaya.me.

## Quick Reference

**When**: Every time you add or modify user-facing text in the frontend  
**Where**: All 7 translation JSON files in `frontend/src/locales/`  
**Who**: Any developer adding UI elements  
**Why**: To ensure all supported languages remain synchronized and up-to-date

## Supported Languages

| Code | Language | Status |
|------|----------|--------|
| en | English | Default, Required |
| hi | हिन्दी (Hindi) | Required |
| ta | தமிழ் (Tamil) | Required |
| te | తెలుగు (Telugu) | Required |
| ka | ಕನ್ನಡ (Kannada) | Required |
| bn | বাঙ্গালি (Bengali) | Required |
| gu | ગુજરાતી (Gujarati) | Required |

## Step-by-Step Process

### Step 1: Identify All User-Facing Text

List every string that appears in the UI:
- Button labels
- Form labels
- Placeholder text
- Error messages
- Validation messages
- Menu items
- Headings
- Tooltips
- Status messages

**Example**: New "Archive Quiz" feature introduces:
- Button label: "Archive Quiz"
- Confirmation message: "Are you sure you want to archive this quiz?"
- Success message: "Quiz archived successfully"
- Error message: "Failed to archive quiz"

### Step 2: Categorize Strings

Assign each string to a logical section in the translation JSON:

```
common      → General UI (Save, Delete, Cancel, Loading, etc.)
auth        → Login/Register screens
quiz        → Quiz creation, editing, management
audience    → Audience/participant features
navigation  → Menu items, page titles
```

**Example**: Archive Quiz strings belong in `quiz` section

### Step 3: Update English Translation File

Open `frontend/src/locales/en/translation.json` and add your new keys:

```json
{
  "quiz": {
    "archiveQuiz": "Archive Quiz",
    "archiveConfirm": "Are you sure you want to archive this quiz?",
    "archiveSuccess": "Quiz archived successfully",
    "archiveError": "Failed to archive quiz"
  }
}
```

### Step 4: Translate to All 6 Other Languages

For each language file (`hi`, `ta`, `te`, `ka`, `bn`, `gu`), add the same keys with translations:

**Hindi** (`hi/translation.json`):
```json
{
  "quiz": {
    "archiveQuiz": "क्विज़ को अभिलेख में रखें",
    "archiveConfirm": "क्या आप वाकई इस क्विज़ को अभिलेख में रखना चाहते हैं?",
    "archiveSuccess": "क्विज़ सफलतापूर्वक अभिलेख में रखा गया",
    "archiveError": "क्विज़ को अभिलेख में रखने में विफल"
  }
}
```

**Tamil** (`ta/translation.json`):
```json
{
  "quiz": {
    "archiveQuiz": "வினாடி வினாவை காப்பகப்படுத்து",
    "archiveConfirm": "இந்த வினாடி வினாவை காப்பகப்படுத்த விரும்புகிறீர்களா?",
    "archiveSuccess": "வினாடி வினா வெற்றிகரமாக காப்பகப்படுத்தப்பட்டது",
    "archiveError": "வினாடி வினாவை காப்பகப்படுத்த முடியவில்லை"
  }
}
```

### Step 5: Update Your React Component

Use the `useTranslation()` hook to access translations:

```jsx
import { useTranslation } from 'react-i18next'
import { Button, Modal, message } from 'antd'

function ArchiveQuizButton({ quizId }) {
  const { t } = useTranslation()

  const handleArchive = async () => {
    Modal.confirm({
      title: t('quiz.archiveQuiz'),
      content: t('quiz.archiveConfirm'),
      onOk: async () => {
        try {
          await archiveQuiz(quizId)
          message.success(t('quiz.archiveSuccess'))
        } catch (error) {
          message.error(t('quiz.archiveError'))
        }
      },
    })
  }

  return (
    <Button onClick={handleArchive}>
      {t('quiz.archiveQuiz')}
    </Button>
  )
}

export default ArchiveQuizButton
```

### Step 6: Verify in All Languages

1. Start the development server: `npm run dev`
2. Use the language switcher to test each language
3. Verify all text appears correctly
4. Check for text overflow or layout issues

## Testing Checklist

- [ ] **English (en)**: Text displays correctly, no placeholders
- [ ] **Hindi (hi)**: Right-to-left text direction handled, meanings preserved
- [ ] **Tamil (ta)**: Special characters render properly
- [ ] **Telugu (te)**: Text alignment and spacing correct
- [ ] **Kannada (ka)**: No text truncation
- [ ] **Bengali (bn)**: All conjuncts display correctly
- [ ] **Gujarati (gu)**: No missing characters

## Common Issues & Solutions

### Issue: "common.missingKey" displays in UI

**Cause**: Translation key not found in JSON file  
**Solution**: 
1. Check spelling of key in component
2. Verify key exists in all 7 language files
3. Ensure JSON syntax is valid (valid JSON brackets, commas)

### Issue: Text overflows UI in certain languages

**Cause**: Different languages have different lengths (e.g., German is longer than English)  
**Solution**:
1. Add `white-space: normal` to CSS
2. Use flexible widths instead of fixed
3. Test all languages before merging

### Issue: Special characters appear as boxes

**Cause**: Font doesn't support script (Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati use non-Latin scripts)  
**Solution**: 
1. Ensure font supports Indian scripts (Noto Sans family is recommended)
2. Confirm browser charset is UTF-8

### Issue: Forgot to update a language file

**Cause**: Only updated 5 out of 7 language files  
**Solution**:
1. Search for the key in all language files
2. Add missing keys to incomplete files
3. Test language switching for that language

## Best Practices

### ✅ Do's

- **Do** categorize related strings together in the same section
- **Do** use descriptive, context-specific key names
- **Do** test all 7 languages before committing
- **Do** use consistent terminology across all languages
- **Do** update translations immediately when modifying UI text
- **Do** use professional or native speakers for non-English translations

### ❌ Don'ts

- **Don't** hardcode strings in React components
- **Don't** update only some language files
- **Don't** use vague key names like `text1` or `label`
- **Don't** rely on machine translation for accuracy
- **Don't** forget to import `useTranslation` hook
- **Don't** mix English text with translation keys

## Key Naming Conventions

Use these patterns for consistent key naming:

```
action items:        create*, delete*, edit*, archive*, publish*
confirmation:        *Confirm, *Sure
status messages:     *Success, *Error, *Failed, *Loading
labels:              *Label, *Title, *Heading
placeholders:        *Placeholder
buttons:             *Button (rarely needed, usually implied)
```

**Examples**:
```
✅ quiz.archiveQuiz          (verb-object pattern)
✅ quiz.archiveConfirm       (action-status pattern)
✅ quiz.noQuizzes            (state-specific pattern)
❌ quiz.button               (too vague)
❌ quiz.txt1                 (meaningless)
❌ archive                   (not scoped)
```

## Integration with Component Development

### Before Writing Component Code

1. Plan all user-facing text
2. Create translation keys structure
3. Update all 7 language files
4. Commit translation changes

### While Writing Component Code

1. Import `useTranslation` hook
2. Destructure `t` function: `const { t } = useTranslation()`
3. Replace all hardcoded strings with `t('section.key')`
4. Test language switching

### After Merging

1. Verify language switcher works on production
2. Monitor for untranslated strings (show as "section.key")
3. Collect user feedback on translation quality
4. Improve translations based on feedback

## File Structure Reference

```
frontend/src/
└── locales/
    ├── i18n.js                      # i18n configuration & initialization
    ├── en/translation.json          # English (master file)
    ├── hi/translation.json          # Hindi
    ├── ta/translation.json          # Tamil
    ├── te/translation.json          # Telugu
    ├── ka/translation.json          # Kannada
    ├── bn/translation.json          # Bengali
    └── gu/translation.json          # Gujarati
```

## Quick Command Reference

```bash
# Install dependencies
npm install

# Start development server (test translations)
npm run dev

# Build for production
npm run build

# Check for missing translation keys (manual)
# Search for hardcoded strings in src/ directory
grep -r "\"[A-Z]" src/ --include="*.jsx" | grep -v "t("
```

## Extended Language Support (Future)

When adding new languages beyond MVP:

1. Create `src/locales/{code}/translation.json`
2. Add language to `LanguageSwitcher.jsx`
3. Add to i18n configuration in `i18n.js`
4. Translate all existing keys (full coverage required)

Example for Malayalam (ml):
```json
// frontend/src/locales/ml/translation.json
{
  "common": {
    "appTitle": "Swaya.me"
    // ... translate all keys
  }
}
```

## Translation Quality Standards

- **Accuracy**: Meaning preserved, not word-for-word translation
- **Consistency**: Same terms used for same concepts across all strings
- **Native speakers**: Use native speaker input for quality, free from errors
- **Culture**: Adapt to cultural context where needed (e.g., greetings, date formats)
- **Tone**: Match original tone (friendly, professional, casual, etc.)

## Escalation & Support

**Issues**:
- Missing translation files
- Incorrect translations
- Unsupported languages
- Rendering problems

**Contact**: Reach out to the i18n maintainer or create an issue with:
- Language affected
- Missing/incorrect key
- Expected vs. actual behavior
- Screenshots if UI-related

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial implementation: 7 languages |
| | | English (default), Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati |

---

**Last Updated**: February 10, 2026  
**Maintainer**: i18n Team  
**Status**: Active (MVP Phase)
