# Generate with AI — Reimagined
**Status:** Planning  
**Author:** Product + Engineering  
**Date:** 2026-06-14

---

## 1. Executive Summary

The current "Generate with AI" feature is a narrow MCQ factory: it accepts a text prompt, returns 4-option multiple-choice questions, and dumps them into the quiz. It ignores poll/survey types entirely, leaves quiz title/description for the user to fill manually, never applies code formatting unless Gemini decides to, and has zero image intelligence.

The reimagined version is a **one-prompt quiz architect** — you describe what you want in plain language, and the AI builds a complete, correctly formatted, quiz-type-appropriate experience ready to launch. The user's job becomes reviewing and approving, not filling forms.

---

## 2. Current State — What's Actually Broken

### 2.1 Broken for 2 of 4 quiz types

The AI modal is gated behind `!isPoll`, so it is inaccessible when quiz type is **poll** or **offline poll**. These types support richer question types (word cloud, scale, paragraph, one-word) that AI could handle better than MCQ anyway — a live poll benefits from open-ended word cloud questions, and a survey benefits from Likert scale + open paragraph questions.

| Type | AI Access Today | Should Be |
|---|---|---|
| Quiz (Live) | ✅ MCQ only | ✅ MCQ, + smart mix option |
| Exam (Test) | ✅ MCQ only | ✅ MCQ + difficulty/time/marks auto-set |
| Poll (Live) | ❌ Hidden | ✅ Word cloud + MCQ mix |
| Offline Poll (Survey) | ❌ Hidden | ✅ Scale + MCQ + paragraph mix |

### 2.2 Doesn't create anything from scratch

The user must:
- Type a title manually
- Write a description manually
- Set question count manually (in two different places: CreateChooser and the modal)
- Set quiz settings (time limit for exams, negative marks) manually

The AI has everything it needs from the prompt to infer all of this, but it only generates question bodies.

### 2.3 Formatting is accidental, not intentional

Gemini's system prompt instructs it to use `<pre><code class="language-X">` for code. This works — but only when the AI decides it's relevant. The user has no way to signal "this is a Python quiz, please format all code snippets properly." If someone writes "10 questions on SQL JOIN clauses" the AI may or may not format them. There is no guaranteed formatting category.

### 2.4 Images never appear

The Question model has `question_image_url` and `option_images` (per-option images). The upload infrastructure exists. But no AI path ever touches these fields — the only path to images is manual upload. For visual subjects (anatomy diagrams, circuit diagrams, geography maps, graph-reading questions) this is a major gap.

---

## 3. Proposed Changes — Prioritised

### Priority 1 (Fix Now — High Impact, Feasible)

#### P1-A: One-Shot Quiz Creation
**What:** A single enhanced prompt generates quiz title, description, and questions in one call.  
**How:** Expand the Gemini response schema to include `title` and `description` at the top level. The frontend pre-fills quiz metadata fields from the AI response before questions are added.

Backend change in `gemini_service.py`:
```python
# Current output schema
{"questions": [...]}

# New output schema
{
  "title": "10 Essential Python Decorator Questions",
  "description": "Tests understanding of Python decorators, closures, and functools.wraps for intermediate Python developers.",
  "questions": [...]
}
```

Frontend: after preview is confirmed, call `quizAPI.update(id, { title, description })` before adding questions.

**Effort:** Small. 1 backend function change + 3 lines of frontend state.

---

#### P1-B: AI for Polls and Offline Polls
**What:** Remove the `!isPoll` gate on the AI button. For poll types, pass `quiz_type` to the AI and have it generate appropriate question types.

**How:** Add `quiz_type` to the generation request. Backend returns a `question_type` field per question alongside a `question_format` hint.

For **Live Poll**: AI generates a mix of:
- `word_cloud` questions (open-ended, short-answer e.g. "What one word describes your leadership style?")
- `mcq` questions (audience opinion polls)

For **Offline Poll/Survey**: AI generates:
- `scale` questions (Likert e.g. "Rate your satisfaction with onboarding: 1-5")
- `paragraph` questions (open-ended e.g. "What could we improve?")
- `mcq` questions (demographics, preference choices)

**Effort:** Medium. Backend: add `quiz_type` param + branch in system prompt. Frontend: unhide button, handle non-MCQ question types in `handleAiAddSelected`.

---

#### P1-C: Formatting Mode ("Code-Aware Generation")
**What:** Add a "Content type" selector in the AI modal that injects a formatting instruction into the prompt sent to Gemini.

Options:
| Label | Internal key | Injected instruction |
|---|---|---|
| General | `general` | (none, current behaviour) |
| Programming / Code | `code` | "Format all code samples using appropriate HTML code blocks with the correct language class (e.g. language-python, language-sql, language-java). Every question with code must use <pre><code class='language-X'>." |
| Math / Science | `math` | "Use plain Unicode for mathematical expressions (e.g. ≥, ², √). Keep formulas readable without LaTeX." |
| Data / SQL | `sql` | "All SQL queries and schemas must be in SQL code blocks. Show table structure as CREATE TABLE or SELECT examples." |
| Visual / Diagram | `visual` | "Describe what the diagram should show in the question text and ask the student to identify elements from it." |

This requires zero backend changes — it's a frontend-only prompt injection before calling the API.

**Effort:** Tiny. Add a `<Select>` component in the modal, prepend the formatting hint to `aiTopic` before the API call.

---

#### P1-D: Exam-Aware Question Attributes
**What:** For exam-type quizzes, generated questions should receive appropriate `points`, `negative_points`, and `max_time_seconds` values based on a **difficulty** selector added to the AI modal.

Difficulty → auto-set values:
| Difficulty | Points | Neg Marks | Time per Q |
|---|---|---|---|
| Easy | 1 | 0 | 45s |
| Medium | 2 | 0.5 | 60s |
| Hard | 4 | 1 | 90s |

Currently all generated questions are hardcoded to 1 point, 0 neg marks, null time. For exams this is particularly wrong.

**Effort:** Small. Frontend-only: pass difficulty values when calling `questionAPI.add()` inside `handleAiAddSelected`.

---

### Priority 2 (High Impact, More Work)

#### P2-A: Edit-in-Preview (Inline Editing Before Adding)
**What:** In the preview step, each generated question should be editable before it's committed to the quiz. Currently the user must add, then go back and edit each question individually.

Each question card in preview gets:
- Click-to-edit question text
- Click-to-edit each option
- Toggle to mark/unmark correct answer
- Regenerate-this-question button (re-calls AI with same prompt but explicitly asks to replace this one question)

**Why this is huge:** The biggest friction point is incorrect options or poorly worded questions. Users currently have to add all, then find each bad one, edit it, and save. Inline editing makes it a one-screen flow.

**Effort:** Medium–Large. Add edit state to each preview card + a `regenerateOne()` handler that calls the API with `count: 1` and a `context` of the original question.

---

#### P2-B: Smart Image Suggestion (Phase 1 — Prompt-Based)
**What:** After questions are generated, an optional "Suggest images" step uses the question text to generate a web search query, then links the user to image search for each question that benefits from a visual.

This does NOT download or auto-embed images (copyright and storage concerns). Instead:
- AI identifies which questions benefit from an image (diagram, map, graph, chart)
- For each such question, shows a "Find image for this" button with a pre-filled image search query
- User can then upload an image they find

**Backend:** Add a lightweight post-processing pass that flags questions where an image would add value and suggests a search query string.

**Effort:** Medium. New AI call (or extend the generation call to return `"image_suggestion": "diagram of photosynthesis process"` per question).

---

#### P2-C: Streaming Generation (Real-Time Preview)
**What:** Questions appear in the preview list one by one as they're generated, rather than all at once after a 5-15 second wait.

Currently: user stares at a spinner for up to 15 seconds.  
With streaming: first question appears in ~2 seconds, rest trickle in — UX feels instant.

**How:** Switch Gemini call to streaming mode. Backend sends SSE (Server-Sent Events) or chunked JSON. Frontend renders each question as it arrives.

**Effort:** Large. Requires SSE endpoint + frontend EventSource or fetch-stream reader + incremental JSON parsing. Worth doing for the "wow" factor.

---

### Priority 3 (Future)

#### P3-A: Smart Re-Generation with Context
After a quiz has questions, re-opening the AI modal should:
- Show existing questions in the system prompt as "already covered topics" 
- Instruct AI not to duplicate or contradict existing questions
- Surface a diff view showing only the new additions

#### P3-B: Voice Prompt Input
Allow the user to speak their prompt instead of typing. Browser Web Speech API captures the audio → converted to text → populates the prompt textarea. Especially useful on mobile.

#### P3-C: AI-Generated Exam Settings
For exam type: after generation, AI suggests exam window (start time, end time) and whether to enable proctoring based on the difficulty level and audience description in the prompt.

#### P3-D: Template-Aware Generation
Prompt includes existing quiz templates (UPSC, JEE, IELTS patterns) as style references. User selects "Style: UPSC MCQ" and AI mimics the question structure, language, and difficulty distribution.

---

## 4. The Target UX — "One Prompt, Complete Quiz"

### Entry: Create Chooser

```
┌─────────────────────────────────────────────────────────────────┐
│  What do you want to create?                                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Generate with AI                                          │  │
│  │                                                           │  │
│  │ Describe your quiz in plain language:                     │  │
│  │ ┌───────────────────────────────────────────────────┐    │  │
│  │ │ 12 questions on SQL JOINs for a data analyst      │    │  │
│  │ │ hiring test. Medium difficulty. Format all SQL    │    │  │
│  │ │ code properly. 2 points each, 90 seconds per Q.   │    │  │
│  │ └───────────────────────────────────────────────────┘    │  │
│  │                                                           │  │
│  │ Type:  [Quiz ▼]    Difficulty:  [Medium ▼]               │  │
│  │                                                           │  │
│  │          [✨ Generate Complete Quiz]                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Or start blank:  [Quiz]  [Poll]  [Test]  [Survey]            │
└─────────────────────────────────────────────────────────────────┘
```

### Generation: Streaming Preview

```
┌────────────────────────────────────────────────────┐
│ ✨ Generating your quiz...                         │
│                                                    │
│ 📋 SQL JOINs Data Analyst Assessment               │  ← Title generated
│ 12 questions · Medium · 90s each · 2 pts          │  ← Settings applied
│                                                    │
│ ✅ Q1: Which JOIN returns all rows from the...    │  ← Questions stream in
│ ✅ Q2: Given the schema below, what does this...  │
│ ⏳ Generating Q3...                               │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Review: Inline Edit Before Committing

```
┌────────────────────────────────────────────────────────────────┐
│ ← Back    Review 12 Questions    ✓ All    ✗ None              │
│                                                                │
│ ┌──────────────────────────────────────────────────── [✓] ┐  │
│ │ Q1: Which SQL JOIN returns only rows where condition... │  │
│ │                                                          │  │
│ │ ● A. INNER JOIN       ← correct                        │  │
│ │ ○ B. LEFT JOIN                                         │  │
│ │ ○ C. CROSS JOIN                                        │  │
│ │ ○ D. FULL OUTER JOIN                                   │  │
│ │                                                          │  │
│ │ [✏️ Edit]  [🔄 Regenerate]  [🖼 Add Image]             │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                                │
│ ┌──────────────────────────────────────────────────── [✓] ┐  │
│ │ Q2:                                                      │  │
│ │ <pre><code class="language-sql">                        │  │
│ │ SELECT e.name, d.dept_name                              │  │
│ │ FROM employees e                                        │  │
│ │ LEFT JOIN departments d ON e.dept_id = d.id             │  │
│ │ </code></pre>                                           │  │
│ │ What will this query return if an employee has no...    │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                                │
│           [Add 12 Questions to Quiz →]                        │
└────────────────────────────────────────────────────────────────┘
```

---

## 5. Implementation Plan

### Sprint 1 — Fix the Gaps (P1-A through P1-D)

**Backend changes:**
1. `gemini_service.py` — Expand `generate_questions()` response to include `title` and `description`. Update JSON schema in system prompt.
2. `gemini_service.py` — Accept `quiz_type` parameter. Branch system prompt: polls get word_cloud/scale instructions, exams get MCQ + difficulty context.
3. `ai.py` — Pass `quiz_type` from request to service. Return `question_type` per generated question.

**Frontend changes:**
1. `QuizBuilder.jsx` — Remove `!isPoll` gate on AI button. Show it for all quiz types.
2. `QuizBuilder.jsx` — Add "Content type" `<Select>` in AI modal (`general`, `code`, `sql`, `math`). Prepend formatting hint to prompt before API call.
3. `QuizBuilder.jsx` — For exam type: add "Difficulty" selector. Pass per-question `points`, `negative_points`, `max_time_seconds` based on difficulty when calling `questionAPI.add()`.
4. `QuizBuilder.jsx` — After `handleAiAddSelected`, call `quizAPI.update(id, { title, description })` with AI-generated values (with user confirmation).
5. `handleAiAddSelected` — Handle `question_type: 'word_cloud'` and `question_type: 'scale'` from AI response, not just MCQ.
6. `CreateChooser.jsx` — Surface "Quiz Type" and "Difficulty" selectors in the AI prompt section so they can be set before navigating to the builder.

**Locale files (all 11):**
- `ai.contentTypeLabel`, `ai.contentTypeGeneral`, `ai.contentTypeCode`, `ai.contentTypeSQL`, `ai.contentTypeMath`
- `ai.difficultyLabel`, `ai.difficultyEasy`, `ai.difficultyMedium`, `ai.difficultyHard`
- `ai.quizTitleGenerated` (toast: "AI suggested a title — updated")

---

### Sprint 2 — Edit in Preview (P2-A)

- Replace read-only question cards in preview step with editable Antd Form fields.
- Add per-question `[Regenerate]` button that calls `aiAPI.generateQuestions({ prompt: aiTopic, count: 1, context: originalQuestion })` and swaps just that card.
- Track dirty state per card so "Add to Quiz" submits the edited version, not the original.

---

### Sprint 3 — Streaming + Images (P2-B, P2-C)

**Streaming:**
- New endpoint `POST /ai/generate/questions/stream` returns `text/event-stream`.
- Each SSE event is one complete question JSON object.
- Frontend uses `EventSource` (or `fetch` with `ReadableStream`). Questions render into preview list as they arrive.
- Loading state becomes a progress bar with "Generated X of N".

**Image suggestions:**
- Extend Gemini schema with optional `"image_query": "..."` field per question.
- Frontend shows a "🔍 Find image" button on preview cards where `image_query` is non-null.
- Clicking opens the `ImageUpload` component with the search query pre-filled as a caption hint.

---

## 6. What NOT to Build

- **Auto-download images from the web** — copyright risk, storage overhead, content moderation nightmare. Suggest + link, don't fetch.
- **AI-generated exam schedule** — too contextual, users know their own dates.
- **Fully autonomous "one-click publish"** — always keep a human review step. Auto-generation without review erodes trust if even one question is wrong.

---

## 7. Success Metrics

| Metric | Current | Target (after Sprint 1) |
|---|---|---|
| Avg time to first published quiz via AI | ~8 min | < 3 min |
| AI modal usage rate (% of quiz creates) | Baseline TBD | +40% |
| Poll/Offline poll AI adoption | 0% | > 20% |
| Formatted code questions out of AI | ~40% of coding quizzes | > 90% |
| User edits per generated question after add | Baseline TBD | -50% |
