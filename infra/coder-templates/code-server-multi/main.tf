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
