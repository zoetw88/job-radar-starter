# AI development map

| Area | Input | Output | Privacy boundary |
|---|---|---|---|
| Configuration | `user-data/profile.yaml` | Structured preferences | Local only |
| Source catalog | Public metadata | Available country/company sources | Public |
| Job adapters | Documented APIs and feeds | Normalized job links | No applicant data |
| Rule matching | Structured local configuration plus normalized jobs | Deterministic score and explanation | Does not open `resume_path` |
| AI command | Structured preferences plus public job fields | Validated score and explanation | Shell-free subprocess; excludes resume path/content, prior notes, and application state |
| Dashboard | Normalized local jobs JSON | Dense list, swipe review, saved matches, filters, and status export | Local storage; developer-owned deployment |
| Scheduling | Developer-selected local time | Rendered cron or Task Scheduler configuration | Render only; no automatic OS mutation |
| Secret scanning | Committed repository content and history | Push/PR CI result | No `user-data/` or `scans/` because those paths remain untracked |
