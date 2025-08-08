#!/bin/bash
# ============================================================================
# 🛠️ DreamArtMachine | Unified Project Toolkit – v3.1 (Run Code Stacker + Solid Backups)
# ============================================================================
# Central CLI for deploy, QA, backups (with hardcoded excludes + dry-run),
# health checks, logs, and developer tools.
# ============================================================================

set -euo pipefail

# ============================================================================
# 1) CONFIG & PATHS
# ============================================================================
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Put backups OUTSIDE the source tree to prevent “backup-ception”
BACKUP_DIR="/backups"
LOG_DIR="$ROOT_DIR/logs"
VENV_DIR="$ROOT_DIR/venv"
STACKER_SCRIPT="$ROOT_DIR/code-stacker.sh"

GUNICORN_SERVICE="dreamartmachine.service"
NGINX_SERVICE="nginx.service"

REMOTE_NAME="gdrive"
RCLONE_FOLDER="DreamArtMachine-Backups"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

if [[ -t 1 ]]; then
    C_RESET='\033[0m'
    C_RED='\033[0;31m'
    C_GREEN='\033[0;32m'
    C_YELLOW='\033[0;33m'
    C_BLUE='\033[0;34m'
    C_CYAN='\033[0;36m'
else
    C_RESET=''; C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_CYAN=''
fi

mkdir -p "$LOG_DIR"
# Ensure backup dir exists and is writable by current user
if [[ ! -d "$BACKUP_DIR" ]]; then
    if sudo mkdir -p "$BACKUP_DIR"; then
        sudo chown "$(id -u)":"$(id -g)" "$BACKUP_DIR" || true
    fi
fi

# ============================================================================
# 2) LOGGING & UTILS
# ============================================================================
log_action() {
    local message="$1"
    local log_file="$LOG_DIR/toolkit-actions-$(date +%Y-%m-%d).log"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${message}" >> "$log_file"
}

print_success() { echo -e "${C_GREEN}✅ $1${C_RESET}"; }
print_error()   { echo -e "${C_RED}❌ $1${C_RESET}"; }
print_warning() { echo -e "${C_YELLOW}⚠️ $1${C_RESET}"; }
print_info()    { echo -e "${C_CYAN}ℹ️ $1${C_RESET}"; }

check_venv() {
    if [[ -z "${VIRTUAL_ENV-}" ]]; then
        print_error "Virtual environment is not activated."
        print_warning "Run: source venv/bin/activate"
        return 1
    fi
}

# ============================================================================
# 3) SERVICES
# ============================================================================
restart_service() {
    local service_name="$1"
    print_info "Restarting ${service_name}..."
    if sudo systemctl restart "$service_name"; then
        print_success "${service_name} restarted."
        log_action "Service restarted: ${service_name}"
    else
        print_error "Failed to restart ${service_name}"
        print_info  "Check: journalctl -u ${service_name} --no-pager"
        log_action "Service restart FAILED: ${service_name}"
    fi
}

reboot_server() {
    print_warning "This will reboot the entire server."
    read -p "Are you sure? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        log_action "🚨 REBOOT triggered from toolkit"
        sudo reboot
    else
        print_info "Reboot cancelled."
    fi
}

# ============================================================================
# 4) GIT
# ============================================================================
git_pull_and_restart() {
    print_info "Git pull (auto-stash if needed)..."
    if [[ -n "$(git status --porcelain)" ]]; then
        git stash push -m "Auto stash by toolkit before pull on $(date)"
        log_action "Local changes stashed before pull"
    fi

    if git pull; then
        log_action "Git pull OK"
        print_success "Pulled latest. Running QA..."
        if run_tests; then
            print_success "QA passed. Restarting app..."
            restart_service "$GUNICORN_SERVICE"
        else
            print_error "QA failed. App NOT restarted."
            log_action "PULL FAILED QA"
        fi
    else
        print_error "Git pull failed."
        log_action "Git pull FAILED"
    fi
}

git_push_safe() {
    print_info "Running QA before push..."
    if ! run_tests; then
        print_error "QA failed. Push aborted."
        log_action "Push aborted (QA failed)"
        return 1
    fi
    git add .
    git commit -m "🔄 Auto-commit via toolkit on $(date)" || print_info "Nothing to commit."
    if git push; then
        print_success "Pushed to remote."
        log_action "Git push OK"
    else
        print_error "Git push failed."
        log_action "Git push FAILED"
    fi
}

# ============================================================================
# 5) BACKUP / RESTORE
# ============================================================================

# Hardcoded excludes – no txt file needed
EXCLUDES=(
  --exclude=.vscode-server
  --exclude=.venv
  --exclude=venv
  --exclude=.cache
  --exclude=__pycache__
  --exclude=*.log
  --exclude=*.tmp
  --exclude=*.pyc
  --exclude=node_modules
  --exclude=.DS_Store
  --exclude=art-processing
  --exclude=inputs
  --exclude=outputs
  # NOTE: No need to exclude backups now (archive is outside $ROOT_DIR)
)

backup_dry_run() {
    print_info "Dry-run: listing what WOULD be backed up (no file created)..."
    local dry_log="$LOG_DIR/backup-dryrun-$TIMESTAMP.log"
    # -c (create), -v (verbose), to /dev/null, list files that would be added
    if tar -cvf /dev/null "${EXCLUDES[@]}" -C "$ROOT_DIR" . | tee "$dry_log"; then
        print_success "Dry-run complete. Log: $dry_log"
        log_action "Backup dry-run saved: $(basename "$dry_log")"
    else
        print_error "Dry-run failed."
    fi
}

run_full_backup() {
    local archive_name="dream-backup-${TIMESTAMP}.tar.gz"
    local archive_path="${BACKUP_DIR}/${archive_name}"

    print_info "Creating backup at: ${archive_path}"
    # Create gz archive with excludes; archive root is $ROOT_DIR
    if tar -czvf "$archive_path" "${EXCLUDES[@]}" -C "$ROOT_DIR" . > "$BACKUP_DIR/backup-$TIMESTAMP.log" 2>&1; then
        print_success "Local backup created: ${archive_path}"
        log_action "Backup created: ${archive_name}"
    else
        print_error "Backup failed. Check log: $BACKUP_DIR/backup-$TIMESTAMP.log"
        return 1
    fi

    # Keep only last 7 backups
    ls -tp "$BACKUP_DIR"/dream-backup-*.tar.gz 2>/dev/null | grep -v '/$' | tail -n +8 | xargs -r rm -- || true
}

upload_to_gdrive() {
    local archive_path="$1"
    if [[ ! -f "$archive_path" ]]; then
        print_error "Archive not found: $archive_path"
        return 1
    fi
    print_info "Uploading to Google Drive ($REMOTE_NAME:$RCLONE_FOLDER)..."
    if rclone copy --progress "$archive_path" "$REMOTE_NAME:$RCLONE_FOLDER"; then
        print_success "Uploaded: $(basename "$archive_path")"
        log_action "GDrive upload OK: $(basename "$archive_path")"
    else
        print_error "GDrive upload failed."
        log_action "GDrive upload FAILED: $(basename "$archive_path")"
        return 1
    fi
}

restore_from_backup() {
    print_info "Searching local backups..."
    mapfile -t backups < <(ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz 2>/dev/null || true)
    if [ ${#backups[@]} -eq 0 ]; then
        print_warning "No local backups found in $BACKUP_DIR"
        return 1
    fi
    echo "Available backups:"
    select archive_path in "${backups[@]}"; do
        [[ -n "${archive_path:-}" ]] && break
        print_error "Invalid selection."
    done

    print_warning "This will overwrite files under $ROOT_DIR."
    read -p "Proceed with restore from '$(basename "$archive_path")'? (y/N): " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { print_info "Restore cancelled."; return; }

    print_info "Restoring..."
    tar -xzf "$archive_path" -C "$ROOT_DIR"
    print_success "Restore complete."
    log_action "Restore from $(basename "$archive_path")"
    print_warning "Re-check your .env, dependencies, and restart services."
}

# ============================================================================
# 6) QA & MAINTENANCE
# ============================================================================
run_tests() {
    check_venv || return 1
    print_info "Running QA..."
    local status=0

    if command -v ruff >/dev/null 2>&1; then
        print_info "Ruff..."
        ruff check . || status=1
    fi

    if command -v pip-audit >/dev/null 2>&1; then
        print_info "pip-audit..."
        pip-audit || status=1
    fi

    if command -v pytest >/dev/null 2>&1; then
        print_info "pytest..."
        pytest --check-links --maxfail=3 --disable-warnings | tee "$LOG_DIR/test-output-$TIMESTAMP.log" || status=1
        log_action "Tests complete: test-output-$TIMESTAMP.log"
    fi

    if [[ -f "tools/validate_integrity.py" ]]; then
        print_info "Custom integrity check..."
        python tools/validate_integrity.py || status=1
    fi

    if [[ $status -ne 0 ]]; then
        print_error "QA FAILED."
        log_action "QA FAILED"
        return 1
    fi
    print_success "QA PASSED."
    log_action "QA PASSED"
}

update_dependencies() {
    check_venv || return 1
    print_info "Updating dependencies from requirements.txt..."
    if pip install --upgrade -r requirements.txt; then
        pip freeze > requirements.txt
        print_success "Dependencies updated."
        log_action "Dependencies updated"
        print_warning "Restart app to apply changes."
    else
        print_error "Dependency update failed."
    fi
}

cleanup_disk() {
    print_info "Cleaning logs/backups older than 30 days..."
    find "$LOG_DIR" -type f -mtime +30 -print -delete | (grep -q . && print_success "Old logs removed." || print_info "No old logs.")
    find "$BACKUP_DIR" -type f -mtime +30 -print -delete | (grep -q . && print_success "Old backups removed." || print_info "No old backups.")
    log_action "Disk cleanup run"
}

# ============================================================================
# 7) DEV TOOLS
# ============================================================================
system_health_check() {
    print_info "Generating system health report..."
    local report_file="$LOG_DIR/health-check-$TIMESTAMP.md"
    {
        echo "# System Health Report - $(date)"
        echo -e "\n## Disk Usage"
        df -h
        echo -e "\n## Memory Usage"
        free -h
        echo -e "\n## .env Presence"
        [[ -f "$ROOT_DIR/.env" ]] && echo "✅ .env present" || echo "❌ .env MISSING"
        echo -e "\n## Top Memory Processes"
        ps aux --sort=-%mem | head -n 6
        echo -e "\n## Top CPU Processes"
        ps aux --sort=-%cpu | head -n 6
        echo -e "\n## Gunicorn Status"
        systemctl status --no-pager "$GUNICORN_SERVICE" || true
    } > "$report_file"
    print_success "Health report: $report_file"
    log_action "Health report saved: $(basename "$report_file")"
}

view_live_log() {
    local gunicorn_log="$LOG_DIR/gunicorn.log"
    local app_log="$LOG_DIR/app.log"
    if [[ -f "$gunicorn_log" ]]; then
        print_info "Tailing $gunicorn_log ..."
        tail -f "$gunicorn_log"
    elif [[ -f "$app_log" ]]; then
        print_info "Tailing $app_log ..."
        tail -f "$app_log"
    else
        print_error "No gunicorn.log or app.log in $LOG_DIR"
    fi
}

run_code_stacker() {
    print_info "Running Code Stacker..."
    if [[ ! -f "$STACKER_SCRIPT" ]]; then
        print_error "code-stacker.sh not found at: $STACKER_SCRIPT"
        print_info "Create it or update STACKER_SCRIPT path in toolkit."
        return 1
    fi
    if [[ ! -x "$STACKER_SCRIPT" ]]; then
        print_info "Making code-stacker.sh executable..."
        chmod +x "$STACKER_SCRIPT" || true
    fi
    if "$STACKER_SCRIPT"; then
        print_success "Code stack generated."
        log_action "Code Stacker run"
    else
        print_error "Code Stacker failed."
    fi
}


# ============================================================================
# 8) MENUS
# ============================================================================
backup_menu() {
    while true; do
        echo -e "\n${C_BLUE}--- 📦 Backup & Restore Menu ---${C_RESET}"
        echo "[1] Dry-Run: show what WOULD be backed up"
        echo "[2] Run Full Local Backup"
        echo "[3] Run Backup + Upload to Google Drive"
        echo "[4] Restore From Local Backup"
        echo "[0] Back to Main Menu"
        read -p "Choose an option: " opt
        case "$opt" in
            1) backup_dry_run ;;
            2) run_full_backup ;;
            3) run_full_backup && latest=$(ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz | head -n1) && upload_to_gdrive "$latest" ;;
            4) restore_from_backup ;;
            0) break ;;
            *) print_error "Invalid option." ;;
        esac
    done
}

restart_menu() {
    while true; do
        echo -e "\n${C_RED}--- ⚡️ System Restart Menu ---${C_RESET}"
        print_warning "Use with care."
        echo "[1] Restart Application (Gunicorn)"
        echo "[2] Restart Web Server (NGINX)"
        echo "[3] REBOOT ENTIRE SERVER"
        echo "[0] Back to Main Menu"
        read -p "Choose an option: " opt
        case "$opt" in
            1) restart_service "$GUNICORN_SERVICE" ;;
            2) restart_service "$NGINX_SERVICE" ;;
            3) reboot_server ;;
            0) break ;;
            *) print_error "Invalid option." ;;
        esac
    done
}

main_menu() {
    while true; do
        echo -e "\n${C_CYAN}🌟 Project Toolkit – DreamArtMachine 🌟${C_RESET}"
        echo -e "${C_YELLOW}--- Git & Deployment ---${C_RESET}"
        echo " [1] Git PULL & Deploy"
        echo " [2] Run QA, Commit & PUSH"
        echo -e "${C_YELLOW}--- System Management ---${C_RESET}"
        echo " [3] Backup & Restore"
        echo " [4] System Restart Options"
        echo " [5] System Health Check"
        echo -e "${C_YELLOW}--- QA & Maintenance ---${C_RESET}"
        echo " [6] Run Full QA Suite"
        echo " [7] Update Python Dependencies"
        echo " [8] Cleanup Old Logs & Backups"
        echo -e "${C_YELLOW}--- Developer Tools ---${C_RESET}"
        echo " [9] View Live Application Log"
        echo "[10] Run Code Stacker Tool"
        echo "[0] Exit"
        read -p "Choose an option: " opt
        case "$opt" in
            1) git_pull_and_restart ;;
            2) git_push_safe ;;
            3) backup_menu ;;
            4) restart_menu ;;
            5) system_health_check ;;
            6) run_tests ;;
            7) update_dependencies ;;
            8) cleanup_disk ;;
            9) view_live_log ;;
            10) run_code_stacker ;;
            0) echo "👋 Bye legend!"; exit 0 ;;
            *) print_error "Invalid option." ;;
        esac
    done
}

# ============================================================================
# 9) ENTRYPOINT
# ============================================================================
if [[ $# -gt 0 ]]; then
    case "$1" in
        --backup) run_full_backup ;;
        --backup-upload) run_full_backup && latest=$(ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz | head -n1) && upload_to_gdrive "$latest" ;;
        --test) run_tests ;;
        --pull) git_pull_and_restart ;;
        --push) git_push_safe ;;
        --stack) run_code_stacker ;;
        --backup-dryrun) backup_dry_run ;;
        *) print_error "Invalid arg '$1'. Run without args for menu." ;;
    esac
else
    main_menu
fi
