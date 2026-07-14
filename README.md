# Job Radar Starter

A local-first, single-developer job review dashboard built for people who want AI assistance without putting their resume, preferences, application history, or credentials in a public repository.

The public edition preserves the useful part of the original workflow: dense ranked cards, recommendations, filters, swipe review, saved matches, and explicit decisions. It deliberately does not ship anyone's private profile, scoring weights, company priorities, scan history, hosted dashboard URL, or credentials.

## What is included

- Official Greenhouse, Lever, and Ashby job-board adapters.
- A public country, source, and company-board catalog.
- A gitignored local profile for resume path, skills, countries, tracks, companies, and matching boundaries.
- A complete CLI for readiness checks, official-source scans, local scoring, optional AI-command scoring, dashboard builds, and safe schedule rendering.
- A normalized jobs JSON format that an AI agent or local script can consume and produce.
- A generated, framework-free dashboard with:
  - list, swipe-review, and saved-match views
  - highest-scored unhandled recommendations
  - country, track, role, skill, freshness, source, and status filters
  - interested, applied, hidden, and expired states
  - pointer gestures and keyboard review controls
  - local status persistence and user-controlled JSON export

## What is intentionally not included

- A real resume, application log, target-company list, or scan output.
- API keys, hosted URLs, Cloudflare bindings, or a shared tracking backend.
- Automated access to LinkedIn, Indeed, Google Jobs, or 104.
- A proprietary scoring prompt or a claim that the example scores are universal.

## Quick start

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item config.example\profile.yaml user-data\profile.yaml
job-radar --json doctor
job-radar --json run
python -m http.server 8000 --directory dashboard\public
```

Open <http://localhost:8000>.

The live `run` command fetches the enabled public ATS boards in `catalog/sources.yaml`, applies generic local rules, writes `scans/latest.json`, and rebuilds the dashboard. The real `user-data/`, `scans/`, `.env`, and `*.local.yaml` paths are ignored by Git.

To preview the UI without a live scan:

```powershell
job-radar build-dashboard --jobs examples\jobs.example.json --output dashboard\public\index.html
```

## CLI

Put global `--json` before the command. JSON output includes stable readiness fields, counts, and absolute output paths.

```powershell
job-radar --json doctor
job-radar --json catalog list
job-radar --json scan --output scans\latest.json
job-radar --json score --jobs scans\latest.json --output scans\scored.json
job-radar --json run
job-radar build-dashboard --jobs scans\latest.json --output dashboard\public\index.html
```

`scan` fails instead of silently publishing a partial result when an official source fails. This makes a broken scheduled run visible.

## Configure your own profile

Edit `user-data/profile.yaml` locally:

```yaml
profile:
  resume_path: user-data/resume.md
  skills: [Go, Python, PostgreSQL]

preferences:
  countries: [CA, REMOTE]
  roles: [backend, platform]
  tracks: [ai-product, backend]
  visa_required: true

companies:
  preferred: [A company you want]
  excluded: [A company you do not want]

matching:
  minimum_score: 65
  must_have: [backend]
  exclude_keywords: [unpaid, commission-only]
```

This file tells the local scorer or AI controller what matters. The built-in scanner, scorer, and dashboard do not open or upload `profile.resume_path`; the field is only a local pointer for a developer-owned extension.

## Normalized job contract

Each object in the jobs JSON may contain:

```json
{
  "source": "greenhouse",
  "external_id": "public-board-id",
  "company": "Northstar Robotics",
  "title": "Senior Backend Engineer",
  "location": "Toronto, Canada",
  "url": "https://example.com/jobs/backend",
  "published_at": "2026-07-14T00:00:00Z",
  "first_seen": "2026-07-14",
  "score": 91,
  "country": "CA",
  "category": "backend",
  "tracks": ["backend"],
  "skills": ["Go", "Kubernetes"],
  "visa_supported": true,
  "summary": "Why this role matches the local profile.",
  "risk": "What to verify before applying.",
  "salary": "CAD 148k–176k"
}
```

If an AI agent creates `summary` or `risk`, instruct it not to copy resume contact details or sensitive interview notes into the output: generated dashboard HTML contains those fields.

## AI-command scoring

Local rules are the default. To delegate scoring, provide an executable that accepts one JSON object on stdin and returns one JSON object on stdout. The executable is launched directly without a shell, and `--ai-command` must be the final Job Radar option:

```powershell
job-radar --json score --jobs scans\latest.json --output scans\scored.json --ai-command python user-data\my_scorer.py
job-radar --json run --ai-command python user-data\my_scorer.py
```

The request contains `contract_version`, structured skills/preferences/company boundaries, matching boundaries, and public job fields. It excludes the resume path, resume contents, prior summaries, risks, and application state. The response contract is:

```json
{
  "scores": [
    {
      "source": "greenhouse",
      "external_id": "public-board-id",
      "score": 91,
      "summary": "Why this role may fit.",
      "risk": "What to verify.",
      "tracks": ["backend"],
      "skills": ["Go"],
      "visa_supported": null
    }
  ]
}
```

Unknown jobs, duplicate identities, unsupported fields, invalid types, and scores outside `0..100` are rejected. Local company and keyword exclusions remain hard exclusions even when an external scorer disagrees.

If that executable calls a hosted model, the provider receives whatever the executable forwards. Review its retention, training, disclosure, and deletion settings; Job Radar cannot control a third party after data leaves the process.

## Daily schedule

Generate scheduler configuration for review:

```powershell
job-radar schedule render --platform windows --daily-at 08:15 --output user-data\job-radar-task.ps1
```

```bash
job-radar schedule render --platform cron --daily-at 08:15 --output user-data/job-radar.cron
```

Times use the host's local timezone. `schedule render` never installs or enables the result; the developer must review and install it separately.

## AI-controlled workflow

```text
local profile + public job boards
              ↓
official scanner + local rules or approved AI command
              ↓
normalized jobs JSON
              ↓
job-radar build-dashboard
              ↓
local dashboard + local status state
```

Keep the AI controller local by default. The repository also ships `.codex/skills/job-radar/` so an AI coding agent follows the same doctor-first, local-data, source-policy, and no-auto-install boundaries.

## Source and legal boundary

Built-in source metadata is documented in [`catalog/sources.yaml`](catalog/sources.yaml). The policy is in [`SOURCE_POLICY.md`](SOURCE_POLICY.md).

- Verify the current source terms before increasing request volume.
- Respect rate limits and do not bypass authentication or access controls.
- Job availability, visa support, compensation, and AI matching explanations must be verified on the official posting.
- This project is independent and is not affiliated with any job board, ATS provider, employer, or government agency.
- Publishing this repository or finding a third-party scraper on GitHub does not grant permission to automate another service. Adapter authors and operators remain responsible for authorization, request volume, applicable terms, privacy disclosures, and local law. This documentation is not legal advice.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The generated dashboard has no frontend dependency or telemetry. Non-HTTP(S) source URLs are removed before they reach either the card markup or embedded job data. Pushes and pull requests run `.github/workflows/gitleaks.yml`; local regex checks are supplementary, not a replacement for CI secret scanning. The workflow needs no Gitleaks license in a personal-account repository; an organization-owned repository must configure the license required by Gitleaks Action.

## License

MIT. See [`LICENSE`](LICENSE).
