#!/usr/bin/env bash
# persona-deploy.sh — Persona App CI/CD menu
#
# Usage:
#   ./persona-deploy.sh              → interactive menu
#   ./persona-deploy.sh <command>    → run a specific command
#
# Commands:
#   deploy-dev        Build & deploy to dev.persona.swaya.me
#   promote-live      Tag + promote dev build → live (persona.swaya.me)
#   rollback-live     Restore a previous persona release on live
#   releases          List all persona release tags
#   migrate-dev       Run alembic migrations on swayame_persona_dev DB
#   migrate-live      Run alembic migrations on swayame_persona DB
#   health            Health-check both persona environments
#   status            Show persona systemd service status
#   logs-dev          Tail dev backend logs
#   logs-live         Tail live backend logs

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
PERSONA_DEV_ROOT="/www/wwwroot/dev.persona.swaya.me"
PERSONA_LIVE_ROOT="/www/wwwroot/persona-live"
PERSONA_LIVE_FRONTEND="/www/wwwroot/persona.swaya.me"
PERSONA_BACKUP_DIR="/home/vinay/persona-backups"
NGINX_BIN="/www/server/nginx/sbin/nginx"

DEV_FRONTEND="$PERSONA_DEV_ROOT/frontend"
DEV_BACKEND="$PERSONA_DEV_ROOT/backend"
LIVE_BACKEND="$PERSONA_LIVE_ROOT/backend"

DEV_SERVICE="swayame-persona-dev.service"
LIVE_SERVICE="swayame-persona.service"

LIVE_VENV="$LIVE_BACKEND/.venv"
DEV_VENV="$DEV_BACKEND/.venv"

# ─── Colours ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET} $*"; }
success() { echo -e "${GREEN}[OK]${RESET}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET} $*"; }
error()   { echo -e "${RED}[ERR]${RESET}  $*" >&2; }
header()  { echo -e "\n${BOLD}${CYAN}══ $* ══${RESET}"; }

confirm() {
    local msg="${1:-Are you sure?}"
    read -rp "$(echo -e "${YELLOW}${msg} [y/N]: ${RESET}")" ans
    [[ "${ans,,}" == "y" ]]
}

timestamp() { date +"%Y%m%d_%H%M%S"; }

# ─── Nginx ───────────────────────────────────────────────────────────────────
nginx_reload() {
    info "Testing nginx config before reload..."
    sudo "$NGINX_BIN" -t
    info "Reloading nginx..."
    sudo "$NGINX_BIN" -s reload
    success "Nginx reloaded."
}

# ─── Health checks ────────────────────────────────────────────────────────────
health_check() {
    local label="$1" port="$2" host="$3"
    info "Health check: $label → http://127.0.0.1:$port/health"
    local response
    response=$(curl -sf -H "Host: $host" "http://127.0.0.1:${port}/health" || true)
    if [[ -n "$response" ]]; then
        success "$label is healthy → $response"
        return 0
    else
        error "$label health check FAILED"
        return 1
    fi
}

health_check_existing_sites() {
    info "Verifying existing swaya.me sites are unaffected..."
    health_check "test.swaya.me" 8001 "test.swaya.me" || { error "⛔ test.swaya.me BROKEN — stop immediately"; return 1; }
    health_check "www.swaya.me"  8000 "www.swaya.me"  || { error "⛔ www.swaya.me BROKEN — stop immediately"; return 1; }
}

# ─── Git helpers ─────────────────────────────────────────────────────────────
git_current_sha() {
    git -C "$PERSONA_DEV_ROOT" rev-parse HEAD
}

git_current_branch() {
    git -C "$PERSONA_DEV_ROOT" rev-parse --abbrev-ref HEAD
}

git_check_clean() {
    git -C "$PERSONA_DEV_ROOT" diff --quiet && git -C "$PERSONA_DEV_ROOT" diff --cached --quiet
}

git_create_release_tag() {
    local tag="$1" message="$2"
    git -C "$PERSONA_DEV_ROOT" tag -a "$tag" -m "$message"
    success "Git tag created: $tag"
}

git_extract_backend_at_tag() {
    local tag="$1" dest="$2"
    info "Extracting backend from git tag $tag..."
    mkdir -p "$dest"
    git -C "$PERSONA_DEV_ROOT" archive "$tag" -- backend/ | tar -x --strip-components=1 -C "$dest"
    success "Backend extracted from $tag → $dest"
}

# ─── Backup helpers ──────────────────────────────────────────────────────────
backup_meta_file() { echo "$PERSONA_BACKUP_DIR/release_${1//\//_}.meta"; }

write_backup_meta() {
    local tag="$1" sha="$2"
    mkdir -p "$PERSONA_BACKUP_DIR"
    cat > "$(backup_meta_file "$tag")" <<EOF
tag=$tag
sha=$sha
branch=$(git_current_branch)
date=$(date -u "+%Y-%m-%d %H:%M:%S UTC")
frontend_backup=$PERSONA_BACKUP_DIR/frontend_$tag
backend_backup=$PERSONA_BACKUP_DIR/backend_$tag
EOF
}

list_releases() {
    # Lists persona/release/* tags sorted by date descending
    git -C "$PERSONA_DEV_ROOT" tag -l "persona/release/*" --sort=-creatordate
}

show_releases() {
    header "Persona Release History"
    local tags
    tags=$(list_releases)
    if [[ -z "$tags" ]]; then
        warn "No persona releases found. Use 'promote-live' to create the first release."
        return
    fi
    local i=1
    while IFS= read -r tag; do
        local sha date has_backup
        sha=$(git -C "$PERSONA_DEV_ROOT" rev-list -n1 "$tag" 2>/dev/null | cut -c1-8)
        date=$(git -C "$PERSONA_DEV_ROOT" log -1 --format="%ai" "$tag" 2>/dev/null | cut -d' ' -f1-2)
        [[ -d "$PERSONA_BACKUP_DIR/frontend_$tag" ]] && has_backup="${GREEN}✓ backup${RESET}" || has_backup="${YELLOW}git-only${RESET}"
        echo -e "  ${BOLD}$i)${RESET} ${CYAN}$tag${RESET}  [$sha] $date  $(echo -e $has_backup)"
        ((i++))
    done <<< "$tags"
}

pick_release() {
    local prompt="${1:-Select release}"
    show_releases
    local tags; tags=$(list_releases)
    [[ -z "$tags" ]] && return 1
    local count; count=$(echo "$tags" | wc -l)
    echo ""
    read -rp "$(echo -e "${YELLOW}${prompt} [1-${count}]: ${RESET}")" sel
    SELECTED_TAG=$(echo "$tags" | sed -n "${sel}p")
    [[ -z "$SELECTED_TAG" ]] && { error "Invalid selection."; return 1; }
    info "Selected: $SELECTED_TAG"
}

# ─── Command: deploy-dev ─────────────────────────────────────────────────────
cmd_deploy_dev() {
    header "Deploy → dev.persona.swaya.me"

    local branch; branch=$(git_current_branch)
    info "Branch: $branch  SHA: $(git_current_sha | cut -c1-8)"

    if ! git_check_clean; then
        warn "Uncommitted changes detected — deploying working tree as-is."
    fi

    info "Building frontend..."
    npm --prefix "$DEV_FRONTEND" run build
    chmod -R a+rX "$DEV_FRONTEND/dist"
    success "Frontend built → $DEV_FRONTEND/dist"

    info "Restarting dev backend ($DEV_SERVICE)..."
    sudo systemctl restart "$DEV_SERVICE"
    sleep 3

    health_check "dev.persona.swaya.me" 8003 "dev.persona.swaya.me"
    success "Dev deploy complete → https://dev.persona.swaya.me"
}

# ─── Command: promote-live ───────────────────────────────────────────────────
cmd_promote_live() {
    header "Promote → live (persona.swaya.me)"

    local branch; branch=$(git_current_branch)
    local sha;    sha=$(git_current_sha)
    local short;  short=$(echo "$sha" | cut -c1-8)

    if [[ "$branch" != "persona" ]]; then
        error "Must be on the persona branch to promote. Current: $branch"
        return 1
    fi

    info "Branch: $branch  SHA: $short"

    if ! git_check_clean; then
        warn "Working tree has uncommitted changes."
        confirm "Continue anyway (promote last committed state)?" || { info "Aborted. Commit your changes first."; return 1; }
    fi

    warn "This will update PRODUCTION (persona.swaya.me)."
    confirm "Proceed with live promotion?" || { info "Aborted."; return 1; }

    local tag="persona/release/$(timestamp)"
    git_create_release_tag "$tag" "Persona release $tag from branch $branch @ $short"
    git -C "$PERSONA_DEV_ROOT" push origin "persona" --tags

    # Backup current live state
    mkdir -p "$PERSONA_BACKUP_DIR"
    if [[ -d "$PERSONA_LIVE_FRONTEND" ]]; then
        info "Backing up live frontend..."
        rsync -a "$PERSONA_LIVE_FRONTEND/" "$PERSONA_BACKUP_DIR/frontend_$tag/"
        success "Frontend backed up."
    fi
    if [[ -d "$LIVE_BACKEND" ]]; then
        info "Backing up live backend..."
        rsync -a --exclude='.venv/' --exclude='.env' --exclude='uploads/' \
            "$LIVE_BACKEND/" "$PERSONA_BACKUP_DIR/backend_$tag/"
        success "Backend backed up."
    fi
    write_backup_meta "$tag" "$sha"

    # Deploy backend
    info "Syncing backend to live..."
    rsync -av --delete \
        --exclude='.venv/' \
        --exclude='.env' \
        --exclude='uploads/' \
        "$DEV_BACKEND/" "$LIVE_BACKEND/"
    success "Backend synced."

    echo "$tag — $(date -u)" > "$LIVE_BACKEND/.deployed_version"

    # Set up live venv if it doesn't exist
    if [[ ! -f "$LIVE_VENV/bin/uvicorn" ]]; then
        info "Creating live Python venv..."
        python3 -m venv "$LIVE_VENV"
        "$LIVE_VENV/bin/pip" install -r "$LIVE_BACKEND/requirements.txt" -q
        success "Live venv created."
    fi

    # Run migrations on live DB
    info "Running Alembic migrations on swayame_persona..."
    (cd "$LIVE_BACKEND" && PYTHONPATH="$LIVE_BACKEND" "$LIVE_VENV/bin/alembic" upgrade head)
    success "Live DB migrations applied."

    # Deploy frontend
    info "Building and deploying frontend to live..."
    npm --prefix "$DEV_FRONTEND" run build
    sudo mkdir -p "$PERSONA_LIVE_FRONTEND"
    sudo rsync -av --delete "$DEV_FRONTEND/dist/" "$PERSONA_LIVE_FRONTEND/"
    sudo chmod -R a+rX "$PERSONA_LIVE_FRONTEND"
    success "Frontend deployed to $PERSONA_LIVE_FRONTEND"

    # Enable and start live service if not running
    if ! sudo systemctl is-active --quiet "$LIVE_SERVICE"; then
        info "Enabling and starting $LIVE_SERVICE..."
        sudo systemctl enable "$LIVE_SERVICE"
        sudo systemctl start "$LIVE_SERVICE"
    else
        info "Restarting live backend ($LIVE_SERVICE)..."
        sudo systemctl restart "$LIVE_SERVICE"
    fi

    nginx_reload
    sleep 3

    if health_check "persona.swaya.me" 8004 "persona.swaya.me"; then
        health_check_existing_sites
        success "Live promotion complete → https://persona.swaya.me"
        echo -e "  ${CYAN}Release tag:${RESET} $tag"
        echo -e "  ${CYAN}SHA:${RESET}         $short ($branch)"
    else
        error "Live health check failed after promotion."
        warn "Consider running: ./persona-deploy.sh rollback-live"
        return 1
    fi
}

# ─── Command: rollback-live ──────────────────────────────────────────────────
cmd_rollback_live() {
    header "Rollback → persona live"

    pick_release "Select persona release to restore" || return 1
    local tag="$SELECTED_TAG"

    warn "This will restore persona.swaya.me to: $tag"
    confirm "Proceed with rollback?" || { info "Aborted."; return; }

    local fe_backup="$PERSONA_BACKUP_DIR/frontend_$tag"
    local be_backup="$PERSONA_BACKUP_DIR/backend_$tag"

    if [[ -d "$fe_backup" ]]; then
        info "Restoring frontend from backup..."
        sudo rsync -av --delete "$fe_backup/" "$PERSONA_LIVE_FRONTEND/"
        success "Frontend restored."
    else
        error "No frontend backup for $tag — cannot restore frontend."
        return 1
    fi

    if [[ -d "$be_backup" ]]; then
        info "Restoring backend from backup..."
        rsync -av --delete \
            --exclude='.venv/' \
            --exclude='.env' \
            --exclude='uploads/' \
            "$be_backup/" "$LIVE_BACKEND/"
        success "Backend restored."
    else
        warn "No backend backup for $tag — extracting from git archive..."
        local tmp; tmp=$(mktemp -d)
        git_extract_backend_at_tag "$tag" "$tmp"
        rsync -av --delete \
            --exclude='.venv/' \
            --exclude='.env' \
            --exclude='uploads/' \
            "$tmp/" "$LIVE_BACKEND/"
        rm -rf "$tmp"
        success "Backend restored from git."
    fi

    echo "$tag (rollback) — $(date -u)" > "$LIVE_BACKEND/.deployed_version"

    info "Restarting live backend..."
    sudo systemctl restart "$LIVE_SERVICE"
    nginx_reload
    sleep 3

    if health_check "persona.swaya.me" 8004 "persona.swaya.me"; then
        success "Rollback to $tag complete."
    else
        error "Health check still failing after rollback. Manual intervention required."
        return 1
    fi
}

# ─── Command: migrate-dev ────────────────────────────────────────────────────
cmd_migrate_dev() {
    header "Alembic migrate → dev DB (swayame_persona_dev)"
    (cd "$DEV_BACKEND" && PYTHONPATH="$DEV_BACKEND" "$DEV_VENV/bin/alembic" upgrade head)
    success "Dev DB migrations applied."
}

# ─── Command: migrate-live ───────────────────────────────────────────────────
cmd_migrate_live() {
    header "Alembic migrate → live DB (swayame_persona)"
    warn "This runs migrations on the LIVE persona database."
    confirm "Proceed?" || { info "Aborted."; return; }
    (cd "$LIVE_BACKEND" && PYTHONPATH="$LIVE_BACKEND" "$LIVE_VENV/bin/alembic" upgrade head)
    success "Live persona DB migrations applied."
}

# ─── Command: health ─────────────────────────────────────────────────────────
cmd_health() {
    header "Persona Health Checks"
    health_check "dev.persona.swaya.me"  8003 "dev.persona.swaya.me"  || true
    health_check "persona.swaya.me"      8004 "persona.swaya.me"      || true

    echo ""
    info "Existing swaya.me sites (must remain unaffected):"
    health_check "test.swaya.me" 8001 "test.swaya.me" || true
    health_check "www.swaya.me"  8000 "www.swaya.me"  || true

    if [[ -f "$LIVE_BACKEND/.deployed_version" ]]; then
        echo ""
        info "Persona live deployed version: $(cat "$LIVE_BACKEND/.deployed_version")"
    fi
}

# ─── Command: status ─────────────────────────────────────────────────────────
cmd_status() {
    header "Persona Service Status"
    local branch; branch=$(git_current_branch 2>/dev/null || echo "unknown")
    local sha; sha=$(git_current_sha 2>/dev/null | cut -c1-8 || echo "?")
    info "Persona branch: $branch  SHA: $sha"
    [[ -f "$LIVE_BACKEND/.deployed_version" ]] && \
        info "Live version: $(cat "$LIVE_BACKEND/.deployed_version")"
    echo ""
    echo -e "${BOLD}Dev backend ($DEV_SERVICE):${RESET}"
    sudo systemctl status "$DEV_SERVICE" --no-pager -l | head -12 || true
    echo ""
    echo -e "${BOLD}Live backend ($LIVE_SERVICE):${RESET}"
    sudo systemctl status "$LIVE_SERVICE" --no-pager -l | head -12 || true
}

# ─── Command: logs ───────────────────────────────────────────────────────────
cmd_logs_dev() {
    header "Persona dev backend logs (Ctrl+C to exit)"
    sudo journalctl -u "$DEV_SERVICE" -f --no-pager
}

cmd_logs_live() {
    header "Persona live backend logs (Ctrl+C to exit)"
    sudo journalctl -u "$LIVE_SERVICE" -f --no-pager
}

# ─── Interactive Menu ─────────────────────────────────────────────────────────
show_menu() {
    local branch sha
    branch=$(git_current_branch 2>/dev/null || echo "unknown")
    sha=$(git_current_sha 2>/dev/null | cut -c1-8 || echo "?")

    echo ""
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║      Persona App Deploy Menu             ║${RESET}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${RESET}"
    echo -e "  Branch: ${BOLD}$branch${RESET} [$sha]"
    [[ -f "$LIVE_BACKEND/.deployed_version" ]] && \
        echo -e "  Live:   $(cat "$LIVE_BACKEND/.deployed_version")"
    echo ""
    echo -e "  ${GREEN}1)${RESET} Deploy → dev.persona.swaya.me    (build + restart dev)"
    echo -e "  ${YELLOW}2)${RESET} Promote → persona.swaya.me       (tag + push to production)"
    echo -e "  ${RED}3)${RESET} Rollback live                     (restore a past release)"
    echo -e "  ${CYAN}4)${RESET} List releases"
    echo ""
    echo -e "  ${CYAN}5)${RESET} Migrate DB → dev"
    echo -e "  ${CYAN}6)${RESET} Migrate DB → live"
    echo ""
    echo -e "  ${CYAN}7)${RESET} Health check (all envs)"
    echo -e "  ${CYAN}8)${RESET} Service status"
    echo -e "  ${CYAN}9)${RESET} Tail logs → dev"
    echo -e "  ${CYAN}a)${RESET} Tail logs → live"
    echo ""
    echo -e "  ${CYAN}0)${RESET} Exit"
    echo ""
}

run_menu() {
    while true; do
        show_menu
        read -rp "$(echo -e "${BOLD}Select option: ${RESET}")" choice
        case "$choice" in
            1) cmd_deploy_dev    ;;
            2) cmd_promote_live  ;;
            3) cmd_rollback_live ;;
            4) show_releases     ;;
            5) cmd_migrate_dev   ;;
            6) cmd_migrate_live  ;;
            7) cmd_health        ;;
            8) cmd_status        ;;
            9) cmd_logs_dev      ;;
            a) cmd_logs_live     ;;
            0) info "Bye."; exit 0 ;;
            *) warn "Unknown option: $choice" ;;
        esac
        echo ""
        read -rp "$(echo -e "${CYAN}Press Enter to return to menu...${RESET}")" _
    done
}

# ─── Entry Point ─────────────────────────────────────────────────────────────
case "${1:-}" in
    deploy-dev)    cmd_deploy_dev    ;;
    promote-live)  cmd_promote_live  ;;
    rollback-live) cmd_rollback_live ;;
    releases)      show_releases     ;;
    migrate-dev)   cmd_migrate_dev   ;;
    migrate-live)  cmd_migrate_live  ;;
    health)        cmd_health        ;;
    status)        cmd_status        ;;
    logs-dev)      cmd_logs_dev      ;;
    logs-live)     cmd_logs_live     ;;
    "")            run_menu          ;;
    *)
        echo "Usage: $0 [deploy-dev|promote-live|rollback-live|releases|migrate-dev|migrate-live|health|status|logs-dev|logs-live]"
        exit 1
        ;;
esac
