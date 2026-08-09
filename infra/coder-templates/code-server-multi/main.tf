terraform {
  required_providers {
    coder = {
      source = "coder/coder"
    }
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

locals {
  username = data.coder_workspace_owner.me.name
}

variable "docker_socket" {
  default     = ""
  description = "(Optional) Docker socket URI"
  type        = string
}

variable "claude_oauth_token" {
  description = "Shared CLAUDE_CODE_OAUTH_TOKEN baked into every workspace (Claude Pro/Max/Team subscription, not per-candidate)."
  type        = string
  sensitive   = true
  default     = ""
}

provider "docker" {
  # Defaulting to null if the variable is an empty string lets us have an optional variable without having to set our own default
  host = var.docker_socket != "" ? var.docker_socket : null
}

data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

data "coder_parameter" "git_repo_url" {
  name         = "git_repo_url"
  display_name = "Starter repo URL"
  description  = "Public git repo cloned into ~/project at workspace start (Python or Java)."
  type         = "string"
  default      = ""
  mutable      = true
}

resource "coder_agent" "main" {
  arch           = data.coder_provisioner.me.arch
  os             = "linux"
  startup_script = <<-EOT
    set -e

    # Prepare user home with default files on first start.
    if [ ! -f ~/.init_done ]; then
      cp -rT /etc/skel ~
      touch ~/.init_done
    fi

    # --- Clone starter repo (fixed convention: ~/project) ---
    if [ -n "${data.coder_parameter.git_repo_url.value}" ] && [ ! -d ~/project/.git ]; then
      git clone "${data.coder_parameter.git_repo_url.value}" ~/project
      cd ~/project && git add -A && git diff --cached --quiet || git commit -m "starter" --author="Starter <starter@swaya.local>" || true
    fi

    # --- Claude Code (headless, shared subscription credential) ---
    if ! command -v claude >/dev/null 2>&1; then
      curl -fsSL https://claude.ai/install.sh | bash || true
    fi
    # ~/.local/bin (where the installer puts `claude`) is only on PATH via ~/.profile,
    # which non-login shells (e.g. code-server's own embedded terminal) never source -
    # symlink into /usr/local/bin instead, which every shell mode has on PATH unconditionally.
    if [ -x ~/.local/bin/claude ] && [ ! -e /usr/local/bin/claude ]; then
      sudo ln -sf ~/.local/bin/claude /usr/local/bin/claude
    fi
    # CLAUDE_CODE_OAUTH_TOKEN is set as a container-level env var (see docker_container.workspace
    # below), not written into a shell rc file - confirmed via spike #7 (2026-07-24) that shell
    # rc files are unreliable across invocation modes: ~/.bashrc has the standard
    # "if not interactive, don't do anything" early-return (blocks our own backend's
    # non-interactive `bash -lc` execs), and ~/.local/bin (needed for `claude` to even be
    # found) is only added to PATH by ~/.profile, which non-login interactive shells
    # (e.g. code-server's own embedded terminal) never source at all. A container-level
    # env var is inherited by every process regardless of shell/login/interactive mode,
    # sidestepping this whole class of shell-startup-file bugs.

    # --- PostToolUse hook: commit AI-driven edits as they happen ---
    mkdir -p ~/project/.claude
    cat > ~/project/.claude/settings.json <<'HOOKEOF'
    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [
              {
                "type": "command",
                "command": "cd ~/project && git add -A && git diff --cached --quiet || git commit -m \"ai-edit: $(date -Iseconds)\" --author=\"Claude Code <ai@swaya.local>\""
              }
            ]
          }
        ]
      }
    }
    HOOKEOF

    # --- Claude Code VS Code extension (GUI panel, added at user request 2026-07-24) ---
    # The registry code-server module installs code-server via its own separate script,
    # which is not guaranteed to run before this one - so poll for the code-server binary
    # rather than assume ordering (confirmed necessary: no --depends_on/ordering is set
    # between this agent's startup_script and the module's own install script).
    # Poll window was 60x2s=120s, but the module's own install + code-server startup
    # together measured ~145-150s in practice - the binary wasn't in PATH yet when the
    # loop gave up, and with no else branch this failed completely silently (confirmed
    # live: a real candidate saw no extension and no error, on the very first attempt).
    # Widened to 90x2s=180s and made failure/success explicit in the log instead of
    # silent. Output is also now redirected - an unredirected backgrounded subshell here
    # was separately triggering Coder's own "output pipes were not closed" warning,
    # which flags the whole startup script as errored even when everything succeeds.
    (
      for i in $(seq 1 90); do
        command -v code-server >/dev/null 2>&1 && break
        sleep 2
      done
      if command -v code-server >/dev/null 2>&1; then
        if code-server --install-extension anthropic.claude-code; then
          echo "claude-code extension installed"
        else
          echo "claude-code extension install FAILED"
        fi
      else
        echo "claude-code extension install skipped: code-server binary never appeared within poll window"
      fi
    ) >/tmp/claude-extension-install.log 2>&1 &

    # --- swaya-submit-timer VS Code extension (countdown + Submit button,
    #     added 2026-08-09; plan: _private/coder_submit_extension_plan.md) ---
    # Base64-embedded straight into this startup script via filebase64()
    # below instead of a Dockerfile COPY or a separately-copied file -
    # decided over both originally-considered options (see the plan's
    # "Packaging & installing" section): no Docker image rebuild, ever, and
    # unlike an image-bake (whose rebuild trigger is keyed only off
    # Dockerfile's own hash, see docker_image.code_server_multi below),
    # Terraform correctly notices a new template version is needed whenever
    # the .vsix's bytes change, since that changes this interpolated string
    # directly. Same poll-for-code-server / explicit-log-not-silent-failure
    # pattern as the Claude Code extension install above - independent
    # background job, doesn't wait on or block that one.
    #
    # Per-candidate session data (invite token, time budget, apiBase,
    # created_at) is NOT plumbed through here - it's written straight into
    # the container by the backend after workspace creation (see
    # _write_session_file in coding_challenge_service_async.py), landing at
    # /home/coder/.swaya/session.json before this extension ever activates.
    cat > /tmp/swaya-submit-timer.vsix.b64 <<'VSIXEOF'
    ${filebase64("${path.module}/swaya-extension/swaya-submit-timer-0.1.1.vsix")}
    VSIXEOF
    base64 -d /tmp/swaya-submit-timer.vsix.b64 > /tmp/swaya-submit-timer.vsix
    (
      for i in $(seq 1 90); do
        command -v code-server >/dev/null 2>&1 && break
        sleep 2
      done
      if command -v code-server >/dev/null 2>&1; then
        if code-server --install-extension /tmp/swaya-submit-timer.vsix; then
          echo "swaya-submit-timer extension installed"
        else
          echo "swaya-submit-timer extension install FAILED"
        fi
      else
        echo "swaya-submit-timer extension install skipped: code-server binary never appeared within poll window"
      fi
    ) >/tmp/swaya-submit-timer-install.log 2>&1 &

    # --- swaya-snapshot-loop: manual-edit safety net, every ~2 minutes ---
    # No systemd in this container (Coder agent runs directly as PID 1), so this is a
    # plain backgrounded shell loop instead of a systemd timer unit. It dies along with
    # every other process in the container on `coder stop` (see design doc's corrected
    # AI-usage timeline capture section, 2026-07-24) - no explicit stop step needed.
    nohup bash -c '
      while true; do
        sleep 120
        cd ~/project 2>/dev/null && { git diff --quiet || git commit -am "manual-snapshot: $(date -Iseconds)" --author="Candidate <candidate@swaya.local>"; }
      done
    ' >/tmp/swaya-snapshot-loop.log 2>&1 &
    disown
  EOT

  # These environment variables allow you to make Git commits right away after creating a
  # workspace. Note that they take precedence over configuration defined in ~/.gitconfig!
  env = {
    GIT_AUTHOR_NAME     = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    GIT_AUTHOR_EMAIL    = "${data.coder_workspace_owner.me.email}"
    GIT_COMMITTER_NAME  = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    GIT_COMMITTER_EMAIL = "${data.coder_workspace_owner.me.email}"
  }

  metadata {
    display_name = "CPU Usage"
    key          = "0_cpu_usage"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "RAM Usage"
    key          = "1_ram_usage"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "Home Disk"
    key          = "3_home_disk"
    script       = "coder stat disk --path $${HOME}"
    interval     = 60
    timeout      = 1
  }
}

# See https://registry.coder.com/modules/coder/code-server
module "code-server" {
  count  = data.coder_workspace.me.start_count
  source = "registry.coder.com/coder/code-server/coder"

  # This ensures that the latest non-breaking version of the module gets downloaded, you can also pin the module version to prevent breaking changes in production.
  version = "~> 1.0"

  agent_id = coder_agent.main.id
  order    = 1
  folder   = "/home/coder/project"

  # Workspace Trust ("Restricted Mode") makes the Claude Code extension invisible by
  # default — it explicitly refuses to activate in an untrusted workspace ("untrusted
  # workspaces are not supported", confirmed via its own extension page) — and every
  # candidate's cloned starter repo counts as untrusted until they manually click
  # Manage -> Trust, which nothing in the UI points them toward. Confirmed live: this
  # is why candidates report never seeing Claude Code at all, not an extension-install
  # failure. The module writes `settings` to code-server's User settings.json only if
  # that file doesn't already exist yet (see registry.coder.com/modules/coder/code-server
  # run.sh) — the settings variable is the only mechanism this module exposes for this,
  # there's no CLI-flag passthrough.
  #
  # Tradeoff accepted knowingly, not overlooked: Workspace Trust is what stops a
  # malicious/compromised starter repo's auto-run tasks (.vscode/tasks.json etc.) from
  # executing the instant the folder opens, and every workspace carries a genuinely
  # valuable shared secret as a plain env var (CLAUDE_CODE_OAUTH_TOKEN, the same Claude
  # subscription credential for every candidate) that such a task could exfiltrate.
  # Accepted because starter repos are host-chosen, not attacker-chosen, and the worst
  # realistic outcome is a leaked shared token (rotatable) rather than a cross-candidate
  # breach — the container boundary, not this in-editor prompt, is the real isolation
  # boundary between candidates. CLAUDE_CODE_OAUTH_TOKEN should be rotated after this
  # change ships, as routine hygiene given the reduced defense-in-depth.
  settings = {
    "security.workspace.trust.enabled" = false

    # This VS Code build ships a built-in Chat/"Copilot" panel natively (not an
    # installed extension - confirmed via `code-server --list-extensions`, only
    # anthropic.claude-code is actually installed; "Models, sign in to use Copilot"
    # is core product UI, unrelated to our own setup). It defaults to open in the
    # secondary side bar, prompting every candidate to sign into a Copilot account
    # they don't have and aren't meant to use, alongside Claude Code (the actual
    # intended tool). No single flag disables the underlying feature (it's driven
    # by an internal, non-configurable context key, `chatIsEnabled` - confirmed by
    # grepping the workbench bundle) - `defaultVisibility: hidden` is the
    # documented, real setting for suppressing the panel it lives in by default.
    # Candidates can still manually reopen the secondary side bar if they want to;
    # this only changes what's visible on first load.
    "workbench.secondarySideBar.defaultVisibility" = "hidden"
  }
}

resource "docker_image" "code_server_multi" {
  name = "swaya/code-server-multi:latest"
  build {
    context = "."
  }
  triggers = {
    dockerfile_sha1 = filesha1("${path.module}/Dockerfile")
  }
}

resource "docker_volume" "home_volume" {
  name = "coder-${data.coder_workspace.me.id}-home"
  # Protect the volume from being deleted due to changes in attributes.
  lifecycle {
    ignore_changes = all
  }
  # Add labels in Docker to keep track of orphan resources.
  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }
  labels {
    label = "coder.owner_id"
    value = data.coder_workspace_owner.me.id
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
  # This field becomes outdated if the workspace is renamed but can
  # be useful for debugging or cleaning out dangling volumes.
  labels {
    label = "coder.workspace_name_at_creation"
    value = data.coder_workspace.me.name
  }
}

resource "docker_container" "workspace" {
  count = data.coder_workspace.me.start_count
  image = docker_image.code_server_multi.image_id
  # Uses lower() to avoid Docker restriction on container names.
  name = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  # Hostname makes the shell more user friendly: coder@my-workspace:~$
  hostname = data.coder_workspace.me.name
  # Use the docker gateway if the access URL is 127.0.0.1
  entrypoint = ["sh", "-c", replace(coder_agent.main.init_script, "/localhost|127\\.0\\.0\\.1/", "host.docker.internal")]
  env = [
    "CODER_AGENT_TOKEN=${coder_agent.main.token}",
    "CLAUDE_CODE_OAUTH_TOKEN=${var.claude_oauth_token}",
  ]
  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }
  volumes {
    container_path = "/home/coder"
    volume_name    = docker_volume.home_volume.name
    read_only      = false
  }

  # Add labels in Docker to keep track of orphan resources.
  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }
  labels {
    label = "coder.owner_id"
    value = data.coder_workspace_owner.me.id
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
  labels {
    label = "coder.workspace_name"
    value = data.coder_workspace.me.name
  }
}
