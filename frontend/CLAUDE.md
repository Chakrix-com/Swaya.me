# Frontend conventions

## UI menus / dropdowns / click-triggered popups

**Never use Ant Design's `Dropdown`, `Select` (for custom option pickers), or a
click-triggered `Popover` for new UI in this app.** They're broken on the user's
office VDI/remote-desktop environment — the menu opens but no option is
selectable, or it gets stuck open/unselectable. Root cause: a click-race in Ant
Design's shared `@rc-component/trigger` mousedown/pointerdown coordination,
confirmed with a brand-new, zero-customization `Dropdown` showing the identical
bug — it's inherent to that trigger mechanism on that environment, not anything
specific to this app's code.

Use instead:
- **Any new "..." actions menu** (row actions, card actions, export menus, etc.):
  reuse `frontend/src/components/MoreActionsMenu.jsx`. It implements the safe
  pattern generically — pass it an `items` array (supports `divider`, `danger`,
  `disabled`, and `confirm: { title, description, onConfirm, okText, cancelText }`
  for Popconfirm-wrapped destructive actions) and it renders the trigger + a
  portaled popup with its own outside-click/Escape handling. Don't write a new
  one-off popup — extend this component if it's missing something.
- **Simple single-choice pickers** (e.g. language switcher): a native `<select>`
  styled with antd theme tokens (`theme.useToken()`), not antd's `Select`.
- If you must build a genuinely new kind of click-triggered popup that doesn't
  fit `MoreActionsMenu`, follow the same underlying pattern by hand: own
  `useState` for open/closed, a single self-owned `document` `mousedown`
  listener for outside-click-to-close, `Escape` to close, rendered via
  `createPortal` into `document.body` with `position: fixed` and viewport-edge
  collision handling — no `@rc-component/trigger` involvement anywhere.

`Popconfirm` and `Tooltip` (also rc-trigger-based) have not been confirmed broken
and are left as-is inside `MoreActionsMenu`'s popup content — only `Dropdown`/
`Select`/click-triggered `Popover` are confirmed and must be avoided for new code.

Fixed so far under this rule: header profile/theme/language menus, sidebar folder
"..." menu, Dashboard/Activities/User Management row "..." menus, Quiz History
export dropdown. Full incident history and reasoning: ask Claude to check project
memory `project_dropdown_vdi_bug.md`, or see git log for `MoreActionsMenu.jsx`.
