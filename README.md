# ExecuCap 🏈💼

ExecuCap reimagines executive compensation tracking as a salary-cap style sports experience. The Flask UI surfaces cap space, blockbuster contracts, position leaders, and free-agent executives for the Fortune 10—ideal for quick scouting or deeper analytics.

## Getting Started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app defaults to the bundled `fortune10_exec_data.py` dataset, so you can explore the dashboard without any external services. When you migrate to Firebase or GCS, set `DATA_SOURCE=gcs` and provide bucket credentials.

## Key Features

- **League Overview**: NFL-inspired landing screen highlights league-wide budget totals, cap-space leaderboard, marquee contracts, and teams flirting with the luxury tax.
- **Team Cap Tables**: Company pages now break out C-Suite tables, board rosters, and a board compensation snapshot with policy notes.
- **Position Salary Leaders**: Aggregated view of highest-paid chairpersons, CEOs, CFOs, VPs, and more based on the current season.
- **Free Agents**: Filterable list of inactive executives with last-known deals and experience summaries.

## Data Model & Sources

- Core entities (`Company`, `Person`) live in `models.py` alongside normalized fact tables (`ExecutiveCompensation`, `ExecutiveEquityGrant`, `BeneficialOwnershipRecord`, `DirectorCompensation`, `DirectorProfile`, `DirectorCompPolicy`, and `SourceManifestEntry`). Everything is wired through a refreshed `LeagueManager` that keeps derived indexes for UI queries.
- `fortune10_exec_data.py` captures Fortune 10 compensation totals. `fortune10_loader.py` converts those records into the normalized models while layering in market-cap snapshots and cap-budget estimates.
- `DATA_SOURCE=fortune10` (default) loads the in-repo dataset. Set `DATA_SOURCE=gcs` to read CSVs from `gs://<bucket>/companies/<slug>/<year>/` (e.g., `walmart_2024_executive_compensation.csv`, `..._director_compensation.csv`, etc.).

## Deployment Tips

- The production Docker image relies on `PYTHONPATH=/app`; keep custom modules (e.g., loaders) in the repo root or ensure the path is set.
- Gunicorn command lives in `Dockerfile` (`CMD exec gunicorn ... app:app`). Cloud Run automatically injects `PORT`.
- For Cloud Run: add environment vars like `DATA_SOURCE`, `BUCKET_NAME`, and credentials via the console or `gcloud run deploy --set-env-vars`.

## Contributing

- Document new datasets or share-count overrides inside `fortune10_loader.py` to keep the live league consistent.
- Run `python -m compileall` after structural changes to catch syntax issues before deploying.
- PRs should highlight UI changes with screenshots and list the data source tested (`fortune10` vs `gcs`).

Enjoy calling plays for the corporate front office! !*** End Patch*** End Patch
