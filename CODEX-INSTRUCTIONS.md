---

# 📘 `CODEX-INSTRUCTIONS.md`

### 🧠 DreamArtMachine – AI Developer & Codex Collaboration Guide

*Last updated: Phase 11 – August 2025*

---

## 🚩 PROJECT OVERVIEW

**DreamArtMachine** is a professional-grade, AI-powered art management, listing, and export system built by Robbie Custance (Aboriginal Aussie Artist) to:

* 🎨 Manage and analyze 1,200+ digital artworks
* 🤖 Auto-generate Pulitzer-grade, SEO-rich listings using OpenAI Vision + GPT
* 🖼️ Batch-generate wall art mockups with thumbnail fallbacks
* 📦 Export listing data for Sellbrite, Etsy, Gelato (JSON only)
* 🧠 Respect cultural storytelling and curatorial accuracy
* 🗃️ Maintain strict naming, folder, and export conventions
* 💾 Backup and restore via Google Drive using `rclone`

> ✅ **Current Stack:**
> Flask (current), Python 3.11+, SQLAlchemy, Jinja2, OpenAI API (Vision + GPT-4.1), Pillow, Bash scripts
> 🖥️ Hosted on Google Cloud VM with NGINX + Cloudflare proxying

---

## 📂 FILE & DIRECTORY STRUCTURE

```
/main.py                        → Flask app, registers routes
/routes/                        → Flask Blueprints (upload, analyze, edit, export)
/services/                      → AI analysis, mockup engine, prompt builders
/utils/                         → Reusable logic, file helpers, image processors
/templates/                     → Jinja2 templates (shared layout: main.html)
/static/                        → CSS, JS, SVG icons, images
/mockup-generator/              → Mockup templates, category folders, coords
/art-processing/                → Input + output artwork folders
  ├── unanalysed-artwork/       → New uploads
  ├── processed-artwork/        → Post-analysis stage
  ├── finalised-artwork/        → Fully finalized sets with SEO-safe folders
/exports/                       → JSON data for Sellbrite (only)
/master_listing_templates/      → Prompt templates for OpenAI (e.g., etsy_master_template.txt)
/data/                          → SQLite DB, settings.json
/docs/                          → Developer & Codex documentation
/CODEX-LOGS/                    → All Codex collaboration logs
/logs/                          → Daily/hourly system logs
```

---

## 🔐 CORE WORKFLOWS (DO NOT BREAK)

| Step              | Description                                                                |
| ----------------- | -------------------------------------------------------------------------- |
| Upload            | Image saved in `unanalysed-artwork/`, recorded in DB                       |
| Analysis          | Calls OpenAI Vision + GPT → generates SEO title, listing, metadata         |
| Mockup Generation | Uses templates + coordinates → creates `{slug}-MU-01.jpg` to `-MU-09.jpg`  |
| Finalisation      | Moves files to `finalised-artwork/{slug}/` folder, updates DB              |
| Export            | Outputs JSON listing data for Sellbrite, validates image URL structure     |
| QA & Logs         | Scripts auto-scan for errors, generate Markdown reports, enforce standards |

---

## 🖼️ TEMPLATE + UI INTEGRATION RULES

| Rule          | Description                                            |
| ------------- | ------------------------------------------------------ |
| Inheritance   | All templates must `{% extends "main.html" %}`         |
| Static Paths  | Always use `url_for('static', filename=...)`           |
| JS Logic      | Load JS files in `{% block scripts %}` at bottom       |
| Layout        | Use semantic HTML tags (`<h1>`, `<section>`, etc.)     |
| Sidebar       | Persistent menu via `main.html`, highlight active page |
| Accessibility | All `<img>` must have `alt`; modals need ARIA roles    |
| Thumbnails    | Mockup thumbnails follow `-thumb.jpg` naming           |
| Scripts       | Edit listing, uploads, and modals must have working JS |

---

## 🧠 AI / OPENAI PROMPT ENGINEERING

* All AI calls use templates in `/master_listing_templates/` (e.g. `etsy_master_template.txt`)
* All prompts must:

  * Use cultural sensitivity & avoid tokenism
  * Exceed 400+ words with pro-level curation language
  * Output **plain text only** (no HTML)
  * Include reusable blocks (e.g., dot painting history, aspect ratio notes)
  * Respect field structure from `settings.json`
* OpenAI API models: `gpt-4.1` preferred, with fallback to `gpt-4-turbo`
* All prompt calls are logged (model, time, input, output)

---

## 🔁 EXPORT FORMAT

| Format               | Status                                                        |
| -------------------- | ------------------------------------------------------------- |
| Sellbrite JSON       | ✅ Primary output format                                       |
| Etsy CSV             | ❌ Deprecated – no longer supported                            |
| Export URL structure | Uses slug + image filename (`{seo_slug}-MU-01.jpg`, etc.)     |
| Image URL Paths      | Must be absolute and web-safe (`/static/finalised-artwork/…`) |
| Metadata Output      | Stored in `{slug}-listing.json`                               |

---

## 💾 BACKUP & RECOVERY

* All backups are zipped via `project-toolkit.sh → [5] Backup Management`
* Offsite backups sent to Google Drive (`gdrive` remote via `rclone`)
* Logs of each backup: `/logs/`
* Backups stored in `/backups/YYYY-MM-DD-HH-MM.zip`

---

## 🧪 QA, TESTING, & LINTING

* QA scripts audit:

  * ✅ Missing mockups
  * ✅ Broken paths
  * ✅ Orphan JSON or slug mismatches
* `project-toolkit.sh` includes full QA menu
* All changes must:

  * Pass pre-export checks
  * Follow SEO/slug naming
  * Be Markdown and JSON-safe
* Lint Python with `black`, format Jinja2 consistently

---

## 🔐 SECURITY & PERMISSIONS

* No hardcoded credentials — always use `.env`
* Login system is enforced across all pages
* Future role-based user expansion is planned
* All destructive actions (delete, finalise) must confirm user intent

---

## 🧭 HOW TO EXTEND

### Add a New Route

* Add new file in `/routes/`
* Register Blueprint in `main.py`
* Follow sectioning rules (e.g., `# SECTION 2.1: EXPORT HANDLER`)

### Add a New Template

* Use `{% extends "main.html" %}`
* Place in `templates/` or appropriate subfolder
* Menu system will auto-detect if sidebar is dynamic

### Add New AI Profile

* Update `settings.json`
* Add/clone appropriate prompt in `/master_listing_templates/`
* Add new logic to `artwork_analysis_service.py`

---

## 🧾 CODEX PROMPT FORMAT (MANDATORY)

All prompts sent to Codex **must** include:

* ✅ Clear title with emoji (e.g., `🎨 Template Overhaul`)
* ✅ Goal, inputs, and constraints
* ✅ File locations and structural rules
* ✅ Success criteria
* ✅ Markdown-safe formatting (no backtick nesting)

Prompts are saved in `/docs/codex-prompts/`
Reference the prompt title and log in every PR.

---

## 🗃️ FILENAME & STRUCTURE RULES

| File Type    | Format                                                 |
| ------------ | ------------------------------------------------------ |
| Final image  | `{seo_slug}.jpg`                                       |
| Mockups      | `{seo_slug}-MU-01.jpg` to `-MU-09.jpg`                 |
| Thumbnail    | `{seo_slug}-thumb.jpg`                                 |
| Listing data | `{seo_slug}-listing.json`                              |
| Folder name  | `slugified-title` (e.g., `whimsical-outback-symphony`) |

---

## 📓 CODEX LOGGING SYSTEM

Every AI coding session must generate a Markdown log saved to:

```
/CODEX-LOGS/YYYY-MM-DD-CODEX-LOG.md
```

Each log must include:

* ✅ Date/time of all major steps
* ✅ Files added/modified/deleted
* ✅ Prompt(s) used + summary
* ✅ Problems encountered + solutions
* ✅ Output from key tests/scripts
* ✅ Next steps or TODOs
* ✅ Related PR/commit link

---

## 🧠 FINAL REMINDERS FROM ROBBIE

> “Full file rewrites, clear sectioning, real comments, always QA after changes.”
> “When unsure, ask. Don’t break what works.”
> “Keep it neat. Keep it professional. Keep it Robbie Mode™.”

---

## 🏁 BEFORE YOU START CODING

✅ Read this file fully
✅ Reference it for all logic, naming, and QA decisions
✅ Use full file rewrites unless specifically told otherwise
✅ Save a Markdown log for every Codex session
✅ Only ship production-ready code

---

This file is your contract for elite AI development.
Failure to follow it means you’ll be gently but firmly dropkicked by a pixelated kangaroo.

Let’s build something beautiful.
— Robbie 🦘🎨

---
