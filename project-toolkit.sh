#!/bin/bash
set -e

# Project Toolkit for Backup and Restore
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$ROOT_DIR/backups"
LOG_DIR="$ROOT_DIR/logs"
INCLUDE_FILE="$ROOT_DIR/backup_includes.txt"
EXTRA_FILE="$ROOT_DIR/files-to-backup.txt"
EXCLUDE_FILE="$ROOT_DIR/backup_excludes.txt"

DEFAULT_EXCLUDES=(".git" "*.pyc" "__pycache__" ".env" ".DS_Store" "venv" "backups")

log_action() {
    mkdir -p "$LOG_DIR"
    local log_file="$LOG_DIR/backup-restore-$(date +%Y%m%d).md"
    echo "[$(date)] $1" >> "$log_file"
}

read_list_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        grep -vE '^\s*#' "$file" | sed '/^\s*$/d'
    fi
}

run_full_backup() {
    mkdir -p "$BACKUP_DIR"
    local timestamp=$(date +%Y-%m-%d-%H-%M-%S)
    local archive="dream-backup-$timestamp.tar"
    local archive_path="$BACKUP_DIR/$archive"

    local tmp_excludes=$(mktemp)
    for pattern in "${DEFAULT_EXCLUDES[@]}"; do
        echo "$pattern" >> "$tmp_excludes"
    done
    if [[ -f "$EXCLUDE_FILE" ]]; then
        cat "$EXCLUDE_FILE" >> "$tmp_excludes"
    fi

    local tmp_includes=$(mktemp)
    echo "." >> "$tmp_includes"
    read_list_file "$INCLUDE_FILE" >> "$tmp_includes"
    read_list_file "$EXTRA_FILE" >> "$tmp_includes"

    local manifest="$BACKUP_DIR/manifest-$timestamp.txt"
    tar -cf "$archive_path" --exclude-from="$tmp_excludes" -T "$tmp_includes" -v > "$manifest"
    tar -rf "$archive_path" -C "$BACKUP_DIR" "$(basename "$manifest")"
    gzip "$archive_path"
    archive_path="$archive_path.gz"

    log_action "Backup created: $(basename "$archive_path")"
    echo "Backup archive created at $archive_path"
    echo "Manifest stored at $manifest"
    rm "$tmp_excludes" "$tmp_includes"
}

list_backups() {
    mkdir -p "$BACKUP_DIR"
    echo "Available backups in $BACKUP_DIR:"
    ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz 2>/dev/null || echo "No backups found."
}

restore_from_backup() {
    mkdir -p "$BACKUP_DIR"
    local archive="$1"
    local assume_yes="$2"
    if [[ -z "$archive" || "$archive" == "latest" ]]; then
        archive=$(ls -1t "$BACKUP_DIR"/dream-backup-*.tar.gz 2>/dev/null | head -n1)
    else
        archive="$BACKUP_DIR/$archive"
    fi
    if [[ ! -f "$archive" ]]; then
        echo "Backup archive not found."
        exit 1
    fi
    echo "Restoring from $archive"
    if [[ "$assume_yes" != "--yes" ]]; then
        read -p "This will overwrite existing files. Continue? (y/N) " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            echo "Restore cancelled."
            exit 1
        fi
    fi
    tar -xzf "$archive" --exclude='master-artwork-paths.json'
    if [[ "$assume_yes" == "--yes" ]]; then
        tar -xzf "$archive" master-artwork-paths.json 2>/dev/null || true
    else
        read -p "Restore master-artwork-paths.json? (y/N) " restore_map
        if [[ "$restore_map" == "y" || "$restore_map" == "Y" ]]; then
            tar -xzf "$archive" master-artwork-paths.json 2>/dev/null || true
        fi
    fi
    mkdir -p art-processing logs inputs
    python3 -m venv venv
    source venv/bin/activate && pip install -r requirements.txt >/dev/null 2>&1 && deactivate
    if [[ ! -f ".env" ]]; then
        echo "Warning: .env file is missing. Please create one."; log_action ".env missing after restore"
    else
        echo "Note: .env restored from backup."; log_action ".env restored from backup"
    fi
    log_action "Restore executed from $(basename "$archive")"
    echo "Restore complete."
}

backup_menu() {
    while true; do
        echo "[1] Run Full Project Backup"
        echo "[2] List All Backups"
        echo "[3] Restore From Backup"
        echo "[0] Back to Main Menu"
        read -p "Select an option: " choice
        case "$choice" in
            1) run_full_backup ;;
            2) list_backups ;;
            3) restore_from_backup ;;
            0) break ;;
            *) echo "Invalid option." ;;
        esac
    done
}

main_menu() {
    while true; do
        echo "Project Toolkit"
        echo "[5] Backup Management"
        echo "[0] Exit"
        read -p "Choose option: " choice
        case "$choice" in
            5) backup_menu ;;
            0) exit 0 ;;
            *) echo "Invalid option." ;;
        esac
    done
}

case "$1" in
    --run-backup)
        run_full_backup ;;
    --list-backups)
        list_backups ;;
    --restore-latest)
        restore_from_backup latest --yes ;;
    *)
        main_menu ;;
 esac
