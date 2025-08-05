#!/bin/bash

# =============================
# DreamArtMachine/ArtNarrator
# code-stacker.sh
# ./code-stacker.sh
# Gathers and combines code from project, EXCLUDING 'file-storage/' and any files inside it.
# =============================

now=$(date "+%a-%d-%B-%Y-%I-%M-%p" | tr '[:lower:]' '[:upper:]')

# --- Folders and files to process
root_folders="descriptions routes scripts settings static/css static/js templates tests utils"
root_files="CHANGELOG.md CODEX-README.md README.md app.py artnarrator-report.sh config.py cron-backup.sh generate_folder_tree.py git-update-pull.sh git-update-push.sh package-lock.json requirements.txt"

# --- List of files now ONLY in file-storage (not in project root)
excluded_files="artnarrator.py codex-merge.sh mockup_categoriser.py run_codex_patch.py smart_sign_artwork.py smart_sign_test01.py sort_and_prepare_midjourney_images.py"

# --- Full code stack (main project code)
out1="code-stacks/full-code-stack/code-stack-${now}.md"
mkdir -p "$(dirname "$out1")"
echo "# FULL CODE STACK ($now)" > "$out1"

for f in app.py config.py requirements.txt; do
  # Only include if not in file-storage (exclusion)
  if [[ ! " $excluded_files " =~ " $f " ]] && [[ -f $f ]]; then
    echo -e "\n\n---\n## $f\n---" >> "$out1"
    cat "$f" >> "$out1"
  fi
done

for d in $root_folders; do
  [[ -d $d ]] && find "$d" -maxdepth 1 -type f \
    \( -name '*.py' -o -name '*.js' -o -name '*.css' -o -name '*.md' -o -name '*.txt' -o -name '*.html' \) \
    ! -path "file-storage/*" | sort | while read file; do
      # Exclude files if they are now in file-storage
      filename=$(basename "$file")
      if [[ ! " $excluded_files " =~ " $filename " ]]; then
        echo -e "\n\n---\n## $file\n---" >> "$out1"
        cat "$file" >> "$out1"
      fi
    done
done

# --- Root files code stack (just loose files)
out2="code-stacks/root-files-code-stack/root-files-code-stack-${now}.md"
mkdir -p "$(dirname "$out2")"
echo "# ROOT FILES CODE STACK ($now)" > "$out2"
for f in $root_files; do
  # Only include if not in file-storage
  if [[ ! " $excluded_files " =~ " $f " ]] && [[ -f $f ]]; then
    echo -e "\n\n---\n## $f\n---" >> "$out2"
    cat "$f" >> "$out2"
  fi
done

echo "✅ Code stacks generated at:"
echo "   $out1"
echo "   $out2"
