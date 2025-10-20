# Repository Guidelines

## Project Structure & Module Organization
- `app.py` hosts the Flask application, routing, and startup sequence that hydrates data from Google Cloud Storage via `CompanyFolderLoader`.
- `models.py` defines the league, company, and personnel domain objects used across the views.
- `company_folder_loader.py` handles bucket discovery, Excel ingestion, and year filtering; keep GCS-specific logic isolated here.
- `templates/` contains Jinja templates for dashboards (`index.html`, `companies.html`, etc.), while `static/css/` stores shared styling.
- `Dockerfile` and `cloudbuild.yaml` provide container and Cloud Build entrypoints; update both when runtime dependencies change.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` sets up a local virtual environment.
- `pip install -r requirements.txt` installs Flask, pandas, and other runtime dependencies.
- `FLASK_APP=app.py flask run --debug` starts the development server on port 5000.
- `docker build -t execap .` followed by `docker run -p 8080:8080 execap` mirrors the production image locally.

## Coding Style & Naming Conventions
- Follow PEP 8: 4-space indentation, snake_case for functions and variables, PascalCase for classes, and ALL_CAPS for configuration constants.
- Keep Flask blueprints, loaders, and model helpers composable; prefer small functions over monolithic views.
- In templates, favor readable block names (e.g., `{% block content %}`) and hyphenated class names tied to `static/css/style.css`.

## Testing Guidelines
- Add automated tests under `tests/` using `pytest`; name files `test_<module>.py` and target business logic in `models.py` and `company_folder_loader.py`.
- Use fixtures or temporary directories to stub bucket data instead of hitting real GCS.
- Run `pytest` (optionally `pytest -k loader`) before opening a pull request and document any gaps in coverage.

## Commit & Pull Request Guidelines
- Match the existing log: concise, imperative summaries (`add loader retry logic`, `fix template year filter`) and group related changes per commit.
- Pull requests should include: a short narrative of changes, environment/setup notes, commands executed (e.g., `pytest`, `flask run`), and screenshots for UI updates.
- Link relevant issues or tickets and call out configuration changes, especially anything impacting `BUCKET_NAME` or credentials.

## Configuration & Security Tips
- Keep bucket names, credential paths, and secrets in environment variables or deployment configs; never hard-code keys or upload Excel fixtures with real data.
- Document required environment variables in PRs and share sample `.env.example` updates when new settings appear.
