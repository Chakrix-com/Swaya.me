# Dependency & License Scan — Open Findings

- **Status:** Scanning infrastructure shipped and live (`.github/workflows/dependency-scanning.yml`, merged via PR #10, all checks verified passing on real GitHub Actions). The findings below are what it surfaced — none are fixed yet, this doc exists to track them.
- **Date:** 2026-08-22
- **Reported by:** Claude Code session, as part of FINOS-readiness prep (see the "Swaya × FINOS Readiness" artifact for the full P0–P3 picture this feeds into)
- **Affected components:** `backend/requirements.txt`, `backend/safety-policy.yml`, `frontend/package.json`

## 1. Backend — CVE backlog (65 findings, 22 packages)

`safety check -r requirements.txt` against the pinned versions in `backend/requirements.txt`. Full detail (per-CVE IDs) lives in `backend/safety-policy.yml`'s `ignore-vulnerabilities` block — this is a summary, not a duplicate.

**Notably stale core pins** (worth prioritizing — these look like genuine drift, not an intentional constraint, since other packages in the same file are current):

| Package | Pinned | Findings |
|---|---|---|
| `pillow` | 12.1.1 | 18 |
| `python-multipart` | 0.0.6 | 10 |
| `starlette` | 1.0.0 | 5 |
| `pyjwt` | 2.8.0 | 5 |

Remaining 18 packages have 1–3 findings each (`pyasn1`, `mako`, `ecdsa`, `urllib3`, `python-engineio`, `black`, `requests`, `python-socketio`, `python-dotenv`, `pytest`, `pymysql`, `pygments`, `msgpack`, `lxml`, `idna`, `cryptography`, `anyio`, `aiosmtplib`).

**Tracking mechanism:** every finding is recorded in `backend/safety-policy.yml` with `reason: pre-existing at scanner-introduction (2026-08-22)` and `expires: '2026-11-22'`. CI is green today; on/after that date `safety check` starts failing on every un-triaged entry again, forcing a real look rather than a silent permanent ignore. Any *new* CVE from a future dependency bump fails the build immediately — the policy file only covers what existed the day scanning was introduced.

**Next step:** a dedicated dependency-upgrade PR, tested independently of feature work — `starlette`/`python-multipart`/`pyjwt` bumps in particular touch core request-handling and auth, not something to bundle in as a side effect of something else.

## 2. Backend — license findings needing a legal decision (5 packages)

`pip-licenses --allow-only=...` currently excludes these 5 via `--ignore-packages` rather than either passing them silently or leaving the check permanently red:

| Package | Reported license | Note |
|---|---|---|
| `cssutils` | LGPL-3.0-or-later | Weak copyleft — FINOS Category X unless there's a reason to treat it differently |
| `encutils` | LGPL-3.0-or-later | Same family, likely a `cssutils` dependency |
| `mysql-connector-python` | GPL | Oracle ships this under the **Universal FOSS Exception**, which is designed exactly to permit inclusion in non-GPL projects — plausibly resolves this, but that's a legal read of the actual exception text against this project's use, not something `pip-licenses`' classifier output settles on its own |
| `text-unidecode` | Artistic License; GPL; GPLv2+ (multi-declared) | Ambiguous — three licenses listed, unclear which actually governs |
| `qrcode` | BSD License; Other/Proprietary License | Almost certainly PyPI classifier noise (its real license is BSD) — flagged rather than assumed |

**This blocks more than CI hygiene** — FINOS's IP review during the contribution process looks at actual dependency licenses, not just the root `LICENSE` file. Worth resolving alongside the copyright-entity question (who legally holds Swaya's own IP — "Chakrix" vs. Nishant personally), since both are the same category of decision: something only a human can settle, not something to infer from tooling.

## 3. Frontend — CVE backlog (10 findings, post-auto-fix)

`npm audit` found 29 originally; **19 were resolved same-day** via non-breaking `npm audit fix` (verified with a full `npm run build`). Remaining 10 all require breaking-change upgrades:

| Package | Issue | Fix requires |
|---|---|---|
| `react-router` / `react-router-dom` | Open redirect, arbitrary constructor injection via SSR hydration | Major version bump to 7.18.2 |
| `exceljs` (via `uuid`) | Missing buffer bounds check in `uuid` v3/v5/v6 | Downgrade to `exceljs@3.4.0` |
| `esbuild` (via `vite`) | (see `npm audit` for current detail) | Vite major bump |
| `path-to-regexp` (via `@ant-design/pro-layout`) | ReDoS | Upstream fix in `@ant-design/pro-components`, not directly controllable |

Left as `continue-on-error: true` in the CVE-scan job pending a dedicated, separately-tested upgrade PR — `react-router-dom` alone touches every route in the app.

## 4. Frontend — license finding needing review (1 package)

`buffers@0.1.1` (deep transitive dependency, likely via the PDF/export chain) declares a bare link (`http://github.com/substack/node-bufferlist`) instead of a recognized SPDX identifier. Excluded from the automated `license-checker` allow-list pending someone actually opening that link and confirming the license text. Small, old, stable package — probably fine, not yet verified.

## 5. Also fixed in passing (not findings, just noting)

- `frontend/package.json` had no `license` field at all — `license-checker` was reporting the app itself as `UNLICENSED`. Added `"license": "Apache-2.0"`.

## Cross-references

- Per-CVE detail for §1: `backend/safety-policy.yml`
- Scanning implementation: `.github/workflows/dependency-scanning.yml`
- Broader FINOS-readiness context and priority ordering: the published "Swaya × FINOS Readiness" artifact
