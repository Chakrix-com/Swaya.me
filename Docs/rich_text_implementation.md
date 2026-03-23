# Rich Text Question Editor — Implementation Checklist

> **Status:** ✅ Complete
> **Date:** 2026-03-22

---

## Context

Currently every question in Swaya.me (across Online Quiz, Poll, Exam) is authored in a plain 2-row `<TextArea>`. This blocks CS exam use cases (code output questions), questions with emphasis/lists, etc.

**Goal:** Add an expandable rich text editor with bold/italic/underline, bullet/numbered lists, and code blocks with language-aware syntax highlighting — working across all 11 locales, day/night mode, and all question types (Quiz, Poll, Exam).

**Approach chosen:** Tiptap v2 (ProseMirror-based, MIT license) — best IME support for Indian-language locales, zero participant-facing bundle impact via Vite code splitting.

---

## Phase 1 — npm Packages

- [x] Install in `frontend/`:
  ```
  @tiptap/react
  @tiptap/starter-kit
  @tiptap/extension-code-block-lowlight
  @tiptap/extension-placeholder
  lowlight
  ```
- [x] Confirm `npm install` resolves without errors
- [x] Update `frontend/package.json` committed

---

## Phase 2 — RichTextEditor Module

- [x] Create `frontend/src/features/quiz/components/RichTextEditor.jsx`
  - Props: `value`, `onChange`, `placeholder`, `lang`, `isDark`, `disabled`
  - `useEditor` with: `StarterKit`, `CodeBlockLowlight.configure({ lowlight })`, `Placeholder`
  - Toolbar buttons (Ant Design): **B** bold, _I_ italic, U underline, bullet list, ordered list, `<>` code block
  - Code block language selector: `Select` dropdown (Python, Java, C, C++, JavaScript, TypeScript, Shell/Bash, Go, Rust, SQL, HTML, CSS)
  - Wrapper: `<div className="rte-wrap rte-wrap--{light|dark}">`
  - Plain-text `value` on mount → Tiptap wraps in `<p>` automatically (backward compat)

- [x] Create `frontend/src/features/quiz/components/RichTextEditor.css`
  - `.rte-wrap` — border + border-radius matching Ant Design Input
  - `.rte-toolbar` — flex row of format buttons
  - `.rte-content .ProseMirror` — min-height, padding, focus outline
  - Code block colors (static CSS, no runtime highlight.js imports):
    - Light: `pre { background: #f6f8fa; color: #24292e; }`
    - Dark: `pre { background: #1e1e2e; color: #cdd6f4; }`
    - ~12 token types × 2 themes (keyword, string, comment, number, function, etc.)

---

## Phase 3 — RichTextRenderer Module

- [x] Create `frontend/src/features/quiz/components/RichTextRenderer.jsx`
  - Props: `content`, `isDark`, `className`
  - Zero Tiptap dependency — pure `dangerouslySetInnerHTML` render
  - Wrapper: `<div className="rte-rendered rte-rendered--{light|dark} {className}">`
  - Plain text (no HTML tags) renders correctly via browser text nodes

- [x] Create `frontend/src/features/quiz/components/RichTextRenderer.css`
  - `.rte-rendered` — typography (line-height, font-size, word-break)
  - `strong`, `em`, `ul`, `ol` — minimal resets for Ant Design compat
  - `pre` — monospace font, border-radius, padding, overflow-x: auto
  - Light/dark code block colors matching RichTextEditor.css

---

## Phase 4 — QuizBuilder Integration

**File:** `frontend/src/features/quiz/QuizBuilder.jsx`

- [x] Import `RichTextEditor` and `useContext(VisitorThemeContext)`
- [x] Add state `const [useRichText, setUseRichText] = useState(false)` inside `QuestionForm`
- [x] On `useEffect` when loading existing question: auto-detect HTML — `/<[a-z][\s\S]*>/i.test(question.text)` → `setUseRichText(true)`
- [x] Add "Rich Text / Simple" toggle button next to question label
- [x] When `useRichText === false`: keep existing `<TextArea rows={2}>` unchanged
- [x] When `useRichText === true`: swap to `<RichTextEditor>` via `Form.Item` with `getValueFromEvent={(v) => v}`
- [x] AI rewrite button: strip HTML tags before sending (`text.replace(/<[^>]*>/g, '')`) then re-set editor content with plain-text response

---

## Phase 5 — Participant & Presenter Views

Replace plain-text `question.text` renders with `<RichTextRenderer>`:

- [x] `frontend/src/features/audience/AudienceSession.jsx` (~line 532)
  - Replace `<Title level={3}>{currentQuestion.text}</Title>`
  - With `<RichTextRenderer content={currentQuestion.text} isDark={theme==='dark'} />`

- [x] `frontend/src/features/offline-poll/OfflinePollSession.jsx` (~line 377)
  - Replace `<Title level={4}>{question.text}</Title>`
  - With `<RichTextRenderer content={question.text} isDark={theme==='dark'} />`

- [x] `frontend/src/features/exam/ExamSession.jsx` (~line 273)
  - Replace `<Title level={4}>{question.text}</Title>`
  - With `<RichTextRenderer content={question.text} isDark={theme==='dark'} />`

- [x] `frontend/src/features/quiz/QuizPresent.jsx` (lines ~131 and ~186)
  - Replace `<p>{question.text}</p>` (both occurrences)
  - With `<RichTextRenderer content={question.text} isDark={true} />` (always dark — presenter has dark gradient)

---

## Phase 6 — Backend Schema

**File:** `backend/features/quiz/schemas.py`

- [x] `QuestionCreate.text`: `max_length=1000` → `max_length=10000`
- [x] `QuestionUpdate.text`: same change
- [x] Add XSS validator to `QuestionCreate`:
  ```python
  @validator('text')
  def no_script_tags(cls, v):
      import re
      if re.search(r'<script|<iframe|on\w+\s*=', v, re.I):
          raise ValueError('Question text contains disallowed HTML')
      return v
  ```

- [x] Create documentation-only Alembic migration:
  `backend/persistence/migrations/versions/20260322_1200_rich_text_question.py`
  (No DDL — MySQL `TEXT` column already supports 65 KB)

---

## Phase 7 — i18n Keys

Add to all 11 locale files (`frontend/src/locales/{en,hi,ta,te,ka,bn,gu,es,fr,de,ru}/translation.json`) under `"quiz"`:

- [x] `en/translation.json`
- [x] `hi/translation.json`
- [x] `ta/translation.json`
- [x] `te/translation.json`
- [x] `ka/translation.json`
- [x] `bn/translation.json`
- [x] `gu/translation.json`
- [x] `es/translation.json`
- [x] `fr/translation.json`
- [x] `de/translation.json`
- [x] `ru/translation.json`

Keys to add — **every visible label, tooltip, placeholder, and dropdown option must be translated in all 11 locales**. No hardcoded English strings in JSX. Non-English locales may start with English fallback text initially (consistent with `exam.*` pattern) but the key must exist in every locale file.

```json
"richTextToggle": "Rich Text",
"simpleTextToggle": "Simple",
"boldTooltip": "Bold",
"italicTooltip": "Italic",
"underlineTooltip": "Underline",
"bulletListTooltip": "Bullet list",
"orderedListTooltip": "Numbered list",
"codeBlockTooltip": "Code block",
"codeLanguageSelect": "Select language"
```

Language dropdown options (Python, Java, C, C++, JavaScript, TypeScript, Shell/Bash, Go, Rust, SQL, HTML, CSS) are code/technical names — these are **not translated** (universally understood as-is).

---

## Phase 8 — Build & Deploy

- [x] `cd frontend && npm run build` — no bundle errors
- [x] Confirm `RichTextEditor` does NOT appear in participant-facing Vite chunks
- [x] `sudo systemctl restart swayame-backend-test.service`
- [x] Smoke test on test.swaya.me

---

## Verification Checklist

- [x] Create a new Online Quiz question → toggle "Rich Text" → author bold text + Python code block → save → reopen → still in Rich Text mode
- [x] Join quiz as audience → code block renders with syntax highlighting in **light** mode
- [x] Join quiz as audience → code block renders with syntax highlighting in **dark** mode
- [x] Open existing plain-text question → auto-opens in Simple mode (no HTML artefacts)
- [x] Existing plain-text question renders correctly in AudienceSession (no formatting broken)
- [x] Exam page (`/e/:slug`) — code block question renders correctly
- [x] Offline Poll — code block question renders correctly
- [x] QuizPresent (presenter view) — code block renders on big screen
- [x] Switch UI to Hindi — toolbar tooltips appear (English fallback is fine)
- [x] Backend: POST question with `<script>` in text → 422 response
- [x] `npm run build` — RichTextEditor not in participant chunk (check chunk filenames)

---

## Standing Rules (Apply to All New UI in This Feature)

### 1. Translation — All Labels in All 11 Languages
Every user-visible string (labels, tooltips, placeholders, button text, status messages) **must** have an i18n key and appear in all 11 locale files:
`en, hi, ta, te, ka, bn, gu, es, fr, de, ru`

- No hardcoded English strings in JSX — always use `t('quiz.keyName')`
- Non-English locales may start with English fallback text but the key must exist in every file
- Exception: code language names (Python, Java, etc.) — technical terms, not translated

### 2. Day/Night Mode — Match Existing Look & Feel Exactly
All new UI elements must behave identically to current public pages (`AudienceSession`, `OfflinePollSession`, `ExamSession`) in both modes:

- Use `--visitor-page-bg`, `--visitor-text-primary`, `--visitor-text-secondary`, `--ctrl-radio-option-border` and other `--visitor-*` / `--ctrl-*` CSS variables already defined in `index.css`
- Do **not** hardcode colors (no `#fff`, `#000`, `#1677ff` etc. in inline styles or CSS)
- The `isDark` prop drives `.rte-wrap--dark` / `.rte-wrap--light` class on the editor wrapper — same pattern as `.visitor-theme--dark` / `.visitor-theme--light` on public page roots
- Toolbar buttons: use `var(--visitor-text-primary)` for icon color so they invert correctly
- Focus outlines, borders, placeholder text: all via CSS variables matching Ant Design's dark/light token system
- Test both modes via Selenium on test.swaya.me before marking any phase complete

---

## Design Decisions (Confirmed)

| Decision | Choice |
|---|---|
| Editor library | Tiptap v2 (MIT, ProseMirror) |
| Code block editing | Inline (cursor enters block directly — no modal) |
| Storage format | HTML in existing `text` column (no DB migration) |
| Existing questions | Auto-detect: HTML in text → Rich Text mode; else Simple mode |
| Syntax highlighting | Tiptap `CodeBlockLowlight` + `lowlight` (static CSS tokens) |
| Participant bundle | `RichTextRenderer` has zero Tiptap imports (Vite splits at import) |
| Dark mode | CSS classes `.rte-wrap--dark` / `.rte-rendered--dark` |
| Default mode | Simple textarea (toggle required to expand — non-breaking) |
| Presenter view | Yes — `RichTextRenderer` in `QuizPresent.jsx` |
| DB column | No change — MySQL `TEXT` handles 65 KB; only Pydantic `max_length` changes |
