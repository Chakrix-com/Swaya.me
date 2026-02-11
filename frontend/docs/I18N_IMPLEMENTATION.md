# Internationalization (i18n) Implementation Guide

## Overview
The Swaya.me application now supports multiple languages with English as the default. Users can switch between the following languages:
- **English** (en)
- **Hindi** (hi)
- **Tamil** (ta)
- **Telugu** (te)
- **Kannada** (ka)
- **Bengali** (bn)
- **Gujarati** (gu)

## Setup Instructions

### 1. Install Dependencies
```bash
npm install
```

The following packages have been added:
- `i18next`: Internationalization framework
- `react-i18next`: React bindings for i18next

### 2. Project Structure
```
frontend/src/
├── locales/
│   ├── i18n.js                 # i18n configuration
│   ├── en/
│   │   └── translation.json    # English translations
│   ├── hi/
│   │   └── translation.json    # Hindi translations
│   ├── ta/
│   │   └── translation.json    # Tamil translations
│   ├── te/
│   │   └── translation.json    # Telugu translations
│   ├── ka/
│   │   └── translation.json    # Kannada translations
│   ├── bn/
│   │   └── translation.json    # Bengali translations
│   └── gu/
│       └── translation.json    # Gujarati translations
├── components/
│   └── LanguageSwitcher.jsx    # Language switcher component
│   └── PublicPageLayout.jsx    # Layout for public pages
├── main.jsx                     # App entry point (i18n initialized here)
└── App.jsx                      # Main app component
```

## Usage Guide

### Using Translations in Components

Use the `useTranslation` hook to access translations:

```jsx
import { useTranslation } from 'react-i18next'

function MyComponent() {
  const { t } = useTranslation()

  return (
    <div>
      <h1>{t('common.appTitle')}</h1>
      <p>{t('auth.loginSuccess')}</p>
      <button>{t('common.save')}</button>
    </div>
  )
}

export default MyComponent
```

### Accessing Translations in Non-Component Files

For services or utility files, you can import and use i18n directly:

```javascript
import i18n from '../locales/i18n'

const message = i18n.t('auth.invalidCredentials')
```

## Translation Structure

### Key Naming Convention
Translations are organized in a hierarchical structure:

```json
{
  "section": {
    "subsection": "Translation string"
  }
}
```

Current sections:
- `common`: General UI elements (save, delete, loading, etc.)
- `auth`: Authentication-related strings (login, register, etc.)
- `quiz`: Quiz feature strings
- `audience`: Audience/participant strings
- `navigation`: Navigation menu items

### Example Usage

In your components, reference keys with dot notation:

```jsx
// Common buttons
{t('common.save')}
{t('common.cancel')}
{t('common.delete')}

// Auth
{t('auth.login')}
{t('auth.registerSuccess')}

// Quiz
{t('quiz.createQuiz')}
{t('quiz.startQuiz')}

// Navigation
{t('navigation.home')}
{t('navigation.settings')}
```

## Adding New Translations

### 1. Add to English File
First, add the new key to `src/locales/en/translation.json`:

```json
{
  "common": {
    "...existing keys...": "...",
    "newKey": "New Translation String"
  }
}
```

### 2. Add to All Language Files
Then add the same key to all language files (`hi`, `ta`, `te`, `ka`, `bn`, `gu`):

```json
{
  "common": {
    "...existing keys...": "...",
    "newKey": "नया अनुवाद स्ट्रिंग"
  }
}
```

### 3. Use in Component
```jsx
{t('common.newKey')}
```

## Language Switcher

The `LanguageSwitcher` component is automatically included in:
- **Authenticated Layout**: Available in the top-right corner next to logout
- **Public Pages**: Can be wrapped with `PublicPageLayout` for login/register

### Using LanguageSwitcher in a Page

```jsx
import PublicPageLayout from '../../components/PublicPageLayout'

function MyPublicPage() {
  return (
    <PublicPageLayout>
      <div>Your content here</div>
    </PublicPageLayout>
  )
}
```

## Language Persistence

Selected language is automatically saved to `localStorage` as `preferredLanguage`. When users revisit the application, their previously selected language is restored.

## Key Features

✅ **Default Language**: English (en)  
✅ **Language Persistence**: User's choice saved in localStorage  
✅ **Easy to Extend**: Simple JSON structure for adding new languages  
✅ **React Integration**: Hooks-based API for seamless component integration  
✅ **Performance**: Lightweight i18next with minimal overhead  

## Implementation Checklist

- [x] i18n infrastructure created
- [x] 7 language translation files created
- [x] Language Switcher component built
- [x] Public page layout with language switcher implemented
- [x] Authenticated layout integrated with language switcher
- [ ] Extract and replace hardcoded strings in components (ongoing)
- [ ] Add new translation keys as features are developed

## Next Steps

1. Replace hardcoded strings in all components with `t()` function calls
2. Test language switching across all pages
3. Add new translation keys as new features are implemented
4. Consider adding missing Indian languages (Malayalam, etc.) if needed
5. Implement RTL support for future languages (Arabic, Urdu, etc.)

## Troubleshooting

**Issue**: Language not changing after selection
- Solution: Clear browser localStorage and try again

**Issue**: Missing translation key shows as `common.missingKey`
- Solution: Add the key to all language translation files

**Issue**: i18n not initialized on app startup
- Solution: Ensure `import './locales/i18n'` is in `main.jsx` before app renders

## Resources

- [i18next Documentation](https://www.i18next.com/)
- [react-i18next Documentation](https://react.i18next.com/)
- [Translation File Format](https://www.i18next.com/misc/json-format)
- [Translation Maintenance Guide](../../Docs/TRANSLATION_MAINTENANCE.md) - **Read this for adding/modifying UI elements**
