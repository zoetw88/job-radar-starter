# Migration from job-tracker-skill

`job-radar-starter` now contains the single developer application tracking,
events, follow-up cadence, funnel metrics, rejection analysis, lifecycle,
review, and dashboard workflows that previously required the separate
`job-tracker-skill` adapter.

## Order of operations

1. Merge job-radar-starter before archiving `job-tracker-skill`.
2. Verify a clean checkout, the release gate, and the generated dashboard.
3. Export the old applications and events for backup.
4. Translate records into the v1 tracking contracts and validate them in a
   disposable `user-data/` directory.
5. Compare application counts, follow-up actions, funnel stages, and rejection
   stages before selecting the new directory.
6. Archive the old repository only after the merged starter is the verified
   source of truth.

There is no automatic migration of personal data. This avoids guessing how
private fields, statuses, dates, or identity should map. Do not copy credentials,
resume contents, or old generated dashboards into the public repository.
