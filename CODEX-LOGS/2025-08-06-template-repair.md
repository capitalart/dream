# Template Repair Log - 2025-08-06

## Templates & Files Updated
- Added script block to `templates/main.html` for per-page JS.
- Imported missing `404.css` into `static/css/main.css`.
- Created `routes/exports_routes.py` and `templates/exports/sellbrite.html`.
- Reworked `routes/finalise_routes.py` to separate `/edit-listing/<slug>` and `/review/<slug>`.
- Registered new blueprints in `app.py` and cleaned nested registrations in `routes/__init__.py`.
- Updated navigation links in `templates/home.html` and `templates/index.html`.
- Attached page-specific scripts in `templates/artworks.html`, `templates/edit_listing.html`, and `templates/review_artwork.html`.
- Simplified `templates/404.html` messaging.

## Errors Resolved
- Fixed Jinja block mismatch causing 500 on `/upload`.
- Corrected blueprint endpoint names that triggered `BuildError` on review pages.
- Restored missing route `/exports/sellbrite`.

## Testing
- `pytest` → all 11 tests passed.

## TODO
- Implement full Sellbrite export logic.
- Flesh out listing editing interface.
