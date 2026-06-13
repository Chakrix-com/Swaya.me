# Swaya Design Token System

## Four surfaces

| Surface | Entry | Tokens used |
|---|---|---|
| **Landing / public pages** | `Home.jsx`, login, legal | `--pub-*` |
| **Host app** | ProLayout + all authenticated pages | `--sw-*`, Ant Design tokens |
| **Participant** | `AudienceSession.jsx`, `AudienceJoin.jsx`, offline polls, exam | `--visitor-aud-*`, `--ctrl-*`, `--skin-*` |
| **Projector** | `QuizPresent.jsx` | `--sw-mode-*`, `--skin-*`, inline dark surface |

---

## Token namespaces

### `--sw-*` — host app tokens (set by `themes.js`)

| Token | Purpose |
|---|---|
| `--sw-primary` / `--sw-primary-strong` / `--sw-primary-soft` / `--sw-primary-border` | Brand primary (changes per theme) |
| `--sw-success/warning/error/info` | Semantic status |
| `--sw-text1/text2/text3` | Ink hierarchy |
| `--sw-bg/card/border/hover` | Surface hierarchy |
| `--sw-tile-{quiz,exam,poll,opoll}-{bg,fg}` | Activity type chips |
| `--sw-chip-{ready,draft,done,live}-{bg,fg}` | Status chips |
| `--sw-hero-bg` / `--sw-banner-bg` | Gradient backgrounds |
| `--sw-mode-quiz/exam/poll/opoll` | Mode accent colors (control room, builder) |

### `--pub-*` — landing / public page tokens

| Token | Purpose |
|---|---|
| `--pub-bg` / `--pub-card` / `--pub-ink` / `--pub-muted` / `--pub-line` | Landing surface |
| `--pub-primary` / `--pub-on-primary` | CTA brand color |
| `--pub-quiz/poll/test/opoll` | Mode accent on marketing |
| `--pub-beam` | Horizontal gradient for accent beams |
| `--pub-font-display` / `--pub-font-body` / `--pub-font-mono` | Font stacks per theme |

### `--visitor-aud-*` — participant page surface (overridden by skins)

| Token | Default | Purpose |
|---|---|---|
| `--visitor-aud-bg` | Indigo gradient | Page background |
| `--visitor-aud-surface` | White/88% | Card backgrounds |
| `--visitor-aud-border` | Navy/20% | Card borders |
| `--visitor-aud-text-primary` | `#1c2b45` | Main text |
| `--visitor-aud-text-secondary` | `#566480` | Secondary text |

### `--ctrl-*` — participant interactive elements (buttons, inputs, radio)

Override these in skins to fully retheme the participant experience. All participant interactive elements (buttons, inputs, radio options) reference these tokens — no hardcoded colors in components.

### `--skin-*` — skin-specific extras (set by `skins.js`)

| Token | Purpose |
|---|---|
| `--skin-accent` | Highlight color for correct answers, CTA |
| `--skin-accent-soft` | Tinted background |
| `--skin-podium-{1,2,3}` | Podium block colors |
| `--skin-correct` / `--skin-correct-bg` | Correct answer reveal |
| `--skin-wrong` / `--skin-wrong-bg` | Wrong answer reveal |

### `--sw-mode-*` — mode accent colors (control room & builder)

```css
--sw-mode-quiz:  #4F46E5;   /* Indigo  */
--sw-mode-exam:  #059669;   /* Emerald */
--sw-mode-poll:  #EA580C;   /* Orange  */
--sw-mode-opoll: #DB2777;   /* Pink    */
```

### Motion tokens (`motion.css`)

| Token | Value | Use |
|---|---|---|
| `--sw-dur-fast` | 120ms | Micro-interactions |
| `--sw-dur-base` | 240ms | Button states, toggles |
| `--sw-dur-slow` | 400ms | Card reveals, transitions |
| `--sw-dur-reveal` | 600ms | Score/answer reveals |
| `--sw-dur-long` | 900ms | Podium, finale |
| `--sw-ease-spring` | `cubic-bezier(0.34,1.56,0.64,1)` | Bouncy scale-in |
| `--sw-ease-out` | `cubic-bezier(0,0,0.2,1)` | Fade/slide out |
| `--sw-ease-in-out` | `cubic-bezier(0.4,0,0.2,1)` | Progress bars |

---

## Adding a new theme

1. Add an entry to `themes/themes.js`. Shape: `{ id, name, swatch, fonts?, antd, proLayout, cssVars }`.
2. `cssVars` only needs to list overrides from Classic Indigo defaults — unset vars fall back to `:root`.
3. The ThemePicker and `applyTheme()` pick it up automatically.

## Adding a new skin

1. Add an entry to `themes/skins.js`. Shape: `{ id, name, emoji, description, preview, cssVars }`.
2. `cssVars` keys must be from `--visitor-aud-*`, `--ctrl-*`, or `--skin-*` namespaces only.
3. `applySkin(id, containerEl?)` clears all skin vars then applies the new set.
4. The QuizBuilder skin picker renders from the registry automatically.

## Adding a new motion animation

1. Add a `@keyframes sw-<name>` block to `themes/motion.css`.
2. Optionally add a `.sw-anim-<name>` utility class.
3. Add a `@media (prefers-reduced-motion)` suppression at the bottom.

---

## Anti-patterns to avoid

- Don't hardcode hex colors in participant components — use `--ctrl-*` or `--skin-*` tokens.
- Don't use `--sw-*` tokens on participant pages (wrong namespace; skins won't override them).
- Don't use Ant Design `colorPrimary` in participant JSX — those are for the host app only.
- Don't skip `prefers-reduced-motion` when adding new CSS animations.
