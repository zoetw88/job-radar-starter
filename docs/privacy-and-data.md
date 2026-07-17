# Privacy and local data

Job Radar is local-only by default. Sync never starts unless explicitly enabled.

## Managed local state

The operator chooses an absolute `user-data/` root. `initialize` creates:

- `tracking/applications.json`
- `tracking/events.json`
- `tracking/lifecycle.json`
- `tracking/rejected.json`
- `review/cache.json`
- `review/company-facts.json`

Raw and normalized runs are written under `scans/`. Dashboard decisions and
theme preference are separate browser localStorage values. Clearing files does
not clear browser localStorage, and clearing the browser does not delete files.

`LocalTrackingStore.export_to` writes applications, events, lifecycle, and
rejected state to a destination outside managed `user-data/`. Review cache and
company facts are intentionally excluded. Exported files are not deleted by
`LocalTrackingStore.delete_tracking_data`; the operator must locate and remove
exports separately.

`LocalTrackingStore.delete_tracking_data` deletes the six managed JSON files
above and then removes empty managed directories. It does not delete `scans/`,
browser localStorage, dashboard exports, or other files outside the configured
root.

Review cache is pruned to 30 days and rejected audit history to 90 days by
default. Both windows are locally configurable with positive
`cache_retention_days` and `rejected_retention_days` values. Rescued rejection
evidence is preserved for the same rejected-audit window rather than silently
removed when the final recommendation changes. After time pruning, rejected
history retains the newest deterministic records up to 10,000 entries and an
8 MiB serialized document; the first limit reached wins.

Lifecycle records without a tracking status are pruned 90 days after they
become expired (120 days after `last_seen` with the default expiry threshold).
Tracked lifecycle records remain until the user clears managed tracking data.

## External processing

The compact review contract minimizes data sent to a selected model provider,
and excludes locally derived summary, risk, company preference, must-have, and
visa-preference text. Its bounded evidence comes only from explicit public job
evidence, public location, and source-provenanced `public_skills`. The ordinary
`skills` field is not sent because local scoring may derive it from the private
profile. Any configured provider
receives the remaining documented request fields. Before
enabling one, the operator is responsible for reviewing provider retention,
training, sharing, deletion, regional processing, and account settings.

Optional status sync is disabled by default. If enabled, Cloudflare is a third
party and receives the status contract described in
[`external-data-contracts.md`](external-data-contracts.md). The operator is
responsible for credentials, access control, retention, disclosure, deletion,
and applicable law. This project is not legal advice.
