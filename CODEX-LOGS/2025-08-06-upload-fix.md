# 2025-08-06 Upload Fix Log

## Summary
- Implemented new `artwork_routes` blueprint with robust `/upload` handler.
- Updated templates and JS for drag-and-drop uploads with flash messaging.
- Saved uploads to `art-processing/unanalysed-artwork` with validation and unique filenames.
- Adjusted navigation links to new route and added flash message rendering.
- Registered blueprint in app factory.

## Files Modified
- `app.py`
- `routes/__init__.py`
- `routes/artwork_routes.py`
- `routes/home_routes.py`
- `templates/index.html`
- `templates/main.html`
- `templates/home.html`
- `templates/partials/footer.html`
- `templates/upload.html`
- `static/js/upload.js`

## Testing
- `black app.py routes`
- `pytest`

