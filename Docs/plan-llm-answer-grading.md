# Plan — LLM Semantic Answer Grading for Single-Line Questions

> **Status:** Draft — not yet implemented
> **Date:** 2026-03-25

---

## Problem

Single-line and paragraph text answers are currently graded by an **exact string match** (case-insensitive, whitespace-stripped):

```python
# backend/features/quiz/answer_service_async.py  lines 228–230
response_clean = request.text_answer.strip().lower()
expected_clean = str(expected_answer).strip().lower()
is_correct = (response_clean == expected_clean)
```

This fails on:
- Minor spelling mistakes — `"photosinthesis"` vs `"photosynthesis"` → marked wrong
- Synonyms / paraphrasing — `"H2O"` vs `"water"` → marked wrong
- Extra articles / punctuation — `"the mitochondria"` vs `"mitochondria"` → marked wrong
- Different word order — `"Newton Isaac"` vs `"Isaac Newton"` → marked wrong

---

## Proposed Solution

Replace the exact-match line with a call to the **existing local Ollama LLM** (already used for the "Rewrite with AI" feature) to semantically judge whether the participant's answer conveys the same meaning as the expected answer.

The LLM returns a strict `YES` / `NO` verdict. If it cannot be reached (Ollama down, timeout) the system falls back gracefully to the original exact-match so grading never silently breaks.

---

## Scope

| Question type | Current grading | After this change |
|---|---|---|
| `SINGLE_LINE` | Exact match | LLM semantic match (with exact-match fallback) |
| `PARAGRAPH` | Exact match | LLM semantic match (with exact-match fallback) |
| `MCQ` | Index comparison | **Unchanged** |
| `WORD_CLOUD` | Not graded | **Unchanged** |
| `SCALE` | Not graded | **Unchanged** |

Only affects questions where the host has set an expected answer (`options[0]` is non-empty).

---

## LLM Details

| Property | Value |
|---|---|
| Provider | Ollama (local, on-premises — `http://127.0.0.1:11434`) |
| Model | `llama3.2:1b` — the existing fast/rewrite model (same as "Rewrite with AI") |
| No API key | Runs entirely on the same VM, no external calls |
| Existing client | `backend/core/ai/ollama_service.py` → `_generate()` |

Using `llama3.2:1b` (not the 3b model) to keep latency low — answer submission is a real-time, participant-facing action.

---

## LLM Prompt Design

```
You are a quiz answer grader.

Expected answer: {expected_answer}
Participant answer: {participant_answer}

Does the participant's answer convey the same meaning as the expected answer,
allowing for minor spelling mistakes, synonyms, different word order, or
extra/missing articles?

Reply with exactly one word: YES or NO.
```

**Why this prompt works well:**
- Single-token output — fast and deterministic to parse
- Explicitly lists the tolerances (spelling, synonyms, word order, articles)
- "Exactly one word" instruction minimises the chance of the model adding explanation text

**Response parsing rule:** Strip the response, take the first word, uppercase it. Accept `YES` as correct, anything else (including `NO`, empty, or garbage) as incorrect. This is the safe default — ambiguous = not correct.

---

## Fallback Strategy

```
LLM available?
  YES → use LLM verdict (YES → correct, NO/other → incorrect)
  NO  → fall back to exact match (current behaviour)
       → log a WARNING so the operator knows grading degraded
```

Fallback triggers on: `OllamaError` (daemon unreachable), `httpx.TimeoutException`, or any unexpected exception. Grading always produces a result — it never raises an error to the participant.

---

## Performance Considerations

- `llama3.2:1b` on CPU typically responds in **1–4 seconds** on the production VM.
- The existing 120-second timeout on `_generate()` is generous — a tighter **8-second timeout** will be used for answer grading to keep the participant UX acceptable.
- The answer submission endpoint (`submit_word_cloud_answer`) is already `async` — the LLM call fits naturally as an `await`.
- If latency becomes a concern in future, answers could be graded asynchronously (submit immediately, grade in background, update `is_correct` post-hoc). **This plan uses synchronous grading for simplicity** — revisit only if real-world latency is a problem.

---

## Implementation Plan

### Step 1 — Add `grade_text_answer()` to `ollama_service.py`

**File:** `backend/core/ai/ollama_service.py`

Add a new public async function at the bottom of the file:

```python
GRADING_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

async def grade_text_answer(participant_answer: str, expected_answer: str) -> bool:
    """
    Use the LLM to semantically compare a participant's text answer against
    the expected answer. Returns True if the meaning matches, False otherwise.
    Falls back to exact-match comparison if Ollama is unavailable.
    """
    prompt = (
        "You are a quiz answer grader.\n\n"
        f"Expected answer: {expected_answer}\n"
        f"Participant answer: {participant_answer}\n\n"
        "Does the participant's answer convey the same meaning as the expected answer, "
        "allowing for minor spelling mistakes, synonyms, different word order, or "
        "extra/missing articles?\n\n"
        "Reply with exactly one word: YES or NO."
    )
    try:
        raw = await _generate(prompt, FALLBACK_MODEL, temperature=0.0, max_tokens=4, fmt="")
        verdict = raw.strip().split()[0].upper() if raw.strip() else "NO"
        return verdict == "YES"
    except Exception:
        logger.warning(
            "Ollama unavailable for answer grading — falling back to exact match. "
            f"expected={expected_answer!r} participant={participant_answer!r}"
        )
        # Graceful degradation: exact match
        return participant_answer.strip().lower() == expected_answer.strip().lower()
```

Key choices:
- `temperature=0.0` — deterministic output, no creative variation in a grading decision
- `max_tokens=4` — the model only needs to output `YES` or `NO`; 4 tokens is ample and keeps inference fast
- `fmt=""` — plain text output, not JSON
- `GRADING_TIMEOUT` — 10 seconds, tighter than the 120-second default

---

### Step 2 — Replace exact match in `answer_service_async.py`

**File:** `backend/features/quiz/answer_service_async.py`

**Current code (lines 226–230):**
```python
is_correct = None
if is_text_scored and expected_answer:
    response_clean = request.text_answer.strip().lower()
    expected_clean = str(expected_answer).strip().lower()
    is_correct = (response_clean == expected_clean)
```

**Replace with:**
```python
is_correct = None
if is_text_scored and expected_answer:
    from core.ai.ollama_service import grade_text_answer
    is_correct = await grade_text_answer(
        participant_answer=request.text_answer.strip(),
        expected_answer=str(expected_answer).strip(),
    )
```

The import is placed inline (same pattern used elsewhere in this file) to avoid circular imports.

---

### Step 3 — Manual smoke test on test.swaya.me

Create a live quiz with a SINGLE_LINE question. Set expected answer to e.g. `"photosynthesis"`.

Test the following submissions and confirm grading:

| Participant answer | Expected verdict | Reason |
|---|---|---|
| `photosynthesis` | ✓ Correct | Exact match |
| `Photosynthesis` | ✓ Correct | Case difference |
| `photosinthesis` | ✓ Correct | Spelling mistake |
| `the process of photosynthesis` | ✓ Correct | Extra words, same meaning |
| `respiration` | ✗ Wrong | Different concept |
| `I don't know` | ✗ Wrong | No meaningful answer |
| *(empty / spaces only)* | ✗ Wrong | Empty (handled before grading) |

Also test with Ollama daemon stopped to confirm exact-match fallback fires and a WARNING appears in logs.

---

### Step 4 — Deploy

```bash
# Regression gate
BASE_URL=https://test.swaya.me/api/v1 \
APP_BASE_URL=https://test.swaya.me \
HOST_EMAIL=demo@swaya.me \
HOST_PASSWORD=Demo1234 \
bash scripts/regression/run_preprod_gate.sh

# Promote
bash deploy.sh promote-live
bash deploy.sh health
```

---

## Files Changed

| File | Change |
|------|--------|
| `backend/core/ai/ollama_service.py` | Add `GRADING_TIMEOUT` constant + `grade_text_answer()` function |
| `backend/features/quiz/answer_service_async.py` | Replace 2-line exact match with `await grade_text_answer(...)` |

**No schema changes. No migrations. No frontend changes.**

---

## Risks & Notes

- **Latency**: Each SINGLE_LINE/PARAGRAPH answer submission will take 1–4 seconds longer while Ollama infers. This is acceptable for quiz use cases but worth monitoring.
- **Non-determinism**: `temperature=0.0` makes outputs highly consistent, but LLMs can still occasionally vary. In practice `llama3.2:1b` is stable for binary YES/NO prompts.
- **Very long paragraph answers**: The prompt passes the full answer text. Very long PARAGRAPH answers (hundreds of words) could slow inference further. The 10-second timeout will catch runaway cases and fall back to exact match.
- **Ollama model availability**: `llama3.2:1b` must be pulled on the VM (`ollama pull llama3.2:1b`). It is already in use for the rewrite feature so it should already be present.
- **No re-grading of past answers**: Answers already stored with `is_correct` set by the old exact-match logic will not be retroactively re-graded. Only new submissions are affected.
