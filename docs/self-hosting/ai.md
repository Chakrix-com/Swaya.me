# AI Configuration for Self-Hosted Deployments

Swaya.me uses a pluggable AI provider system. You can run with **any combination** of:
- A local LLM via Ollama (no cloud account, no API key, fully private)
- OpenAI, Groq, Azure, Together.ai, LM Studio, or any OpenAI-compatible server
- Google Gemini (default on swaya.me)
- Anthropic Claude

Two env vars control which providers are used:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AI_PRIMARY_PROVIDER` | `gemini` | Question generation, exam analysis, participant summaries |
| `AI_LIGHT_PROVIDER` | `ollama` | Distractor generation, text rewriting, semantic answer grading |

You can use the same provider for both, or mix and match.

---

## Quick-Start: Provider Options

| Provider | Env value | Keys needed | Free tier | Best for |
|----------|-----------|-------------|-----------|----------|
| Google Gemini | `gemini` | `GEMINI_KEY` | Yes (limited) | Best quality, default |
| OpenAI | `openai` or `openai_compat` | `OPENAI_API_KEY` | No | High quality, paid |
| Groq | `openai_compat` | `OPENAI_API_KEY` | Yes (generous) | Fast + cheap cloud |
| Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` | No | High quality alternative |
| Ollama (local) | `ollama` | None | Free | Air-gapped, privacy-first |
| Azure OpenAI | `openai_compat` | `OPENAI_API_KEY` | Enterprise | Enterprise/compliance |
| LM Studio | `openai_compat` | Any string | Free | Local desktop |

---

## Configuration Examples

### Full local — Ollama for everything (no cloud required)

```env
AI_PRIMARY_PROVIDER=ollama
AI_LIGHT_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_FALLBACK_MODEL=qwen2.5:3b
```

Pull the model first: `ollama pull qwen2.5:7b`

**Model recommendations by RAM:**

| RAM | Primary model | Fallback model |
|-----|--------------|----------------|
| 4 GB | `qwen2.5:3b` | `qwen2.5:3b` |
| 8 GB | `qwen2.5:7b` | `qwen2.5:3b` |
| 16 GB | `qwen2.5:14b` | `llama3.1:8b` |
| 32 GB+ | `qwen2.5:32b` | `qwen2.5:14b` |

---

### Groq (fast cloud, generous free tier)

Sign up at [console.groq.com](https://console.groq.com) — no credit card required for free tier.

```env
AI_PRIMARY_PROVIDER=openai_compat
AI_LIGHT_PROVIDER=openai_compat
OPENAI_API_KEY=gsk_...
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.1-70b-versatile
OPENAI_MODEL_FAST=llama-3.1-8b-instant
```

---

### OpenAI

```env
AI_PRIMARY_PROVIDER=openai_compat
AI_LIGHT_PROVIDER=openai_compat
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FAST=gpt-4o-mini
```

---

### Anthropic Claude

```env
AI_PRIMARY_PROVIDER=anthropic
AI_LIGHT_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001
```

---

### Azure OpenAI (enterprise)

```env
AI_PRIMARY_PROVIDER=openai_compat
AI_LIGHT_PROVIDER=openai_compat
OPENAI_API_KEY=<your-azure-key>
OPENAI_BASE_URL=https://<resource>.openai.azure.com/openai/deployments/<deployment>
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FAST=gpt-4o-mini
```

---

### LM Studio (fully local, desktop)

Run LM Studio and enable its local server (default port 1234).

```env
AI_PRIMARY_PROVIDER=openai_compat
AI_LIGHT_PROVIDER=openai_compat
OPENAI_API_KEY=lm-studio        # any non-empty string
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_MODEL=local-model        # matches the model name shown in LM Studio
OPENAI_MODEL_FAST=local-model
```

---

### Hybrid: Gemini primary + Groq light (cost-optimised)

Use Gemini for complex generation and Groq for fast/cheap light tasks.

```env
AI_PRIMARY_PROVIDER=gemini
AI_LIGHT_PROVIDER=openai_compat
GEMINI_KEY=...
GEMINI_MODEL_COMPLEX=gemini-2.5-pro
GEMINI_MODEL_FAST=gemini-2.5-flash
OPENAI_API_KEY=gsk_...
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL_FAST=llama-3.1-8b-instant
```

---

## No-AI Mode

The app runs without any AI configuration. When no provider is configured (no API key set),
AI endpoints return HTTP 503 gracefully and the frontend disables AI buttons automatically.

To confirm AI is disabled: leave `AI_PRIMARY_PROVIDER` unset and all API keys empty.
No errors will occur — AI features simply won't appear.

---

## Feature × Provider Matrix

| Feature | Gemini | OpenAI-compat | Anthropic | Ollama |
|---------|:------:|:-------------:|:---------:|:------:|
| Question generation (MCQ) | ✅ Full | ✅ Full | ✅ Full | ✅ Basic |
| Question generation (Poll/Survey) | ✅ Full | ✅ Full | ✅ Full | ⚠️ Limited |
| Streaming generation | ✅ | ✅ (polyfill) | ✅ (polyfill) | ✅ (polyfill) |
| Prompt validation | ✅ | ✅ | ✅ | ❌ (fails open) |
| Distractor generation | ✅ | ✅ | ✅ | ✅ |
| Text rewriting | ✅ | ✅ | ✅ | ✅ |
| Semantic answer grading | ✅ | ✅ | ✅ | ✅ |
| Participant exam summary | ✅ | ✅ | ✅ | ❌ |
| Cohort exam analysis | ✅ | ✅ | ✅ | ❌ |
| List available models | ❌ | ✅ | Hardcoded | ✅ |

**Notes:**
- "Polyfill" streaming: the response is generated in one shot then yielded question-by-question. The frontend SSE client sees no difference.
- Ollama "Basic" MCQ: works well for straightforward quiz/exam types; complex poll/survey schemas may produce inconsistent JSON from smaller models. Use a 7B+ model for best results.
- Ollama does not support participant summaries or cohort analysis — these are skipped silently (email sent without AI section).

---

## OpenAI-Compatible Services

The `openai_compat` provider works with any service that implements the `/v1/chat/completions` endpoint:

| Service | `OPENAI_BASE_URL` | Notes |
|---------|-------------------|-------|
| OpenAI | `https://api.openai.com/v1` | |
| Groq | `https://api.groq.com/openai/v1` | Fast, free tier |
| Together.ai | `https://api.together.xyz/v1` | |
| Mistral | `https://api.mistral.ai/v1` | |
| LM Studio | `http://localhost:1234/v1` | Local desktop |
| vLLM | `http://localhost:8080/v1` | Local server |
| Ollama OpenAI compat | `http://localhost:11434/v1` | Alternative to `ollama` provider |
| Azure OpenAI | `https://<resource>.openai.azure.com/...` | Enterprise |

> **Note:** Some local servers (older LM Studio, some vLLM configs) ignore `response_format: json_object`. The provider handles this by always parsing defensively — stripping markdown fences before JSON parsing.
