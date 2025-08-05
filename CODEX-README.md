# Backup and Restore Guidelines

This document defines the standards for backup creation and restoration integrity within this project.

## Backup

- Use `project-toolkit.sh` or `cron-backup.sh` to generate backups.
- Archives are stored in `backups/` as `dream-backup-YYYY-MM-DD-HH-MM-SS.tar.gz`.
- A `manifest-*.txt` file listing every archived path is produced and included with each backup.
- Default exclusions: `.env`, `.git`, `venv`, `__pycache__`, `.DS_Store`, and anything listed in `backup_excludes.txt`.

## Restore

- Restoration recreates the project structure and virtual environment.
- `python3 -m venv venv` is run and dependencies are installed from `requirements.txt`.
- Missing `.env` files are noted; restored ones trigger a warning.
- Optionally restore `master-artwork-paths.json` when requested.

## Logging

- Every backup or restore appends a timestamped entry to `logs/backup-restore-*.md` describing the action.
