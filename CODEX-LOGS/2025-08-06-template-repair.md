# 2025-08-06 Template Repair Log

## Changes
- Consolidated menu and theme scripts into `static/js/main.js`; removed experimental scripts.
- Added routes for upload, artworks, finalised pages; created admin blueprint with stub pages.
- Replaced legacy templates with minimal versions and fixed navigation links.
- Updated `app.py` to render `login.html`, added error handlers, and registered admin blueprint.
- Created new `finalised.html` template and adjusted image paths in `review_artwork.html`.

## Testing
- `black app.py routes/home_routes.py routes/admin_routes.py`
- `pytest`

