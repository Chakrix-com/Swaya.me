#!/usr/bin/env bash
# deploy.sh — Swaya.me CI/CD menu
#
# Usage:
#   ./deploy.sh              → interactive menu
#   ./deploy.sh <command>    → run a specific command
#
# Commands:
#   deploy-test       Build & deploy to test.swaya.me
#   promote-live      Tag + promote test build → live (www.swaya.me)
#   rollback-live     Restore a previous release on live
#   hotfix <tag>      Branch off a past release tag for a targeted fix
#   releases          List all release tags with metadata
#   migrate-test      Run alembic migrations on test DB
#   migrate-live      Run alembic migrations on live DB
#   health            Health-check both environments
#   status            Show systemd service status
#   logs-test         Tail test backend logs
#   logs-live         Tail live backend logs

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
DEV_ROOT="/home/vinay/Swaya.me"
LIVE_ROOT="/www/wwwroot/swaya-live"
LIVE_FRONTEND="/www/wwwroot/www.swaya.me"
BACKUP_DIR="/home/vinay/swaya-backups"
NGINX_BIN="/www/server/nginx/sbin/nginx"

DEV_FRONTEND="$DEV_ROOT/frontend"
DEV_BACKEND="$DEV_ROOT/backend"
LIVE_BACKEND="$LIVE_ROOT/backend"

TEST_SERVICE="swayame-backend-test.service"
LIVE_SERVICE="swayame-backend.service"

LIVE_VENV="$LIVE_BACKEND/.venv"
TEST_VENV="$DEV_BACKEND/.venv"

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

# ─── Live exam safety check ──────────────────────────────────────────────────
# Exits non-zero (and prints who is in the exam) if anyone is actively taking
# an exam on the LIVE database (last activity within 30 minutes, not completed).
check_no_live_exams() {
    local db_user="swayame_user"
    local db_pass="Sw4y4m3_S3cur3_P4ssw0rd!2026"
    local db_name="swayame"

    local result
    result=$(mysql -u"$db_user" -p"$db_pass" -h 127.0.0.1 "$db_name" --silent --skip-column-names 2>/dev/null <<'SQL'
SELECT CONCAT(p.display_name, ' <', p.email, '> — ', q.title,
              ' (', TIMESTAMPDIFF(MINUTE, p.started_at, NOW()), ' min in, ',
              ROUND(q.exam_time_limit_seconds/60 - TIMESTAMPDIFF(MINUTE, p.started_at, NOW())),
              ' min left)')
FROM participants p
JOIN quiz_sessions qs ON p.session_id = qs.id
JOIN quizzes q        ON qs.quiz_id   = q.id
WHERE p.completed_at  IS NULL
  AND p.is_abandoned  = 0
  AND qs.status       = 'ACTIVE'
  AND q.exam_slug     IS NOT NULL
  AND p.started_at    IS NOT NULL
  AND TIMESTAMPDIFF(MINUTE, p.last_activity_at, NOW()) < 30;
SQL
)

    if [[ -n "$result" ]]; then
        error "⛔  Cannot deploy — participants are actively taking exams:"
        while IFS= read -r line; do
            echo -e "     ${YELLOW}•${RESET} $line"
        done <<< "$result"
        error "Wait for them to finish (or exceed 30 min of inactivity) before promoting."
        return 1
    fi
    success "No active exam participants — safe to deploy."
    return 0
}

# ─── Nginx ───────────────────────────────────────────────────────────────────
nginx_reload() {
    info "Reloading nginx..."
    sudo "$NGINX_BIN" -s reload
    success "Nginx reloaded."
}

# ─── Health check ─────────────────────────────────────────────────────────────
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

# ─── Git helpers ─────────────────────────────────────────────────────────────
git_check_clean() {
    # Returns 0 if working tree is clean
    git -C "$DEV_ROOT" diff --quiet && git -C "$DEV_ROOT" diff --cached --quiet
}

git_current_sha() {
    git -C "$DEV_ROOT" rev-parse HEAD
}

git_current_branch() {
    git -C "$DEV_ROOT" rev-parse --abbrev-ref HEAD
}

git_create_release_tag() {
    local tag="$1" message="$2"
    git -C "$DEV_ROOT" tag -a "$tag" -m "$message"
    success "Git tag created: $tag"
}

# Extract backend files at a given git tag into a directory (no checkout needed)
git_extract_backend_at_tag() {
    local tag="$1" dest="$2"
    info "Extracting backend from git tag $tag..."
    mkdir -p "$dest"
    git -C "$DEV_ROOT" archive "$tag" -- backend/ | tar -x --strip-components=1 -C "$dest"
    success "Backend extracted from $tag → $dest"
}

# ─── Backup helpers ──────────────────────────────────────────────────────────
backup_meta_file() { echo "$BACKUP_DIR/release_${1//\//_}.meta"; }

write_backup_meta() {
    local tag="$1" sha="$2"
    cat > "$(backup_meta_file "$tag")" <<EOF
tag=$tag
sha=$sha
branch=$(git_current_branch)
date=$(date -u "+%Y-%m-%d %H:%M:%S UTC")
frontend_backup=$BACKUP_DIR/frontend_$tag
backend_backup=$BACKUP_DIR/backend_$tag
EOF
}

list_releases() {
    # Lists release/* tags sorted by date descending
    git -C "$DEV_ROOT" tag -l "release/*" --sort=-creatordate
}

show_releases() {
    header "Release History"
    local tags
    tags=$(list_releases)
    if [[ -z "$tags" ]]; then
        warn "No releases found. Use 'promote-live' to create the first release."
        return
    fi
    local i=1
    while IFS= read -r tag; do
        local meta_file; meta_file=$(backup_meta_file "$tag")
        local sha date branch has_backup
        sha=$(git -C "$DEV_ROOT" rev-list -n1 "$tag" 2>/dev/null | cut -c1-8)
        date=$(git -C "$DEV_ROOT" log -1 --format="%ai" "$tag" 2>/dev/null | cut -d' ' -f1-2)
        branch=$(grep "^branch=" "$meta_file" 2>/dev/null | cut -d= -f2 || echo "unknown")
        [[ -d "$BACKUP_DIR/frontend_$tag" ]] && has_backup="${GREEN}✓ backup${RESET}" || has_backup="${YELLOW}git-only${RESET}"
        echo -e "  ${BOLD}$i)${RESET} ${CYAN}$tag${RESET}  [$sha] $date  branch:$branch  $(echo -e $has_backup)"
        ((i++))
    done <<< "$tags"
}

# Prompt user to select a release; sets $SELECTED_TAG
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

# ─── Command: deploy-test ────────────────────────────────────────────────────
cmd_deploy_test() {
    header "Deploy → test.swaya.me"

    local branch; branch=$(git_current_branch)
    info "Branch: $branch  SHA: $(git_current_sha | cut -c1-8)"

    if ! git_check_clean; then
        warn "Uncommitted changes detected — deploying working tree as-is."
    fi

    info "Building frontend..."
    npm --prefix "$DEV_FRONTEND" run build
    # Ensure nginx worker can traverse and read test static assets.
    chmod 751 "/home/vinay" "$DEV_ROOT"
    chmod -R a+rX "$DEV_FRONTEND/dist"
    success "Frontend built → $DEV_FRONTEND/dist"

    info "Restarting test backend ($TEST_SERVICE)..."
    sudo systemctl restart "$TEST_SERVICE"

    nginx_reload

    sleep 2
    health_check "test.swaya.me" 8001 "test.swaya.me"
    success "Test deploy complete → https://test.swaya.me"
}

# ─── Command: promote-live ───────────────────────────────────────────────────
cmd_promote_live() {
    header "Promote → live (www.swaya.me)"

    # 1. Git state checks
    local branch; branch=$(git_current_branch)
    local sha;    sha=$(git_current_sha)
    local short;  short=$(echo "$sha" | cut -c1-8)

    info "Branch: $branch  SHA: $short"

    if ! git_check_clean; then
        warn "Working tree has uncommitted changes."
        warn "These changes will NOT be included in the release tag."
        confirm "Continue anyway (promote last committed state)?" || { info "Aborted. Commit your changes first."; return 1; }
    fi

    # Safety: abort if anyone is mid-exam on live
    check_no_live_exams || return 1

    warn "This will update PRODUCTION (www.swaya.me)."
    confirm "Proceed?" || { info "Aborted."; return; }

    local ts; ts=$(timestamp)
    local tag="release/$ts"

    # 2. Create release tag BEFORE deploying (audit trail)
    git_create_release_tag "$tag" "Release from branch $branch at $short"

    # 3. Backup current live state
    mkdir -p "$BACKUP_DIR"
    info "Backing up live frontend → $BACKUP_DIR/frontend_$tag"
    mkdir -p "$BACKUP_DIR/frontend_$tag"
    rsync -a "$LIVE_FRONTEND/" "$BACKUP_DIR/frontend_$tag/"
    success "Frontend backup done."

    info "Backing up live backend → $BACKUP_DIR/backend_$tag"
    mkdir -p "$BACKUP_DIR/backend_$tag"
    rsync -a \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='uploads/' \
        "$LIVE_BACKEND/" "$BACKUP_DIR/backend_$tag/"
    success "Backend backup done."

    # Save metadata (tag, sha, branch, dates, backup paths)
    write_backup_meta "$tag" "$sha"

    # 4. Sync backend code to live (exclude sensitive/runtime files)
    info "Syncing backend code → $LIVE_BACKEND ..."
    rsync -av --delete \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='uploads/' \
        "$DEV_BACKEND/" "$LIVE_BACKEND/"
    success "Backend synced."

    # 5. Update pip dependencies if requirements changed
    if ! diff -q "$DEV_BACKEND/requirements.txt" "$BACKUP_DIR/backend_$tag/requirements.txt" &>/dev/null 2>&1; then
        info "requirements.txt changed — installing dependencies..."
        "$LIVE_VENV/bin/pip" install --no-deps -r "$LIVE_BACKEND/requirements.txt" -q
        success "Dependencies updated."
    else
        info "requirements.txt unchanged — skipping pip install."
    fi

    # 6. Run DB migrations on live
    info "Running alembic migrations on live DB..."
    (cd "$LIVE_BACKEND" && PYTHONPATH="$LIVE_BACKEND" "$LIVE_VENV/bin/alembic" upgrade head)
    success "Live DB migrations applied."

    # 7. Deploy frontend (build must already be done via deploy-test, or build now)
    if [[ ! -d "$DEV_FRONTEND/dist" ]]; then
        info "No dist found — building frontend first..."
        npm --prefix "$DEV_FRONTEND" run build
    fi
    info "Deploying frontend → $LIVE_FRONTEND ..."
    sudo rsync -av --delete "$DEV_FRONTEND/dist/" "$LIVE_FRONTEND/"
    success "Frontend deployed."

    # 8. Write deployed version marker to live backend
    echo "$tag ($short) on $branch — $(date -u)" > "$LIVE_BACKEND/.deployed_version"

    # 9. Restart live backend
    info "Restarting live backend ($LIVE_SERVICE)..."
    sudo systemctl restart "$LIVE_SERVICE"

    nginx_reload
    sleep 8

    # 10. Health check — auto-rollback on failure
    if ! health_check "www.swaya.me" 8000 "www.swaya.me"; then
        error "Live health check FAILED. Initiating automatic rollback..."
        _restore_release "$tag"
        return 1
    fi

    # 11. Push branch + release tag to GitHub
    info "Pushing branch '$branch' and tag '$tag' to GitHub..."
    git -C "$DEV_ROOT" push origin "$branch"
    git -C "$DEV_ROOT" push origin "$tag"
    success "GitHub updated → branch '$branch' + tag '$tag'"

    success "Live promotion complete → https://www.swaya.me"
    echo -e "  ${CYAN}Release tag:${RESET} $tag"
    echo -e "  ${CYAN}SHA:${RESET}         $short ($branch)"
    echo -e "  ${CYAN}Backup at:${RESET}   $BACKUP_DIR/*_$tag"
}

# ─── Command: rollback-live ──────────────────────────────────────────────────
cmd_rollback_live() {
    header "Rollback → live"

    pick_release "Select release to restore" || return 1
    local tag="$SELECTED_TAG"

    warn "This will restore production to: $tag"
    confirm "Proceed with rollback?" || { info "Aborted."; return; }

    _restore_release "$tag"
}

_restore_release() {
    local tag="$1"
    local fe_backup="$BACKUP_DIR/frontend_$tag"
    local be_backup="$BACKUP_DIR/backend_$tag"

    # Frontend: must come from file backup (dist is gitignored)
    if [[ -d "$fe_backup" ]]; then
        info "Restoring frontend from file backup..."
        sudo rsync -av --delete "$fe_backup/" "$LIVE_FRONTEND/"
        success "Frontend restored."
    else
        error "No frontend backup for $tag — cannot restore frontend."
        error "You will need to manually rebuild frontend at that git tag."
        return 1
    fi

    # Backend: prefer file backup; fall back to git archive
    if [[ -d "$be_backup" ]]; then
        info "Restoring backend from file backup..."
        rsync -av --delete \
            --exclude='.venv/' \
            --exclude='.env' \
            --exclude='uploads/' \
            "$be_backup/" "$LIVE_BACKEND/"
        success "Backend restored from file backup."
    else
        warn "No file backup found for $tag — extracting from git archive..."
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
    sleep 8

    if health_check "www.swaya.me" 8000 "www.swaya.me"; then
        success "Rollback to $tag complete."
    else
        error "Health check still failing after rollback. Manual intervention required."
        return 1
    fi
}

# ─── Command: hotfix ─────────────────────────────────────────────────────────
cmd_hotfix() {
    header "Start Hotfix Branch from Past Release"
    echo ""
    echo "  Use this when you need to fix a specific past release"
    echo "  without including changes made after it on main."
    echo ""

    pick_release "Select release to branch from" || return 1
    local tag="$SELECTED_TAG"

    local default_name="hotfix/$(date +%Y%m%d)"
    read -rp "$(echo -e "${YELLOW}Branch name [${default_name}]: ${RESET}")" branch_name
    branch_name="${branch_name:-$default_name}"

    git -C "$DEV_ROOT" checkout -b "$branch_name" "$tag"
    success "Created and switched to branch: $branch_name (based on $tag)"
    echo ""
    info "Make your fixes, then run:"
    echo "  ./deploy.sh deploy-test    # test the fix"
    echo "  ./deploy.sh promote-live   # promote hotfix to live"
    echo ""
    warn "Remember to merge this branch back into main when done:"
    echo "  git checkout main && git merge $branch_name"
}

# ─── Command: releases ───────────────────────────────────────────────────────
cmd_releases() {
    show_releases
}

# ─── Command: migrate-test ───────────────────────────────────────────────────
cmd_migrate_test() {
    header "Alembic migrate → test DB (swayame_test)"
    (cd "$DEV_BACKEND" && "$TEST_VENV/bin/alembic" upgrade head)
    success "Test DB migrations applied."
}

# ─── Command: migrate-live ───────────────────────────────────────────────────
cmd_migrate_live() {
    header "Alembic migrate → live DB (swayame)"
    warn "This runs migrations on the LIVE database."
    confirm "Proceed?" || { info "Aborted."; return; }
    (cd "$LIVE_BACKEND" && PYTHONPATH="$LIVE_BACKEND" "$LIVE_VENV/bin/alembic" upgrade head)
    success "Live DB migrations applied."
}

# ─── Command: health ─────────────────────────────────────────────────────────
cmd_health() {
    header "Health Checks"
    health_check "test.swaya.me" 8001 "test.swaya.me" || true
    health_check "www.swaya.me"  8000 "www.swaya.me"  || true

    # Show currently deployed version on live
    if [[ -f "$LIVE_BACKEND/.deployed_version" ]]; then
        echo ""
        info "Live deployed version: $(cat "$LIVE_BACKEND/.deployed_version")"
    fi
}

# ─── Command: status ─────────────────────────────────────────────────────────
cmd_status() {
    header "Service Status"
    local branch; branch=$(git_current_branch)
    local sha; sha=$(git_current_sha | cut -c1-8)
    info "Dev branch: $branch  SHA: $sha"
    [[ -f "$LIVE_BACKEND/.deployed_version" ]] && \
        info "Live version: $(cat "$LIVE_BACKEND/.deployed_version")"
    echo ""
    echo -e "${BOLD}Test backend ($TEST_SERVICE):${RESET}"
    sudo systemctl status "$TEST_SERVICE" --no-pager -l | head -12 || true
    echo ""
    echo -e "${BOLD}Live backend ($LIVE_SERVICE):${RESET}"
    sudo systemctl status "$LIVE_SERVICE" --no-pager -l | head -12 || true

    # Check for worker count (concurrency warning)
    local live_workers; live_workers=$(systemctl cat "$LIVE_SERVICE" 2>/dev/null | grep -oP "workers \d+" | grep -oP "\d+" || echo "0")
    if [[ "$live_workers" -gt 0 && "$live_workers" -lt 4 ]]; then
        echo ""
        warn "CONCURRENCY WARNING: Live backend is running with only $live_workers workers."
        warn "For 700+ simultaneous users, it is recommended to use at least 4-8 workers."
        warn "To fix: sudo systemctl edit --full $LIVE_SERVICE"
        warn "Change: --workers 4"
        warn "Then:   sudo systemctl daemon-reload && sudo systemctl restart $LIVE_SERVICE"
    fi
}

# ─── Command: logs ───────────────────────────────────────────────────────────
cmd_logs_test() {
    header "Test backend logs (Ctrl+C to exit)"
    sudo journalctl -u "$TEST_SERVICE" -f --no-pager
}

cmd_logs_live() {
    header "Live backend logs (Ctrl+C to exit)"
    sudo journalctl -u "$LIVE_SERVICE" -f --no-pager
}

# ─── Interactive Menu ─────────────────────────────────────────────────────────
show_menu() {
    local branch sha
    branch=$(git_current_branch 2>/dev/null || echo "unknown")
    sha=$(git_current_sha 2>/dev/null | cut -c1-8 || echo "?")
    local clean_indicator
    git_check_clean 2>/dev/null && clean_indicator="${GREEN}clean${RESET}" || clean_indicator="${YELLOW}dirty${RESET}"

    echo ""
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║         Swaya.me Deploy Menu             ║${RESET}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${RESET}"
    echo -e "  Branch: ${BOLD}$branch${RESET} [$sha]  $(echo -e $clean_indicator)"
    [[ -f "$LIVE_BACKEND/.deployed_version" ]] && \
        echo -e "  Live:   $(cat "$LIVE_BACKEND/.deployed_version")"
    echo ""
    echo -e "  ${GREEN}1)${RESET} Deploy → test.swaya.me       (build + restart test)"
    echo -e "  ${YELLOW}2)${RESET} Promote → live www.swaya.me  (tag + push to production)"
    echo -e "  ${RED}3)${RESET} Rollback live                 (restore a past release)"
    echo -e "  ${CYAN}4)${RESET} Start hotfix branch          (fix from a past release)"
    echo -e "  ${CYAN}5)${RESET} List releases"
    echo ""
    echo -e "  ${CYAN}6)${RESET} Migrate DB → test"
    echo -e "  ${CYAN}7)${RESET} Migrate DB → live"
    echo ""
    echo -e "  ${CYAN}8)${RESET} Health check (both envs)"
    echo -e "  ${CYAN}9)${RESET} Service status"
    echo -e "  ${CYAN}a)${RESET} Tail logs → test"
    echo -e "  ${CYAN}b)${RESET} Tail logs → live"
    echo ""
    echo -e "  ${CYAN}0)${RESET} Exit"
    echo ""
}

run_menu() {
    while true; do
        show_menu
        read -rp "$(echo -e "${BOLD}Select option: ${RESET}")" choice
        case "$choice" in
            1) cmd_deploy_test   ;;
            2) cmd_promote_live  ;;
            3) cmd_rollback_live ;;
            4) cmd_hotfix        ;;
            5) cmd_releases      ;;
            6) cmd_migrate_test  ;;
            7) cmd_migrate_live  ;;
            8) cmd_health        ;;
            9) cmd_status        ;;
            a) cmd_logs_test     ;;
            b) cmd_logs_live     ;;
            0) info "Bye."; exit 0 ;;
            *) warn "Unknown option: $choice" ;;
        esac
        echo ""
        read -rp "$(echo -e "${CYAN}Press Enter to return to menu...${RESET}")" _
    done
}

# ─── Entry Point ─────────────────────────────────────────────────────────────
case "${1:-}" in
    deploy-test)   cmd_deploy_test   ;;
    promote-live)  cmd_promote_live  ;;
    rollback-live) cmd_rollback_live ;;
    hotfix)        cmd_hotfix        ;;
    releases)      cmd_releases      ;;
    migrate-test)  cmd_migrate_test  ;;
    migrate-live)  cmd_migrate_live  ;;
    health)        cmd_health        ;;
    status)        cmd_status        ;;
    logs-test)     cmd_logs_test     ;;
    logs-live)     cmd_logs_live     ;;
    "")            run_menu          ;;
    *)
        echo "Usage: $0 [deploy-test|promote-live|rollback-live|hotfix|releases|migrate-test|migrate-live|health|status|logs-test|logs-live]"
        exit 1
        ;;
esac
