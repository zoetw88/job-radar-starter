# Operator guide

## 1. Initialize and scan

Run `job-radar doctor`, then initialize the local tracking store through the
tracking API or your agent/script adapter. Configure only official Greenhouse,
Lever, or Ashby boards you are authorized to query.

Atomic mode does not replace the last complete output when any configured
source fails. Best-effort mode writes partial healthy-source results with
`incomplete: true` and structured failures. Treat incomplete scans as partial,
not as proof that missing companies have no jobs.

## 2. Normalize, score, and review

Stable IDs and aliases prevent the same application from splitting when a
company or title spelling changes. Lifecycle merge records `first_seen` and
`last_seen`; absent jobs become stale and later expired according to the
configured policy.

Expired jobs without a tracking status remain available for 90 days after the
30-day expiry threshold, then are pruned from lifecycle state. Jobs with an
interested, applied, hidden, or expired tracking decision are retained.
`merge_scan_state` exposes `untracked_expired_retention_days` when a different
deterministic local window is required.

### Runtime dependency boundary

Pure scoring rules live in `job_radar.application` and depend only on the
normalized job model and user configuration. The CLI composes concrete
boundaries around them: `official_sources` selects Greenhouse, Lever, or Ashby;
`legacy_command_adapter` owns the bounded external scoring command;
`job_output` owns JSON file replacement; and Dashboard rendering remains a UI
adapter. `public_workflow` receives scoring and repository behavior through
callable or protocol ports instead of importing those concrete adapters.

Local rules run first. A hard exclusion cannot be reversed by a model. Eligible
jobs can receive fast review, while strong review is reserved for high-fit,
near-threshold, visa-uncertain, or conflicting cases. AI output is advisory.
The operator makes the application decision.

Review results use a versioned cache keyed by the stable job, JD hash, profile
rubric hash, prompt version, model, and review mode. Rejected records remain
auditable, and the deterministic rejected sample supports daily quality checks.

Configure providers through the bounded timeout contract
`review_with_timeout(mode, request, timeout_seconds=...)`. The provider adapter
must terminate or cancel its own subprocess or HTTP request when that timeout
expires. The built-in external-command adapter starts an isolated process
group, drains stdout and stderr incrementally with a 1 MiB limit for each
stream, and kills the whole process tree immediately on timeout or overflow.
Both the standalone `review` command and integrated `run` workflow execute the
configured review runner in a separate spawned process and kill that process
tree at the total deadline; custom Python runners must therefore be
importable/pickleable rather than local closures. Recommended
public defaults are a 30-second per-call
timeout, a 300-second total review deadline, and at most 100 fast-model calls
per run.

Configure a compact provider command explicitly as the final option:

```powershell
job-radar --json review --jobs scans\latest.json --output scans\review.json --provider-command python user-data\review_provider.py
job-radar --json run --provider-command python user-data\review_provider.py
```

Use `--per-call-timeout`, `--total-review-deadline`, and `--max-fast-calls`
before `--provider-command` to override the safe defaults. The command receives
one compact request on stdin and must write one response on stdout. It is not
invoked through a shell. The legacy `--ai-command` boundary uses the same
isolated, streaming, timeout, output-limit, and process-tree cleanup behavior.

Completed responses are checkpointed to the cache before the next provider
batch, and rejected audit progress is persisted after the first decision,
periodically in bounded batches, and at normal completion. An interrupted
replay therefore retains an initial durable checkpoint while avoiding
quadratic full-document rewrites for large rejected queues. Cache entries are
kept for 30 days by default; rejected audit entries, including rescued
decisions, are kept for 90 days by default. After date pruning, rejected
history is also limited to the newest deterministic 10,000 records and an
8 MiB serialized document, whichever limit is reached first. Override
`cache_retention_days` and
`rejected_retention_days` with positive integers when local policy requires a
different bounded time window; the safety caps still apply.

## 3. Track the funnel

Record each application and append events for interview, rejection, offer, and
other stage changes. Follow-up calculation covers thank-you notes, application
follow-up, no-response review, promised-response follow-up, and offer
deadlines. Funnel metrics and rejection-stage slices are derived from these
records rather than entered separately.

## 4. Build and use the dashboard

Run `job-radar build-dashboard` against the normalized view model. The dashboard
shows scan completeness, active/stale/expired lifecycle, recommendations,
rejected audit, application metrics, due actions, filters, cards, and swipe
review. Browser status buttons persist in localStorage.

## 5. Export, delete, or sync

Use `LocalTrackingStore.export_to` to export applications, events, lifecycle,
and rejection data outside the managed root. Use
`LocalTrackingStore.delete_tracking_data` to delete managed tracking, lifecycle,
rejected, review cache, and company-fact files. Exports, scans, and browser
localStorage require separate deletion.

Cloudflare sync is optional. If you enable it, configure your own Worker,
SQLite-backed Durable Object,
and bearer token; then verify GET, POST, and DELETE with the versioned status
contract. Do not treat the template as a shared hosted service.
