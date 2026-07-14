# Public release audit

## Data boundary

Public code may contain source metadata, example configuration, and documented API adapters. User resumes, preferences, company priorities, application history, scan output, credentials, and tokens live under gitignored `user-data/` or environment variables.

## Source policy

Built-in adapters require a documented API, government open-data endpoint, or authorized feed. Undocumented endpoints and services whose terms prohibit automated collection are excluded even if a third-party GitHub scraper exists.

## Verification evidence — 2026-07-15

- `.venv/Scripts/python.exe -m pytest -q`: `25 passed`.
- `.venv/Scripts/python.exe -m compileall -q job_radar`: passed.
- Editable packaging install passed after explicitly limiting setuptools discovery to `job_radar*`; `job-radar --help` and `doctor --json` also passed from outside the repository.
- Live official-source run: `1,841` normalized jobs scanned, `4` published with the example profile, and both gitignored JSON and Dashboard outputs generated.
- Real AI subprocess protocol smoke passed: stdin request, stdout response, identity/range validation, and shell-free execution.
- Runtime privacy and secret regex scan across `job_radar/`, `dashboard/`, `examples/`, `config.example/`, and `catalog/`: no private URL, email, secret header, credential pattern, application log, or target-company file marker found.
- Restricted-source runtime scan: no LinkedIn, Indeed, Google Jobs, or 104 implementation reference found.
- License audit: MIT `LICENSE` present; source and independence boundary documented in `SOURCE_POLICY.md`.
- `gitleaks` remains unavailable on this host. `.github/workflows/gitleaks.yml` uses the current official `gitleaks-action@v3` for push and pull requests; it cannot run until the repository has a GitHub commit/remote.
- Browser desktop flow passed against the live generated dashboard: list, swipe review, interested state, reload persistence, saved matches, and search. Browser testing found and fixed the missing `[hidden]` CSS contract.
- Browser responsive check passed after correcting the mobile command-bar gutter: at the available 500px override, `scrollWidth` and `clientWidth` were both `500`.

## Data behavior

- Retention: status remains in browser local storage until the user clears site data or replaces it.
- Sharing: the generated page sends no applicant or status data to a third party.
- Export: status leaves the browser only when the user presses `Export status`; exported files are user-controlled.
- Deletion: clearing browser site data deletes local status. Exported copies must be deleted separately by the user.
- AI providers: the built-in command protocol sends structured preferences and public job fields, not `resume_path`, resume contents, prior notes, or application state. Any downstream provider retention, training, sharing, disclosure, and deletion remain the developer's responsibility.

## Remaining publication boundary

- The repository has no root commit or GitHub remote yet.
- CI gitleaks execution remains unverified until a commit is pushed to the future GitHub repository.
- Official API availability and terms can change and must be rechecked before expanding request volume.
