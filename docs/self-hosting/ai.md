# AI Configuration for Self-Hosted Deployments

Swaya.me uses a pluggable AI provider system with two tiers:

- **Primary** — question generation, exam analysis, participant summaries. Requires a capable model (cloud or local API-compatible server).
- **Light** — distractor generation, text rewriting, semantic answer grading. Ollama (local, no API key) works well here.

Two env vars control which providers are used:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AI_PRIMARY_PROVIDER` | `gemini` | Question generation, exam analysis, participant summaries |
| `AI_LIGHT_PROVIDER` | `ollama` | Distractor generation, text rewriting, semantic answer grading |

**Ollama is a light-tier provider only.** Do not set `AI_PRIMARY_PROVIDER=ollama` — question generation is not supported via Ollama.

---

## Quick-Start: Provider Options

| Provider | Env value | Keys needed | Free tier | Best for |
|----------|-----------|-------------|-----------|----------|
| Google Gemini | `gemini` | `GEMINI_KEY` | Yes (limited) | Best quality, default |
| OpenAI | `openai_compat` | `OPENAI_API_KEY` | No | High quality, paid |
| Groq | `openai_compat` | `OPENAI_API_KEY` | Yes (generous) | Fast + cheap cloud |
| Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` | No | High quality alternative |
| LM Studio / vLLM | `openai_compat` | Any string | Free | Local primary tier |
| Azure OpenAI | `openai_compat` | `OPENAI_API_KEY` | Enterprise | Enterprise/compliance |
| Ollama (local) | `ollama` | None | Free | **Light tier only** |

---

## Configuration Examples

### Default — Gemini primary + Ollama light (no extra config needed)

This is the default on swaya.me. Requires only a Gemini API key and a local Ollama daemon.

```env
# AI_PRIMARY_PROVIDER defaults to gemini
# AI_LIGHT_PROVIDER defaults to ollama
GEMINI_KEY=AIza...
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

Pull the Ollama model first: `ollama pull qwen2.5:3b`

**Ollama model recommendations by RAM (light tier):**

| RAM | Model |
|-----|-------|
| 2 GB | `qwen2.5:3b` |
| 4 GB | `qwen2.5:3b` |
| 8 GB | `qwen2.5:7b` |
| 16 GB | `qwen2.5:14b` |

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

### LM Studio (local primary, fully private)

Run LM Studio, enable its local server (default port 1234), and load a 7B+ model.

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
| Question generation | ✅ | ✅ | ✅ | ❌ (light tier only) |
| Streaming generation | ✅ | ✅ (polyfill) | ✅ (polyfill) | ❌ |
| Prompt validation | ✅ | ✅ | ✅ | ❌ (fails open) |
| Distractor generation | ✅ | ✅ | ✅ | ✅ |
| Text rewriting | ✅ | ✅ | ✅ | ✅ |
| Semantic answer grading | ✅ | ✅ | ✅ | ✅ |
| Poll prompt generation | ✅ | ✅ | ✅ | ✅ |
| Participant exam summary | ✅ | ✅ | ✅ | ❌ |
| Cohort exam analysis | ✅ | ✅ | ✅ | ❌ |
| List available models | ❌ | ✅ | Hardcoded | ✅ |

**Notes:**
- "Polyfill" streaming: the response is generated in one shot then yielded question-by-question. The frontend SSE client sees no difference.
- Ollama is the default `AI_LIGHT_PROVIDER`. It handles distractors, rewriting, and grading well on any 3B+ model.
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
| Ollama OpenAI compat | `http://localhost:11434/v1` | Use for light tier only |
| Azure OpenAI | `https://<resource>.openai.azure.com/...` | Enterprise |

> **Note:** Some local servers (older LM Studio, some vLLM configs) ignore `response_format: json_object`. The provider handles this by always parsing defensively — stripping markdown fences before JSON parsing.
