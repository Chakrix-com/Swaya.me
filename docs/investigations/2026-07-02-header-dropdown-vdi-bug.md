# Header Dropdown (Language / Theme Picker) Failure over Office VDI

- **Status:** Investigation complete — root cause identified. No fix implemented yet (analysis-only session).
- **Date:** 2026-07-02
- **Reported by:** meetnishant@gmail.com
- **Environment where it reproduces:** Office VDI / remote desktop client ("VCSe"). Not reproduced yet on a normal local browser session (reproduction strategy defined, not yet executed — see "Next steps").
- **Affected components:** `frontend/src/components/ThemePicker.jsx`, `frontend/src/components/LanguageSwitcher.jsx` (repo: `/home/vinay/Swaya.me`, branch `main`)

## 1. Reported symptoms

While using swaya.me from an office VDI session, the language dropdown and theme picker in the header exhibit three distinct, reproducible problems. Everything else on the site (quiz, poll, other controls) works normally — only these two pickers are affected.

1. **Needs a second click to open.** The first click on the trigger does nothing; the second click opens the popup.
2. **Cross-dropdown "flipping."** Once two of these dropdowns have been interacted with, clicking either one's trigger can toggle *the other* dropdown instead of / as well as itself. The two controls become "synced" — clicking either flips both.
3. **Abandoned/ghost dropdown.** After opening successfully, selecting an option (or trying to close it) can leave the popup stuck: visibly rendered, but unresponsive to further clicks, and Escape does not close it. The rest of the page keeps working normally.

## 2. Investigation method

No git repo existed at the deployed site path (`/www/wwwroot/www.swaya.me`), so initial analysis worked from the production build only:
- Confirmed stack via the deployed bundle (`assets/index-6jifKGq0.js`, referenced by `index.html`): **React 18.3.1 + Ant Design**, using Ant's popup engine `@rc-component/trigger` (and `rc-select`/`rc-dropdown` markers). i18n via `i18next`.
- Found the header markup and CSS classes (`assets/index-D7G_h1IW.css`) for the actual controls: `.language-switcher-container`, `.theme-picker-btn`, `.public-brand-header`.
- Found `getPopupContainer:X=>X.parentElement/parentNode` overrides compiled into the bundle — present even in the oldest retained build (2026-06-26), so the change predates our observation window but postdates the original redesign commit (see below).

Once the actual source checkout was located at `/home/vinay/Swaya.me` (git repo, branch `main`, HEAD `f8520f5`), analysis switched to real source + git history + the installed `@rc-component/trigger@2.3.1` library source in `node_modules`, which is authoritative over bundle-reading.

## 3. Timeline

| Commit / state | What it did | Has `getPopupContainer` override? | Has `startTransition`? |
|---|---|---|---|
| `bdc8101` — *"feat: 3-theme UI system (Classic Indigo, Funky-Studio, Perky-Game)"* (2026-06-11) | Original "aesthetic redesign." Introduced `ThemePicker.jsx` from scratch as a plain, default `<Dropdown>`. | No | No |
| `c25f6c8` — *"fix: make ThemePicker icon visible on light visitor pages in Funky-Studio"* | Added `className="theme-picker-btn"` only. | No | No |
| `85ceb62` (current `HEAD`, `main`) | Latest commit on the file's history; still no `getPopupContainer`/`startTransition`. | No | No |
| **Uncommitted working-tree changes** (present now in `/home/vinay/Swaya.me`, and already reflected in the live production bundle since at least 2026-06-26) | Added `getPopupContainer={trigger => trigger.parentElement}` to both components; wrapped the selection action in `startTransition(...)` in both components; added `virtual={false}` to `LanguageSwitcher`'s `Select`. | **Yes** | **Yes** |

**Conclusion:** the bug was not introduced by the original visual redesign (`bdc8101`). It was introduced by a later, still-uncommitted local edit layered on top of it — one that was built and deployed to production without being committed to git.

## 4. Root cause

Two lines, present in both affected components, break two invariants that Ant Design's popup engine (`@rc-component/trigger`) relies on:

```jsx
// Both ThemePicker.jsx and LanguageSwitcher.jsx
getPopupContainer={trigger => trigger.parentElement}

// ThemePicker.jsx
onClick: () => startTransition(() => dispatch(setTheme(id))),

// LanguageSwitcher.jsx
startTransition(() => {
  i18n.changeLanguage(value)
})
```

### 4a. Structural fact (confirmed, not inferred)
Both components are direct siblings inside the same header container:

```jsx
<div className="language-switcher-container">
  <ThemePicker />
  <LanguageSwitcher />
  <BetaBadge />
</div>
```

Neither component wraps its trigger in an extra element, so `trigger.parentElement` resolves to the **same physical DOM node** (`.language-switcher-container`) for both. Before this change, each popup rendered into an isolated node under `document.body` (Ant Design's default) — fully decoupled from every other popup on the page. Now two independent popups share one small, `display:flex` host meant only to lay out the two icon buttons.

### 4b. Mechanism (confirmed via `@rc-component/trigger@2.3.1` source, `node_modules/@rc-component/trigger/lib/index.js:356-363`)
The entire click-to-open/close logic is one flip on a single boolean:

```js
cloneProps.onClick = function (event) {
  if (openRef.current && clickToHide) {
    triggerOpen(false);
  } else if (!openRef.current && clickToShow) {
    triggerOpen(true);
  }
  ...
};
```

There is no separate concept of "first click" vs "second click" in this code — every click just flips (or tries to flip) that ref. If it gets out of sync with what's actually on screen, clicks stop doing what they look like they should do.

### 4c. Why re-renders can desync it
`startTransition` marks the state update from selecting an option (which triggers `i18n.changeLanguage` / `setTheme`, both of which cascade into re-rendering nearly the entire app tree) as low-priority and interruptible. Combined with the popup DOM now living *inside* the trigger's own subtree (4a) instead of an isolated portal root, a click/Escape/outside-click that lands while that deferred re-render is still in flight can leave the popup's internal open/visible state out of sync with its actual on-screen DOM.

## 5. Root cause per symptom

| # | Symptom | Direct cause |
|---|---|---|
| 1 | Needs a second click to open | `openRef.current` is left `true` by a prior broken interaction with the same dropdown (symptom 3) even though nothing is visibly open. The next click is read as "close something already open" → no-op. The click after that sees the corrected state and opens normally. Not a fresh bug per click — inherited desync from the dropdown's last broken interaction. |
| 2 | Cross-dropdown flipping / syncing | Both dropdowns' `getPopupContainer` resolve to the **same shared DOM node** (§4a). Popups are no longer isolated; the shared `display:flex` container's layout and the two triggers' near-identical, adjacent coordinates let one dropdown's popup/positioning interfere with the other's clickable area, so a click aimed at one trigger can perturb the other. |
| 3 | Ghost/abandoned dropdown, unselectable, Escape does nothing | Combination of §4a (popup nested inside the component's own subtree instead of an isolated portal root) and §4c (`startTransition` deferring the state update that should close/update it). A click landing mid-transition can leave the popup visually present but internally in a state the code no longer believes needs closing — so further clicks do nothing and the Escape handler, which checks that same state, short-circuits. |

**Unifying statement:** one change (adding `getPopupContainer` + wrapping the close-triggering state update in `startTransition` on both pickers), two broken invariants (shared popup host; deferred/interruptible close state), three visible symptoms — not three unrelated bugs.

## 6. Evidence / file references

- Source repo: `/home/vinay/Swaya.me` (branch `main`, HEAD `f8520f5` at time of investigation)
- `git diff -- frontend/src/components/ThemePicker.jsx` (uncommitted) — adds `getPopupContainer` + `startTransition`
- `git diff -- frontend/src/components/LanguageSwitcher.jsx` (uncommitted) — adds `getPopupContainer`, `startTransition`, `virtual={false}`
- `git show bdc8101:frontend/src/components/ThemePicker.jsx` — original clean version, no override
- `git log --oneline -- frontend/src/components/LanguageSwitcher.jsx frontend/src/components/ThemePicker.jsx`
- `frontend/node_modules/@rc-component/trigger/lib/index.js:356-363` — click open/close toggle logic
- `frontend/node_modules/@rc-component/trigger/lib/hooks/useWinClick.js` — outside-click-to-close listener logic
- Deployed bundle (for cross-check): `/www/wwwroot/www.swaya.me/assets/index-6jifKGq0.js`, `assets/index-D7G_h1IW.css` — confirms the uncommitted change is already live in production, and has been since at least the oldest retained build (2026-06-26).

## 7. What's confirmed vs. what still needs live verification

**Confirmed from source/structure (high confidence, no live testing needed):**
- Stack and library identity (Ant Design / `@rc-component/trigger`, React 18.3.1)
- Both components share the same `getPopupContainer` target (§4a) — this is a static DOM-structure fact, not a guess
- The uncommitted diff is the only relevant code difference between "working" and "broken" for these two components
- The click-toggle mechanism in `@rc-component/trigger` (§4b) is a single shared ref, exactly as described

**Plausible, source-grounded, but not yet observed live (pending the simulation work):**
- The exact pixel/timing mechanism by which the shared container causes cross-dropdown interference (layout shift vs. overlapping absolute-position coordinates)
- Whether `openRef.current` staying `true` is precisely what's happening for symptom 1, vs. a related but distinct desync
- Confirmation that a hard-refresh's very first click (before any prior interaction with the dropdown in that session) opens correctly — this is a testable prediction of the current theory

## 8. Next steps (not yet executed — deferred by request)

1. **Local simulation without VDI access** (dev site is not reachable from the office VDI due to whitelisting, so this must be reproduced on a normal machine):
   - Manual: Chrome DevTools → Performance → CPU throttling (6x–20x slowdown) on `localhost`, then interact with the pickers at normal human speed — throttling should widen the race window enough to reproduce symptom 3 reliably.
   - Scripted/deterministic: Playwright + CDP `Emulation.setCPUThrottlingRate`, with scripted clicks spaced a few tens of ms apart, to get a repeatable pass/fail signal usable before and after any fix.
2. **Validate the fresh-load prediction** from §7 as a cheap sanity check before/alongside the simulation.
3. **Candidate fix direction (not yet implemented):** revert/remove the `getPopupContainer={trigger => trigger.parentElement}` override on both components (restores isolated `document.body` portals, likely resolves symptom 2 outright and reduces symptoms 1 and 3); re-evaluate whether the `startTransition` wrapping around `i18n.changeLanguage`/`setTheme` needs an `isPending`-aware guard instead of being applied unconditionally.
4. Apply and test in **dev only**, confirm via the simulation harness, before touching production.

---
*This document was generated from a Claude Code investigation session. No code changes were made to either `/www/wwwroot/www.swaya.me` (production) or `/home/vinay/Swaya.me` (source) as part of this investigation.*
