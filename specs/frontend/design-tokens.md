# Design Tokens — Frontend

**Date:** 2026-06-13  
**Status:** Implemented  
**Canonical source:** `frontend/src/themes/README.md` — full namespace reference with tables and anti-patterns.

This document records decisions and rationale; for the full token catalog see the README.

---

## Four-surface model

Swaya renders across four distinct surfaces. Each has its own token namespace to prevent bleed-through.

| Surface | Token prefix | Set by | Entry component |
|---|---|---|---|
| Landing / public pages | `--pub-*` | `themes.js` (per theme) | `Home.jsx`, login, legal |
| Host app | `--sw-*` | `themes.js` via `applyTheme()` | ProLayout + all auth pages |
| Participant | `--visitor-aud-*`, `--ctrl-*`, `--skin-*` | `skins.js` via `applySkin()` | `AudienceSession.jsx`, `AudienceJoin.jsx`, exam |
| Projector | `--sw-mode-*`, `--skin-*` | skin + mode | `QuizPresent.jsx` |

**Key invariant:** `--sw-*` tokens must never appear in participant components. Participant components use only `--ctrl-*`/`--skin-*`/`--visitor-aud-*`. Themes change the host app; skins change the participant experience independently.

---

## Themes vs Skins — why two systems

**Themes** (`frontend/src/themes/themes.js`) are chosen by the host for their own UI. They control:
- Host brand colors, typography (Ant Design `colorPrimary` + custom `--sw-*` overrides)
- Landing page look for the host's tenant

**Skins** (`frontend/src/themes/skins.js`) are assigned per-quiz by the host. They control:
- The look participants see during the quiz (background, card color, button color)
- Applied at session join via `applySkin(quiz.skin, containerEl)` and again in the projector view

A host running on "Boardroom" theme can send participants into a "Party" skin — the two systems are completely independent.

---

## Motion tokens

Defined in `frontend/src/themes/motion.css`, imported in `index.css`.

All animations **must** include a `@media (prefers-reduced-motion: reduce)` suppression. The file already has a catch-all block at the bottom. New keyframes added there automatically get suppressed.

Duration tokens are CSS custom properties so they can be overridden per-skin if needed (e.g., a "calm" skin could set `--sw-dur-reveal: 0ms`).

---

## How Ant Design tokens interact

Ant Design 5 uses CSS-in-JS design tokens (`ConfigProvider → theme → token`). These live in the `:root` via `themes.js → applyTheme()`. The mapping:
- `colorPrimary` → Ant Design button/link/focus-ring colors  
- We set `colorBgBase`, `colorTextBase` for light/dark mode  
- Ant Design tokens do NOT reach participant pages (no `<ConfigProvider>` wraps audience pages)

Do **not** use `antd` token names in participant JSX (e.g., `token.colorPrimary`). Use `var(--ctrl-btn-primary-bg)` instead.

---

## Adding tokens — checklist

1. **Host app token**: add to `themes.js` `cssVars` for each theme. Add to `README.md` table.
2. **Participant interactive token**: add to `--ctrl-*` section in `index.css` default, override in each skin in `skins.js`.
3. **Skin-specific token**: must be in `--skin-*` namespace; add to `skins.js` per-skin.
4. **Motion token**: add duration to `motion.css`; add `prefers-reduced-motion` suppression; add to README.

---

## Anti-patterns

See `frontend/src/themes/README.md` § Anti-patterns. Key ones:
- No hardcoded hex values in participant components.
- No `--sw-*` on participant pages.
- No Ant Design `colorPrimary` in audience/exam JSX.
- All new CSS animations need `prefers-reduced-motion` suppression.
