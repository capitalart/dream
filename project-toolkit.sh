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
    git add .
    git commit -m "🔄 Auto commit via toolkit on $TIMESTAMP" || echo "ℹ️ Nothing to commit."
    git push && log_action "✅ Git push successful"
}

# ============================================================================
# QA / QC / TESTING
# ============================================================================
run_tests() {
    echo "🧪 Running test suite..."
    if command -v pytest >/dev/null 2>&1; then
        pytest --maxfail=3 --disable-warnings | tee "$LOG_DIR/test-output-$TIMESTAMP.log"
        log_action "🧪 Test run complete: test-output-$TIMESTAMP.log"
    else
        echo "❌ pytest not found. Skipping tests."
    fi
}

# ============================================================================
# SYSTEM HEALTH CHECK
# ============================================================================
system_health_check() {
    echo "🩺 Checking system health..."
    echo "Disk usage:" && df -h | tee -a "$LOG_DIR/health-check-$TIMESTAMP.md"
    echo -e "\nMemory usage:" && free -h | tee -a "$LOG_DIR/health-check-$TIMESTAMP.md"
    echo -e "\nRunning services:" && systemctl list-units --type=service --state=running | tee -a "$LOG_DIR/health-check-$TIMESTAMP.md"
    log_action "🩺 System health report saved: health-check-$TIMESTAMP.md"
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
    [[ "$archive" == "latest" ]] && archive=$(ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz | head -n1)
    [[ ! -f "$archive" ]] && echo "❌ Archive not found." && return

    echo "🛠️ Restoring from $archive"
    read -p "Proceed with restore? This will overwrite files. (y/N): " confirm
    [[ "$confirm" != "y" && "$confirm" != "Y" ]] && echo "❌ Cancelled." && return

    tar -xzf "$archive" --exclude='master-artwork-paths.json'
    read -p "Restore master-artwork-paths.json? (y/N): " mconfirm
    [[ "$mconfirm" == "y" || "$mconfirm" == "Y" ]] && tar -xzf "$archive" master-artwork-paths.json

    python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && deactivate
    [[ -f ".env" ]] && echo ".env OK ✅" || echo "⚠️ .env missing"
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
        echo "[3] Run Full QA, QC, & Testing (via pytest)"
        echo "[4] System Health Check"
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
    --code-stacker) run_code_stacker ;;
    --run-tests) run_tests ;;
    *) main_menu ;;
esac
