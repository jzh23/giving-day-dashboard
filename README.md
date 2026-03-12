# Giving Day Dashboard (GitHub Pages + Actions)

Cheap architecture:
- Frontend: static files in `docs/` served by GitHub Pages.
- Data collection: GitHub Action runs every 5 minutes and commits JSON updates.
- Storage: git history + `docs/data/history.json` for chart data.

## 1. Configure campaigns
Edit `campaigns.json`:
- `name`: display name
- `url`: campaign page URL

The scraper derives the team `id` from the URL slug after `/campaigns/`.
Example: `https://givingday.cornell.edu/campaigns/cornell-fsae` -> `cornell-fsae`.

## 2. Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/scrape.py
```
Then open `docs/index.html` from a static server (example):
```bash
python3 -m http.server 8000 --directory docs
```

## 3. Publish on GitHub Pages
1. Push this folder as its own GitHub repository.
2. In GitHub repo settings, enable Pages:
   - Build and deployment: `Deploy from a branch`
   - Branch: `main`, folder: `/docs`
3. Enable Actions in the repository.
4. The workflow `.github/workflows/update-data.yml` will update every 5 minutes.

## Notes
- GitHub Actions cron can be delayed during platform load.
- If the campaign HTML changes, update `selectors` in `campaigns.json`.
