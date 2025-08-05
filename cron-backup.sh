#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
./project-toolkit.sh --run-backup >> logs/backup-cron-$(date +%Y%m%d).log 2>&1
