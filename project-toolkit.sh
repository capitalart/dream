#!/bin/bash
set -e

# ============================================================================
# 🛠️ DreamArtMachine | Unified Project Toolkit – Git, Backup, QA, GDrive, Logs
# ============================================================================
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$ROOT_DIR/backups"
LOG_DIR="$ROOT_DIR/logs"
INCLUDE_FILE="$ROOT_DIR/backup_includes.txt"
EXTRA_FILE="$ROOT_DIR/files-to-backup.txt"
EXCLUDE_FILE="$ROOT_DIR/backup_excludes.txt"
REMOTE_NAME="gdrive"
RCLONE_FOLDER="DreamArtMachine-Backups"
STACKER_SCRIPT="$ROOT_DIR/code-stacker.sh"
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)

DEFAULT_EXCLUDES=(".git" "*.pyc" "__pycache__" ".env" ".DS_Store" "venv" "backups")

mkdir -p "$LOG_DIR"

log_action() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_DIR/toolkit-actions-$TIMESTAMP.log"
}

# ============================================================================
# GIT ACTIONS
# ============================================================================
git_pull_safe() {
    echo "🔄 Pulling latest changes..."
    if [[ -n "$(git status --porcelain)" ]]; then
        git stash push -m "Auto stash before pull"
        log_action "🟡 Local changes stashed before pull"
    fi
    git pull && log_action "✅ Git pull successful"
}

git_push_safe() {
    echo "📤 Preparing to push changes..."
    if ! run_tests; then
        echo "❌ QA checks failed. Push aborted."
        log_action "❌ Git push aborted: QA failed"
        return 1
    fi
    git add .
    git commit -m "🔄 Auto commit via toolkit on $TIMESTAMP" || echo "ℹ️ Nothing to commit."
    git push && log_action "✅ Git push successful"
}

# ============================================================================
# QA / QC / TESTING
# ============================================================================
run_tests() {
    echo "🧪 Running full QA suite..."
    local status=0
    if command -v pytest >/dev/null 2>&1; then
        pytest --maxfail=3 --disable-warnings | tee "$LOG_DIR/test-output-$TIMESTAMP.log" || status=1
        log_action "🧪 Test run complete: test-output-$TIMESTAMP.log"
    else
        echo "❌ pytest not found."
        status=1
    fi

    python tools/validate_sku_integrity.py | tee "$LOG_DIR/sku-validate-$TIMESTAMP.log" || status=1

    pip_outdated_check

    # File permission audit (world-writable files)
    find "$ROOT_DIR" -type f -perm -0002 -not -path "*/venv/*" > "$LOG_DIR/perm-audit-$TIMESTAMP.log"
    if [[ -s "$LOG_DIR/perm-audit-$TIMESTAMP.log" ]]; then
        echo "⚠️ World-writable files detected (see perm-audit-$TIMESTAMP.log)"
    fi

    if [[ $status -ne 0 ]]; then
        log_action "❌ QA suite failed"
        return 1
    fi
    log_action "✅ QA suite passed"
}

# ============================================================================
# SYSTEM HEALTH CHECK
# ============================================================================
system_health_check() {
    echo "🩺 Checking system health..."
    local report="$LOG_DIR/health-check-$TIMESTAMP.md"
    echo "Disk usage:" | tee "$report"
    df -h | tee -a "$report"
    echo -e "\nMemory usage:" | tee -a "$report"
    free -h | tee -a "$report"
    echo -e "\n.env check:" | tee -a "$report"
    [[ -f "$ROOT_DIR/.env" ]] && echo ".env present" | tee -a "$report" || echo ".env missing" | tee -a "$report"
    echo -e "\nRunning services:" | tee -a "$report"
    systemctl list-units --type=service --state=running | tee -a "$report"
    echo -e "\nPip outdated packages:" | tee -a "$report"
    pip_outdated_check | tee -a "$report"
    log_action "🩺 System health report saved: $(basename "$report")"
}

# ============================================================================
# Pip Outdated Checker
# ============================================================================
pip_outdated_check() {
    echo "📦 Checking for outdated Python packages..."
    pip list --outdated || true
}

# ============================================================================
# LAST 60 MIN LOG SNAPSHOT
# ============================================================================
export_logs_snapshot() {
    OUTPUT="$LOG_DIR/log-snapshot-$TIMESTAMP.md"
    echo "🧾 Exporting logs from the past 60 minutes..."
    find "$ROOT_DIR" -type f -name "*.log" -mmin -60 -exec tail -n 50 {} + > "$OUTPUT"
    echo "🕐 Snapshot saved to $OUTPUT"
    log_action "🧾 Log snapshot created: $OUTPUT"
}

# ============================================================================
# CODE STACKER
# ============================================================================
run_code_stacker() {
    echo "📚 Running code-stacker.sh..."
    if [[ -f "$STACKER_SCRIPT" ]]; then
        bash "$STACKER_SCRIPT"
        log_action "📚 Code stacker run complete"
    else
        echo "❌ code-stacker.sh not found!"
    fi
}

# ============================================================================
# BACKUP: Create
# ============================================================================
run_full_backup() {
    if ! run_tests; then
        echo "❌ QA checks failed. Backup aborted."
        log_action "❌ Backup aborted: QA failed"
        return 1
    fi
    mkdir -p "$BACKUP_DIR"
    local archive_name="dream-backup-$TIMESTAMP.tar"
    local archive_path="$BACKUP_DIR/$archive_name"
    local manifest="$BACKUP_DIR/manifest-$TIMESTAMP.txt"

    tmp_excludes=$(mktemp)
    tmp_includes=$(mktemp)
    for pattern in "${DEFAULT_EXCLUDES[@]}"; do echo "$pattern" >> "$tmp_excludes"; done
    [[ -f "$EXCLUDE_FILE" ]] && cat "$EXCLUDE_FILE" >> "$tmp_excludes"
    echo "." >> "$tmp_includes"
    grep -v '^#' "$INCLUDE_FILE" "$EXTRA_FILE" 2>/dev/null | sed '/^\s*$/d' >> "$tmp_includes"

    tar -cf "$archive_path" --exclude-from="$tmp_excludes" -T "$tmp_includes" -v > "$manifest"
    tar -rf "$archive_path" -C "$BACKUP_DIR" "$(basename "$manifest")"
    gzip "$archive_path"
    archive_path="$archive_path.gz"

    echo "✅ Local backup created: $archive_path"
    log_action "📦 Backup created: $(basename "$archive_path")"
    rm "$tmp_excludes" "$tmp_includes"
}

# ============================================================================
# BACKUP: Upload to GDrive
# ============================================================================
upload_to_gdrive() {
    local archive="$1"
    [[ ! -f "$archive" ]] && echo "❌ Archive not found: $archive" && return
    rclone copy "$archive" "$REMOTE_NAME:$RCLONE_FOLDER" && {
        echo "☁️ Uploaded to GDrive: $archive"
        log_action "☁️ GDrive upload complete: $archive"
    } || {
        echo "❌ Upload failed."
        log_action "❌ GDrive upload failed: $archive"
    }
}

# ============================================================================
# BACKUP: Restore
# ============================================================================
restore_from_backup() {
    local archive="$1"
    local mode="$2"
    [[ "$archive" == "latest" ]] && archive=$(ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz | head -n1)
    [[ ! -f "$archive" ]] && echo "❌ Archive not found." && return

    echo "🛠️ Restoring from $archive"
    if [[ "$mode" != "--auto" ]]; then
        read -p "Proceed with restore? This will overwrite files. (y/N): " confirm
        [[ "$confirm" != "y" && "$confirm" != "Y" ]] && echo "❌ Cancelled." && return
    fi

    tar -xzf "$archive" --exclude='master-artwork-paths.json' --exclude='.env'
    if [[ "$mode" != "--auto" ]]; then
        read -p "Restore master-artwork-paths.json? (y/N): " mconfirm
        [[ "$mconfirm" == "y" || "$mconfirm" == "Y" ]] && tar -xzf "$archive" master-artwork-paths.json
    else
        tar -xzf "$archive" master-artwork-paths.json || true
    fi

    if tar -tzf "$archive" .env >/dev/null 2>&1; then
        tar -xzf "$archive" .env
        echo ".env restored"
    else
        echo "⚠️ .env not in archive"
        echo "# placeholder" > .env.template
    fi

    python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && deactivate
    local report="$LOG_DIR/restore-check-$(date +%Y-%m-%d).md"
    if python tools/validate_sku_integrity.py | tee "$report"; then
        echo "SKU integrity check passed"
    else
        echo "⚠️ SKU integrity issues detected" | tee -a "$report"
    fi
    if command -v pytest >/dev/null 2>&1; then
        pytest >> "$report" 2>&1 || true
    fi
    local slug_count=$(find art-processing/processed-artwork -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    echo "Restored slugs: $slug_count" >> "$report"
    python - <<'PY' >> "$report" 2>&1
from dotenv import load_dotenv
load_dotenv();print("dotenv loaded")
PY
    if [[ -f ".env" ]]; then
        echo ".env OK ✅" | tee -a "$report"
    else
        echo "⚠️ .env missing" | tee -a "$report"
    fi
    log_action "🔁 Restore completed from $archive"
}

# ============================================================================
# BACKUP MENU
# ============================================================================
backup_menu() {
    while true; do
        echo -e "\n=== 📦 BACKUP MENU ==="
        echo "[1] Run Full Local Backup"
        echo "[2] List Backups"
        echo "[3] Restore From Backup"
        echo "[4] Backup + Upload to Google Drive"
        echo "[0] Back to Main Menu"
        read -p "Choice: " opt
        case "$opt" in
            1) run_full_backup ;;
            2) ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz 2>/dev/null || echo "No backups yet." ;;
            3) restore_from_backup ;;
            4) run_full_backup && latest=$(ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz | head -n1) && upload_to_gdrive "$latest" ;;
            0) break ;;
            *) echo "❌ Invalid." ;;
        esac
    done
}

# ============================================================================
# MAIN MENU
# ============================================================================
main_menu() {
    while true; do
        echo -e "\n🌟 Project Toolkit – DreamArtMachine"
        echo "[1] Git PULL / Sync from GitHub"
        echo "[2] Git PUSH / Commit & Push to GitHub"
        echo "[3] Run Full QA, QC, & Testing (via pytest + SKU checks)"
        echo "[4] System Health Check (disk, RAM, .env, pip outdated)"
        echo "[5] Backup Management"
        echo "[6] Export Log Snapshot (last 60 min)"
        echo "[7] Run Code Stacker Tool"
        echo "[0] Exit"
        read -p "Choose: " opt
        case "$opt" in
            1) git_pull_safe ;;
            2) git_push_safe ;;
            3) run_tests ;;
            4) system_health_check ;;
            5) backup_menu ;;
            6) export_logs_snapshot ;;
            7) run_code_stacker ;;
            0) echo "👋 Bye legend!"; exit 0 ;;
            *) echo "❌ Invalid option." ;;
        esac
    done
}

# ============================================================================
# CLI SHORTCUTS
# ============================================================================
case "$1" in
    --run-backup) run_full_backup ;;
    --upload-latest)
        latest=$(ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz | head -n1)
        upload_to_gdrive "$latest"
        ;;
    --list-backups) ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz ;;
    --restore-latest) restore_from_backup latest ;;
    --restore-latest-auto) restore_from_backup latest --auto ;;
    --code-stacker) run_code_stacker ;;
    --run-tests) run_tests ;;
    --validate-skus) python tools/validate_sku_integrity.py ;;
    --run-pip-check) pip_outdated_check ;;
    --repair-orphans)
        shift
        python tools/repair_orphan_skus.py "$@"
        ;;
    *) main_menu ;;
esac
