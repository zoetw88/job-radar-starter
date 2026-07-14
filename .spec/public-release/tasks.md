# Public release tasks

## Acceptance criteria

- [x] User preferences load only from a local YAML file.
- [x] No maintainer resume, preferences, applications, credentials, scans, or historical Git objects exist.
- [x] Built-in sources use documented APIs, government open data, or authorized feeds.
- [x] Restricted scraping sources are neither bundled nor recommended.
- [x] Country, company, and job-site catalogs are public data separated from user preferences.
- [x] Dashboard builds from developer-owned local JSON and stores tracking state locally.
- [x] Automated tests, secret scan, license audit, and privacy grep pass.
- [ ] GitHub publication requires a clean repository with a new root commit.

## Dashboard parity

- [x] Preserve the original dashboard's dense job cards, score, fit explanation, risk, salary, source, and official-link hierarchy.
- [x] Provide list, swipe-review, and saved-match views without copying private job data.
- [x] Provide recommendations from the highest-scored unhandled jobs.
- [x] Filter by country, track, role category, skill, freshness, source, and tracking status.
- [x] Support interested, applied, hidden, and expired states with keyboard and pointer review controls.
- [x] Store tracking state locally by default and support a user-controlled JSON export.
- [x] Do not include the maintainer's profile, scoring weights, company lists, URLs, credentials, Cloudflare bindings, or application records.
- [x] Preserve accessible focus, reduced-motion, empty-state, and invalid-link behavior.

## Scheduled pipeline and CLI

- [x] `doctor --json` reports catalog, profile, local-output, network-auth, and AI-command readiness without exposing secrets.
- [x] `catalog list --json` exposes the configured public countries, sources, and company boards.
- [x] `scan` fetches enabled official sources and writes normalized jobs JSON.
- [x] `score` applies deterministic local rules and optionally delegates to a shell-free AI command JSON protocol.
- [x] `run` composes scan, score, jobs output, and dashboard generation in one command.
- [x] AI delegation sends structured preferences and public job data but does not read resume contents automatically.
- [x] AI responses validate job identity, score range, and allowed fields before changing output.
- [x] `schedule render` produces Windows Task Scheduler or cron configuration without installing it.
- [x] Human and `--json` output report stable paths, counts, and machine-readable errors.
- [x] GitHub push and pull requests run `gitleaks` in CI; local regex scanning remains supplementary only.

## Blockers

- Unauthenticated scraping of 104, LinkedIn, Indeed, and Google Jobs is not authorized as a built-in source. Manual URL/JSON import, search-based link discovery, official connectors/APIs, and explicitly authorized feeds remain valid extension paths.
