# Contributing to Swaya.me

Thank you for contributing to Swaya.me! This guide helps you understand our development workflow and standards.

## Code of Conduct

- Be respectful and inclusive
- Focus on the code, not the person
- Help others learn and grow
- Report issues constructively

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Follow the guidelines below
5. Submit a pull request

## Development Guidelines

### Frontend Development

#### UI Elements & Internationalization (i18n)

**CRITICAL**: Every time you add or modify user-facing text in the UI, you **MUST** update the translation files for all 7 supported languages.

**Supported Languages**:
- English (en) - Default
- Hindi (hi)
- Tamil (ta)
- Telugu (te)
- Kannada (ka)
- Bengali (bn)
- Gujarati (gu)

**Steps**:

1. **Plan translations**: Before coding, identify all text strings in your UI
2. **Update English first**: Add keys to `frontend/src/locales/en/translation.json`
3. **Translate to all languages**: Add same keys to all 6 other language files with translations
4. **Use i18n in components**: 
   ```jsx
   import { useTranslation } from 'react-i18next'
   
   function MyComponent() {
     const { t } = useTranslation()
     return <button>{t('section.key')}</button>
   }
   ```
5. **Test in all languages**: Use the language switcher to verify all 7 languages work

**Quick Reference**:
- [Translation Maintenance Guide](./Docs/TRANSLATION_MAINTENANCE.md) - Complete walkthrough
- [Translation Checklist](./TRANSLATION_CHECKLIST.md) - Quick reference
- [i18n Implementation](./frontend/docs/I18N_IMPLEMENTATION.md) - Technical details

#### Code Style

- Use functional components with hooks
- Follow Ant Design patterns for UI
- Use Redux Toolkit for state management
- Keep components focused and reusable
- Add comments for complex logic

#### Testing

- Test UI in all supported languages
- Verify responsive design across devices
- Check Ant Design locale switching works
- Test error states and edge cases

### Backend Development

#### Python Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Keep functions focused and testable
- Document complex business logic

#### API Design

- RESTful endpoints
- Consistent error response format
- Request/response validation with Pydantic
- JWT authentication for protected routes

#### Testing

- Unit tests for business logic
- Integration tests for API endpoints
- Mock external dependencies
- Target >80% code coverage

### Database Changes

1. Create a migration: `alembic revision --autogenerate -m "description"`
2. Review generated migration file
3. Test migration up and down
4. Document schema changes

## Pull Request Process

### Before Submitting

1. **Update documentation**: If adding a feature, document it in Docs/
2. **Update translations**: If adding UI text, update all 7 language files
3. **Run tests**: Ensure all tests pass locally
4. **Verify build**: Run `npm run build` (frontend) or `python -m pytest` (backend)
5. **Check linting**: Fix any lint errors

### PR Checklist

- [ ] Branch name follows convention: `feature/name` or `fix/name`
- [ ] Commit messages are clear and descriptive
- [ ] Updated relevant documentation
- [ ] **All 7 language files updated** (if UI changes)
- [ ] Tests added or updated
- [ ] No hardcoded strings (use i18n keys)
- [ ] Code follows style guidelines
- [ ] No breaking changes documented

### PR Title Format

```
[AREA] Brief description (50 chars max)
```

Examples:
- `[Frontend] Add language switcher to auth pages`
- `[Backend] Fix quiz session timeout logic`
- `[Docs] Update architecture documentation`

Areas: `Frontend`, `Backend`, `Docs`, `Infra`, `Chore`

### PR Description Template

```markdown
## Description
Brief explanation of what this PR does.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issue
Closes #123 (if applicable)

## Testing
How to test these changes:
1. Step 1
2. Step 2

## Screenshots (if UI changes)
[Add screenshots here]

## Translation Updates
- [ ] English (en) - UPDATED/N/A
- [ ] Hindi (hi) - UPDATED/N/A
- [ ] Tamil (ta) - UPDATED/N/A
- [ ] Telugu (te) - UPDATED/N/A
- [ ] Kannada (ka) - UPDATED/N/A
- [ ] Bengali (bn) - UPDATED/N/A
- [ ] Gujarati (gu) - UPDATED/N/A
```

## Common Workflow Examples

### Adding a New Button to Quiz Screen

1. **Add translation keys** (before coding):
   ```json
   // en/translation.json
   { "quiz": { "exportResults": "Export Results" } }
   ```

2. **Add to all 6 language files** with translations

3. **Update component**:
   ```jsx
   const { t } = useTranslation()
   return <Button>{t('quiz.exportResults')}</Button>
   ```

4. **Test all languages**: Switch language switcher and verify text appears

5. **Commit**: Include all translation file changes

### Fixing a Backend Bug

1. Write a failing test that reproduces the bug
2. Implement the fix
3. Verify test passes
4. Update documentation if behavior changes
5. Submit PR with test and fix together

### Updating Documentation

1. Clarify existing docs or fix errors
2. Add examples if needed
3. Keep consistent with style
4. Link related docs
5. Update version date if major changes

## Architecture Guidelines

### Follow the 3-Layer Model

```
Services → Platform → Features
```

- **Services**: API and realtime transport only
- **Platform**: Orchestration, auth, policies, tier enforcement
- **Features**: Business logic (quiz creation, session management, etc.)

See [Docs/logical_architecture.md](./Docs/logical_architecture.md)

### Multi-Tenant Requirements

- All domain tables must have `tenant_id` foreign key
- Platform handles tenant context resolution
- Features work with scoped data only

## Commit Message Guidelines

```
[Area] Imperative, present tense (50 chars max)

[Optional] Longer explanation in present tense.
Explain what and why, not how.

Fixes #123
```

Examples:
```
[Frontend] Add language switcher component
[i18n] Update Tamil translations for quiz builder
[Backend] Fix session timeout race condition
[Docs] Add translation maintenance guide
```

## Filing Issues

### Bug Report

```
Title: [BUG] Brief description
Description:
- What happens
- What should happen
- Steps to reproduce
- Environment (OS, browser, versions)
```

### Feature Request

```
Title: [FEATURE] What you want
Description:
- Why it's needed
- How it should work
- Who benefits
- Acceptance criteria
```

### Documentation Request

```
Title: [DOCS] What's unclear
Description:
- What you tried to understand
- What was confusing
- Where the docs are
- Suggested improvement
```

## Release Process

1. **Version bump**: Update version in `package.json` (frontend) and `version.py` (backend)
2. **Update CHANGELOG**: Document all changes
3. **Tag release**: `git tag v1.2.3`
4. **Build**: `npm run build` (frontend), prepare Docker images (backend)
5. **Deploy**: Follow [DEPLOYMENT.md](./DEPLOYMENT.md)
6. **Verify**: Test critical paths in production

## Getting Help

- **Questions**: Start a discussion in the repo
- **Bugs**: File an issue with details
- **Design help**: Comment on related PR/issue
- **Architecture questions**: See [Docs/](./Docs/) for architecture docs

## Recognition

Contributors will be acknowledged in:
- CHANGELOG.md
- GitHub contributors page
- Project appreciation list

Thank you for improving Swaya.me! 🙏

---

**Last Updated**: February 10, 2026  
**Maintained By**: Swaya.me Core Team
