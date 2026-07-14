# job-radar-starter agent notes

## Purpose

This repository is the public, single-developer edition of Job Radar. It must remain usable without its maintainer's resume, preferences, application history, credentials, private scan output, or private deployment.

## Commands

- Tests: `.venv/Scripts/python.exe -m pytest -q`
- Build example dashboard: `.venv/Scripts/job-radar.exe build-dashboard --jobs examples/jobs.example.json --output dashboard/public/index.html`

## Boundaries

- Keep the Python package dependency-light and the generated dashboard framework-free.
- Built-in sources must use documented public APIs or authorized feeds.
- User configuration and scan output belong in gitignored `user-data/` and `scans/` paths.
- The public dashboard stores status locally by default. Do not embed credentials or private service URLs.
- Preserve the dependency direction `dashboard/CLI -> application -> models/adapters`; source adapters do not call the dashboard.
