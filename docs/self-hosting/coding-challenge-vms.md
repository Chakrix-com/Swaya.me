# Coding Challenge: Sandbox VM Setup

The `coding_challenge` quiz type gives each candidate a real, isolated browser IDE
(via [Coder OSS](https://coder.com)) to write and run code against a git-repo-sourced
problem statement, with an optional shared Claude Code assistant, and AI-graded
results. This infrastructure is **separate from the main Swaya app server** — it
needs its own host (or can share a beefy one) and its own one-time setup.

If you only want to run Swaya's quizzes/polls/exams, you can skip this doc entirely.
Coding-challenge creation is gated behind the `CODING_CHALLENGE_PRO` tier /
per-user override anyway (see `docs/multi-tenancy.md`), so nothing else breaks if
this is never configured — `coding_challenge`-related endpoints simply fail when
called without a reachable Coder server.

---

## Architecture

```
Swaya backend (FastAPI)  ──subprocess──▶  coder CLI  ──SSH/HTTPS──▶  Coder server (sandbox VM)
                                                                          │
                                                                    Docker workspaces
                                                                    (one per candidate)
```

- All interaction is through the `coder` CLI as a subprocess
  (`backend/features/coding_challenge/coder_client.py`) — there is no REST "exec"
  endpoint in Coder's API, only a raw WebSocket PTY stream, so `coder ssh <workspace>
  -- <cmd>` is the reliable mechanism with faithful exit codes.
- The Swaya backend process must be logged into the Coder server as a **service
  account** (`coder login`, session cached under `~/.config/coderv2/` for whatever
  OS user runs the backend's systemd service). There is no `CODER_TOKEN` env var —
  auth is entirely the CLI's own cached session.
- Each candidate gets a throwaway Docker container (a Coder "workspace"), destroyed
  after grading.

---

## 1. Provision the Coder server

Any Linux VM with Docker works — it can be the same box as the Swaya backend for
a small deployment, or a dedicated one (recommended once you have real candidate
traffic, since each active workspace is a running Docker container). This is
the exact recipe used to stand up Swaya's own instance (`sandbox.swaya.me`) —
a single small VM, no separate database or load balancer needed.

**Prerequisites:** a DNS `A` record pointing your chosen subdomain (e.g.
`sandbox.yourdomain.com`) at the VM's IP, and ports 80/443 open — needed for
automatic TLS in the next step.

```bash
# On the sandbox VM
curl -fsSL https://coder.com/install.sh | sh
```

This installs Coder as a `.deb`/`.rpm` package with its own systemd unit
(`coder.service`) and an **embedded Postgres** — no separate database server to
set up for a single-VM deployment. Configuration lives in `/etc/coder.d/coder.env`:

```env
# /etc/coder.d/coder.env
CODER_ACCESS_URL=https://sandbox.yourdomain.com
CODER_HTTP_ADDRESS=127.0.0.1:3000

# Required: without wildcard DNS for per-app subdomains, workspace app URLs
# are path-based (https://<url>/@<user>/<workspace>/apps/<slug>?...) — this is
# also the exact URL shape mint_session_url() builds in coder_client.py, so
# these two must be enabled or candidates can't open their IDE session link.
CODER_DANGEROUS_ALLOW_PATH_APP_SHARING=true
CODER_DANGEROUS_ALLOW_PATH_APP_SITE_OWNER_ACCESS=true
```

Add the `coder` OS user to the `docker` group so it can provision containers,
then start the service:

```bash
sudo adduser coder docker
sudo systemctl enable --now coder
sudo -u coder docker ps   # sanity check
```

**TLS + reverse proxy:** Coder only binds to `127.0.0.1:3000` — it needs
something in front of it for the public HTTPS URL. The simplest option
(what `sandbox.swaya.me` actually uses) is [Caddy](https://caddyserver.com/),
since it gets you automatic Let's Encrypt TLS with no certbot/renewal setup:

```bash
sudo apt install -y caddy   # or see caddyserver.com/docs/install
```

```caddyfile
# /etc/caddy/Caddyfile
sandbox.yourdomain.com {
	reverse_proxy 127.0.0.1:3000
}
```

```bash
sudo systemctl enable --now caddy
```

Visit `https://sandbox.yourdomain.com` and follow Coder's first-run flow to
create the first admin user.

## 2. Create a service account for the Swaya backend

Do **not** point the backend at a personal admin login. Create a dedicated
account (e.g. `swaya-backend-svc`) in the Coder UI or via `coder server
create-admin-user`, matching `CODER_SERVICE_ACCOUNT_USERNAME` in `backend/.env`
(default `swaya-backend-svc`).

## 3. Build and push the workspace template

The template lives in this repo at `infra/coder-templates/code-server-multi/` —
a Docker-based template providing a browser VS Code (code-server), Python 3 +
`pytest`/`pytest-json-report`, and OpenJDK 17 + Maven preinstalled, plus a
`git_repo_url` parameter that clones the candidate's starter repo into
`~/project` on workspace start.

```bash
# From the sandbox VM, with the coder CLI logged in as an admin
coder templates push code-server-multi \
  --directory infra/coder-templates/code-server-multi \
  --var claude_oauth_token="$CLAUDE_CODE_OAUTH_TOKEN" \
  --yes
```

`CODE_SERVER_TEMPLATE_NAME` in `backend/.env` must match the template name you
pushed it as (default `code-server-multi`).

**Claude Code shared credential (optional):** the template installs Claude Code
in its startup script and expects a single, subscription-billed OAuth token
(`claude setup-token`, from a Pro/Max/Team/Enterprise plan — not metered
per-token API billing) passed as the sensitive Terraform variable
`claude_oauth_token` above, so it's baked into every workspace's container
environment rather than left as a visible template parameter. Every candidate
shares this one credential — they do have raw shell access inside their own
workspace and could read the env var out of it, so treat it like any other
sandbox-admin-level credential and rotate it if you suspect leakage. Skip this
variable entirely if you don't want AI assistance available inside workspaces.

## 4. Log the Swaya backend into Coder

On the machine running the Swaya backend (systemd service):

```bash
# As the same OS user the backend's systemd service runs as
coder login https://sandbox.yourdomain.com
# follow the prompt, authenticating as the swaya-backend-svc account
```

This caches a session under `~/.config/coderv2/`, which the backend process
inherits automatically since it runs as the same OS user — no token needs to be
stored in `.env`.

Confirm the CLI is usable and can reach the template:

```bash
coder templates list
coder create test-workspace -t code-server-multi -y
coder ssh test-workspace -- echo ok
coder delete test-workspace -y
```

## 5. Configure `backend/.env`

```env
CODER_URL=https://sandbox.yourdomain.com
CODER_CLI_PATH=coder                      # or an absolute path if not on PATH
CODER_SERVICE_ACCOUNT_USERNAME=swaya-backend-svc
CODE_SERVER_TEMPLATE_NAME=code-server-multi
MAX_CONCURRENT_WORKSPACES=5                # cap on simultaneously active candidate workspaces
WORKSPACE_MAX_LIFETIME_SECONDS=5400        # hard timeout per workspace (90 min default)
```

Restart the backend after changing these — `CoderSettings`
(`backend/core/config/settings.py`) is read once at process start.

## 6. Verify end-to-end

1. As a user with `CODING_CHALLENGE_PRO` tier (or super_admin), create a quiz of
   type `coding_challenge`, add a question with a `git_repo_url` and a
   `test_command` (e.g. `pytest --json-report --json-report-file=/tmp/report.json`).
   Generate a candidate invite link and open it.
2. Confirm a workspace is provisioned and the browser IDE loads.
3. Submit — confirm the workspace is torn down (`coder list` on the sandbox VM
   should show it gone) and a graded result appears in examiner review.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `CoderClientError: ... failed (rc=1)` on every call | Backend's OS user isn't logged in — re-run `coder login` as that exact user |
| Workspace creation succeeds but candidate IDE never loads | Docker socket permissions on the sandbox VM — re-check `adduser coder docker` step |
| `coder ssh <ws> -- <cmd>` hangs | Agent hasn't finished its `startup_script` yet (cloning + installing Claude Code can take a minute on first boot) |
| Claude Code missing inside workspace | `claude_oauth_token` wasn't passed at `templates push` time, or the install script failed (`curl` blocked by an egress firewall on the sandbox VM) |
