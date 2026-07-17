<!-- branch: codex/integrate-job-tracker -->

# integrate-job-tracker tasks

- [x] task-1: Establish versioned domain contracts for tracking and job lifecycle.
  - **RED first:** tests for application/job stable identity, allowed state
    transitions, retry-safe event identity, aliases, first/last seen,
    stale/expired state, legacy keys, unknown fields, bounds, and date parsing.
  - **Implement:** pure domain models, validators, serializers, and identity
    rules. No filesystem, CLI, dashboard, subprocess, HTTP, or Cloudflare imports.
  - **Verify:** focused domain tests plus the existing suite.
  - **Acceptance covered:** 2, 6.
  - **Commit boundary:** domain contracts and tests.

  <details>
  <summary>Verification evidence</summary>

  - Focused: `.venv\Scripts\python.exe -m pytest -q tests\test_tracking_domain.py`
    → `41 passed in 0.10s`
  - Full suite: `.venv\Scripts\python.exe -m pytest -q`
    → `66 passed in 0.68s`
  - Architecture grep found no filesystem, subprocess, HTTP, Cloudflare,
    Dashboard, or CLI imports under `job_radar/domain/`.
  - Acceptance 2 evidence: `job_radar/domain/tracking.py:95`,
    `job_radar/domain/tracking.py:124`, `job_radar/domain/tracking.py:131`,
    `job_radar/domain/tracking.py:145`, and
    `job_radar/domain/tracking.py:311`.
  - Acceptance 6 evidence: `job_radar/domain/tracking.py:212`,
    `job_radar/domain/tracking.py:232`, and
    `job_radar/domain/tracking.py:258`.

  </details>

- [x] task-2: Add atomic local repositories and privacy-safe initialization.
  - **RED first:** prove initialization is idempotent, all mutable state stays
    under the configured `user-data/` root, writes replace atomically, malformed
    state is preserved for recovery, traversal is rejected, export is explicit,
    and deletion removes only the scoped tracking data.
  - **Implement:** repository interfaces and filesystem adapters for tracking,
    lifecycle history, rejected queue, review cache, and company facts.
  - **Verify:** storage tests, `.gitignore` contract, tracked-file privacy grep,
    and existing tests.
  - **Acceptance covered:** 1, 2, 9.
  - **Commit boundary:** storage boundaries/adapters, blank examples, and tests.

  <details>
  <summary>Verification evidence</summary>

  - Focused: `.venv\Scripts\python.exe -m pytest -q tests\test_tracking_storage.py`
    → `27 passed in 1.45s`
  - Full suite: `.venv\Scripts\python.exe -m pytest -q`
    → `93 passed in 2.90s`
  - Acceptance 1 evidence: `job_radar/data/tracking_store.py:58`,
    `job_radar/data/tracking_store.py:80`,
    `job_radar/data/tracking_store.py:91`, and `.gitignore`.
  - Acceptance 2 evidence: `job_radar/data/tracking_store.py:23` and
    `job_radar/data/tracking_store.py:73`; malformed JSON fails closed and
    atomic replacement preserves the previous document on failure.
  - Acceptance 9 evidence: `examples/tracking-state.example.json` and
    `examples/aliases.example.json`; scoped privacy grep returned no matches.
  - Architecture grep found no upward Dashboard/CLI/application or network
    imports in `job_radar/data/`; the adapter uses the Python standard library.

  </details>

- [x] task-3: Implement application, interview, follow-up, and metrics commands.
  - **RED first:** cover application upsert, interview/status events, day 7-10
    follow-up, 14-day no-response suggestion, thank-you within 24 hours,
    promised date plus two business days, offer deadline, rejection stage,
    identical-event replay, deterministic metrics, and sample warnings.
  - **Implement:** application-layer commands over repository abstractions; no
    automated external messaging.
  - **Verify:** focused use-case tests and end-to-end temp-directory smoke.
  - **Acceptance covered:** 2, 3.
  - **Commit boundary:** tracking use cases and tests.

  <details>
  <summary>Verification evidence</summary>

  - Focused: `.venv\Scripts\python.exe -m pytest -q tests\test_tracking_commands.py`
    → `19 passed in 0.48s`
  - Full suite: `.venv\Scripts\python.exe -m pytest -q`
    → `112 passed in 2.57s`
  - Acceptance 2 evidence: `job_radar/tracking_commands.py:130` and
    `job_radar/tracking_commands.py:160`; identical commands/events are
    retry-safe and invalid transitions are validated before repository writes.
  - Acceptance 3 evidence: `job_radar/tracking_commands.py:245`,
    `job_radar/tracking_commands.py:357`, and
    `job_radar/tracking_commands.py:385`; due actions and metrics use fixed,
    deterministic ordering and compact JSON.
  - Architecture grep found no data adapter, filesystem, subprocess, network,
    Dashboard, or CLI imports in the command module.

  </details>

- [x] task-4: Add explicit atomic and best-effort source orchestration.
  - **RED first:** fake healthy, failing, malformed, oversized, and hanging
    sources; prove per-source timeout, deterministic order/deduplication,
    structured failures, incomplete marker, atomic rollback, and best-effort
    partial output without a hanging process.
  - **Implement:** application-level source runner over the existing official
    adapter boundary. Do not copy the private watchdog's `os._exit` behavior.
  - **Verify:** focused orchestration tests, official adapter tests, and CLI
    scan smoke in both modes.
  - **Acceptance covered:** 4, 5.
  - **Commit boundary:** source orchestration, output contract, CLI switches,
    and tests.

  <details>
  <summary>Verification evidence</summary>

  - A Windows startup timing regression was fixed before final verification.
  - Focused: `.venv\Scripts\python.exe -m pytest -q tests\test_source_orchestration.py`
    → `14 passed in 21.60s`
  - Full suite: `.venv\Scripts\python.exe -m pytest -q`
    → `126 passed in 20.84s`
  - Acceptance 4 evidence: `job_radar/source_orchestration.py:102` and
    `job_radar/cli.py:74`; output is versioned, deterministic, failure-safe,
    and marks partial scans incomplete.
  - Acceptance 5 evidence: `job_radar/source_orchestration.py:23`,
    `job_radar/source_orchestration.py:68`, and the Windows hanging-source
    test; child execution starts its timeout after a READY handshake and is
    terminated/joined on timeout.
  - Grep found no `os._exit`, thread fallback, Dashboard, or CLI upward import
    in the orchestrator.

  </details>

- [x] task-5: Implement stable lifecycle merge and status migration.
  - **RED first:** reordered/multi-day scan fixtures covering aliases, stable
    keys, duplicate provider records, preserved curated fields, first/last seen,
    stale/expired thresholds, and legacy local status migration.
  - **Implement:** generic merge/lifecycle use cases and user-owned alias config;
    examples contain invented companies only.
  - **Verify:** lifecycle tests, repeated scan smoke, and existing Dashboard
    state tests.
  - **Acceptance covered:** 6.
  - **Commit boundary:** lifecycle merge, alias config contract, and tests.

  <details>
  <summary>Verification evidence</summary>

  - Focused: `.venv\Scripts\python.exe -m pytest -q tests\test_lifecycle_merge.py`
    → `16 passed in 0.12s`
  - Full suite: `.venv\Scripts\python.exe -m pytest -q`
    → `142 passed in 32.49s`
  - Acceptance 6 evidence: `job_radar/lifecycle_merge.py:255`,
    `job_radar/lifecycle_merge.py:231`, and
    `job_radar/lifecycle_merge.py:216`; merge ordering, aliases, lifecycle
    dates, freshness, and legacy status migration are deterministic.
  - Incomplete scans preserve active state for jobs in failed source/company
    scopes at `job_radar/lifecycle_merge.py:305` and
    `job_radar/lifecycle_merge.py:331`.
  - Architecture grep found no data, Dashboard, provider adapter, CLI,
    filesystem, subprocess, or network imports.

  </details>

- [x] task-6: Add compact tiered AI review, versioned cache, and rejected sampling.
  - **RED first:** strict short schema, minimal request fields, provider failure,
    fast/strong routing, escalation budget, hard-exclusion precedence, cache
    hit/invalidation matrix, evidence-backed fact TTL, complete reject reasons,
    deterministic daily sampling, disagreement/rescue, and audit retention.
  - **Implement:** provider-neutral review interfaces and application pipeline.
    Reuse the existing external-command safety boundary; provider-specific code
    remains optional.
  - **Verify:** focused review tests with fake providers, token/payload-size
    assertions, and no-network CLI smoke.
  - **Acceptance covered:** 7, 8, 9.
  - **Commit boundary:** review pipeline, schemas/cache/sampling, CLI, and tests.

  <details>
  <summary>Verification evidence</summary>

  - Focused AI review plus source regression:
    `.venv\Scripts\python.exe -m pytest -q tests\test_source_orchestration.py tests\test_ai_review_pipeline.py`
    → `36 passed in 13.91s`
  - Full suite: `.venv\Scripts\python.exe -m pytest -q`
    → `164 passed in 15.14s`
  - Acceptance 7 evidence: `job_radar/ai_review.py:115`,
    `job_radar/ai_review.py:158`, and `job_radar/ai_review.py:337`;
    requests are minimal/bounded, responses strict, hard exclusions precede
    providers, and escalation is deterministic and budgeted.
  - Acceptance 8 evidence: `job_radar/ai_review.py:47`; every versioned cache
    input is included and cache hits are reported.
  - Acceptance 9 evidence: `job_radar/ai_review.py:289` and
    `job_radar/ai_review.py:337`; rejected audits retain reason codes and rescue
    history while daily sampling is deterministic.
  - Disabled `review` CLI at `job_radar/cli.py:442` performs no network/provider
    call and writes an empty versioned result.

  </details>

- [x] task-7: Extend the existing Dashboard without changing its visual identity.
  - **RED first:** generated-output and browser tests for loading, complete vs
    partial scan, failed sources, rejected review, stale/expired, tracking
    summaries, legacy status migration, filters, recommendations, swipe/keyboard
    behavior, local persistence, export, mobile overflow, and safe rendering.
  - **Implement:** extend the versioned Dashboard view model and framework-free
    renderer. Preserve current layout, card density, filters, and interaction
    language; use only invented example data.
  - **Verify:** Dashboard unit/contracts, example build, desktop/mobile browser
    smoke, screenshots, console, and overflow checks.
  - **Acceptance covered:** 10.
  - **Commit boundary:** Dashboard schema/renderer/assets and tests.

  <details>
  <summary>Verification evidence</summary>

  - Focused: `.venv\Scripts\python.exe -m pytest -q tests\test_dashboard_states.py tests\test_dashboard.py`
    → `14 passed in 0.55s`
  - Full Python suite: `.venv\Scripts\python.exe -m pytest -q`
    → `174 passed in 23.84s`
  - Chromium: `npm run test:browser` → `2 passed in 20.3s` at
    1440×1000 and 390×844; no horizontal overflow, console error, or page error.
  - Acceptance 10 evidence: `job_radar/dashboard.py:401`,
    `job_radar/dashboard.py:354`, `job_radar/dashboard.py:206`, and
    `job_radar/dashboard.py:227`; the versioned view model exposes scan,
    lifecycle, rejected, tracking, migration, and export states while retaining
    the existing list/deck/matches interaction model.
  - Screenshots visually inspected at
    `test-results/dashboard-evidence/desktop.png` and
    `test-results/dashboard-evidence/mobile-390.png`; the original
    industrial/editorial density and card language are preserved.
  - Playwright is pinned to `1.61.1`; the originally proposed `1.54.1` was not
    used because versions below `1.55.1` are affected by HIGH
    `GHSA-7mvr-c777-76hp`. `npm audit --audit-level=high` reports zero
    vulnerabilities.

  </details>

- [x] task-8: Provide an optional, self-owned Cloudflare sync template.
  - **RED first:** tests for fail-closed auth, trusted identity, GET/POST,
    allowlisted status values, legacy-key cleanup, payload/key bounds,
    rate/abuse consideration, safe errors, no-store/private caching, fake
    cross-device persistence, and absence of production identifiers.
  - **Implement:** isolated optional Worker/Pages template and documented local
    configuration. Local-only remains default and runtime code does not depend
    on Cloudflare.
  - **Verify:** Worker tests, dry-run/preview smoke when credentials permit,
    generated-config inspection, and secret scan.
  - **Acceptance covered:** 11.
  - **Commit boundary:** optional sync template, configuration examples, tests,
    and threat/privacy notes.

  <details>
  <summary>Verification evidence</summary>

  - Python contract plus full suite:
    `.venv\Scripts\python.exe -m pytest -q` → `180 passed in 24.33s`
  - Worker runtime: `npm test` in `optional-sync/cloudflare`
    → `28 passed in 7.27s` using local workerd and isolated KV.
  - TypeScript: `npm exec tsc -- --noEmit` passed.
  - Dependency audit: `npm audit --audit-level=high`
    → `0 vulnerabilities`.
  - Wrangler: `npm exec wrangler -- deploy --dry-run` passed with only
    `env.STATUS_KV`; no login, account, remote write, or deployment occurred.
  - Chromium regression: `npm run test:browser` → `2 passed in 22.8s`.
  - Acceptance 11 evidence: `optional-sync/cloudflare/src/index.ts:1`,
    `optional-sync/cloudflare/src/index.ts:49`,
    `optional-sync/cloudflare/src/index.ts:160`, and
    `optional-sync/cloudflare/wrangler.jsonc`; auth/binding failures close,
    identity is fixed, payloads/statuses are bounded, errors are fixed, and
    responses are private/no-store.
  - Privacy grep found no production account, namespace, route, domain, maintainer,
    credential, or private host values in the template.
  - A background HTTP preview was blocked by shell policy; local workerd KV
    integration plus Wrangler dry-run provide the accepted non-production
    runtime evidence.

  </details>

- [x] task-9: Consolidate agent-neutral docs, source policy, migration, and release gates.
  - **RED first:** documentation/release contracts proving Claude/Codex/other
    agent neutrality, local retention/export/deletion, exact external fields,
    optional sync/provider sharing, official-source allowlist, explicit
    LinkedIn/Indeed/Google Jobs/104 exclusion, and preservation of existing CLI
    workflows.
  - **Implement:** README, source policy, normalized schemas, migration from
    `job-tracker-skill`, operator examples, decisions, and gotchas. Do not claim
    legal approval or universal scoring quality.
  - **Verify:** clean install; full tests; example Dashboard build; tracking,
    atomic/best-effort scan, AI fake-provider, lifecycle, export/delete, and
    optional sync smoke; `git diff --check`; Gitleaks; dependency audit; grep
    for private names/data/URLs/paths; browser QA.
  - **Acceptance covered:** 1-13.
  - **Commit boundary:** documentation, release contracts, and final evidence.

  <details>
  <summary>Verification evidence</summary>

  - Focused public release contracts: `20 passed`.
  - Independent end-to-end:
    `scripts/verify-public-release.ps1` → exit `0`.
  - The gate produced: Python `200 passed`, Dashboard build `2 jobs`,
    root and optional npm audits `0 vulnerabilities`, Chromium `2 passed`,
    TypeScript typecheck passed, Worker Vitest `28 passed`, Wrangler
    `deploy --dry-run` passed with only `STATUS_KV`, Gitleaks `8.30.1`
    reported `no leaks found`, and privacy/generated/diff checks passed.
  - Acceptance 12 evidence: `README.md`, `SOURCE_POLICY.md`,
    `docs/privacy-and-data.md`, `docs/external-data-contracts.md`, and
    `docs/operator-guide.md`; Claude, Codex, other agents, and scripts share
    one contract, while risky bundled scraper sources remain excluded.
  - Acceptance 13 evidence: `scripts/verify-public-release.ps1` and
    `docs/release-checklist.md`.
  - No production deployment occurred and `job-tracker-skill` remains
    unarchived pending review, merge, and post-merge acceptance.

  </details>

- [x] task-10: Wire the public CLI into one coherent versioned workflow.
  - **RED first:** scan-envelope input for score/build, integrated run output,
    lifecycle/tracking/view-model wiring, disabled and fake-provider review,
    legacy list compatibility, and a release-gate end-to-end smoke.
  - **Implement:** application orchestration and minimal CLI commands/options;
    do not place workflows in adapters or Dashboard code.
  - **Verify:** focused CLI/application smoke plus full release gate.
  - **Acceptance covered:** 14, 20.
  - **Commit boundary:** workflow wiring, CLI contracts, and tests.

  <details>
  <summary>Verification evidence</summary>

  - Combined remediation focused suite:
    `.venv\Scripts\python.exe -m pytest -q tests\test_public_workflow.py tests\test_tracking_commands.py tests\test_tracking_storage.py tests\test_source_orchestration.py`
    → `86 passed in 30.29s`
  - Independent release gate: `scripts/verify-public-release.ps1` → exit `0`;
    workflow smoke `8 passed`, full Python `226 passed`, Chromium `2 passed`,
    Worker `28 passed`, audits/Gitleaks/Wrangler dry-run green.
  - Acceptance 14 evidence: `job_radar/cli.py:186`,
    `job_radar/cli.py:472`, `job_radar/public_workflow.py:112`, and
    `job_radar/public_workflow.py:163`; legacy lists and versioned envelopes
    feed one scan/review/lifecycle/tracking/Dashboard workflow.
  - Acceptance 20 evidence: `scripts/verify-public-release.ps1`; the release
    gate now begins with the public workflow smoke.

  </details>

- [x] task-11: Make status events atomic and conflicting retries explicit.
  - **RED first:** second-write failure, rollback/recovery, identical replay,
    conflicting replay status/details, and temp-directory persistence.
  - **Implement:** repository unit-of-work or a single atomic aggregate boundary.
  - **Verify:** focused tracking/storage tests and full suite.
  - **Acceptance covered:** 15.
  - **Commit boundary:** atomic repository boundary, command behavior, and tests.

  <details>
  <summary>Verification evidence</summary>

  - Focused: `.venv\Scripts\python.exe -m pytest -q tests\test_tracking_commands.py tests\test_tracking_storage.py`
    → `54 passed in 3.52s`
  - Acceptance 15 evidence: `job_radar/data/tracking_store.py:86`,
    `job_radar/data/tracking_store.py:201`,
    `job_radar/tracking_commands.py:240`, and
    `job_radar/tracking_commands.py:251`; application/event documents use a
    recovery journal and one repository commit boundary, identical replay is
    accepted, and conflicting replay is rejected before writes.
  - Independent release gate after task-10/task-12 completion: full Python
    `226 passed`; all task-11 behavior remains covered.

  </details>

- [x] task-12: Bound source concurrency and eliminate Queue payload deadlocks.
  - **RED first:** maximum active workers, near-limit successful payload,
    timeout/failure mix, deterministic output, and orphan/IPC cleanup.
  - **Implement:** rolling bounded workers and a result transport that is
    drained before process completion can block.
  - **Verify:** repeated Windows stress tests and full suite.
  - **Acceptance covered:** 16.
  - **Commit boundary:** source worker scheduler/transport and tests.

  <details>
  <summary>Verification evidence</summary>

  - Focused source suite: `24 passed in 23.91s`.
  - Repeated bounded/9,500-job/mixed-cleanup stress: three consecutive passes.
  - Combined remediation focused suite: `86 passed in 30.29s`.
  - Independent release gate: full Python `226 passed`.
  - Acceptance 16 evidence: `job_radar/source_orchestration.py` uses a
    validated rolling `max_concurrency=4` scheduler and one-way Pipe transport
    drained before join; CLI exposes `--max-source-concurrency`.
  - Post-test process inspection found no Job Radar child processes or IPC
    workers left behind.

  </details>

- [x] task-13: Bound AI execution and long-term review state.
  - **RED first:** provider hang, per-call timeout, total deadline,
    max-fast-calls, checkpoint replay, linear current-rejected lookup,
    retention/pruning, and deterministic reports.
  - **Implement:** bounded provider execution and repository checkpoints with
    documented retention defaults.
  - **Verify:** fake-provider timing tests, scale tests, and full suite.
  - **Acceptance covered:** 17.
  - **Commit boundary:** AI execution/cache/audit retention and tests.

  <details>
  <summary>Verification evidence</summary>

  - Independent AI/workflow/storage suite:
    `.venv\Scripts\python.exe -m pytest -q tests\test_public_workflow.py tests\test_ai_review_pipeline.py tests\test_tracking_storage.py`
    → `66 passed in 2.58s`.
  - Acceptance 17 evidence: `job_radar/ai_review.py` enforces per-call timeout,
    total deadline, fast-call budget, immediate cache/rejected checkpoints,
    30-day cache retention, 90-day rejected-audit retention, and a linear
    current-rejected lookup.
  - `job_radar/public_workflow.py` explicitly passes the shared safe defaults
    `30 seconds / 300 seconds / 100 fast calls` to every configured review
    runner; disabled review remains provider-free.

  </details>

- [x] task-14: Keep Dashboard rendering bounded for large scans.
  - **RED first:** one embedded jobs payload, indexed rejected lookup,
    bounded initial render/pagination, 1k/5k artifact-size thresholds, and
    browser interaction/mobile regressions.
  - **Implement:** a bounded rendering strategy that preserves current layout,
    filters, recommendations, deck, matches, and accessibility.
  - **Verify:** scale tests, Python Dashboard tests, and Chromium.
  - **Acceptance covered:** 18.
  - **Commit boundary:** Dashboard data/render performance and tests.

  <details>
  <summary>Verification evidence</summary>

  - Independent focused Dashboard suite:
    `.venv\Scripts\python.exe -m pytest -q tests\test_dashboard_states.py tests\test_dashboard.py`
    → `18 passed in 2.63s`.
  - Independent Chromium run: `npm run test:browser`
    → `3 passed in 28.2s`, covering desktop, 390 px mobile, and bounded
    50→100 load-more behavior with filters preserved.
  - Scale artifacts: 1,000 jobs → `747,344 bytes`; 5,000 jobs →
    `3,254,544 bytes`, below the accepted `850,000` and `3,500,000` limits.
  - Acceptance 18 evidence: `job_radar/dashboard.py` emits one canonical jobs
    payload, indexes rejected membership with a `Set`, caps initial
    server/client rendering at 50, and preserves the original layout,
    filters, recommendations, deck, matches, local state, and export behavior.

  </details>

- [x] task-15: Prevent optional sync lost updates and stored-state overflow.
  - **RED first:** concurrent two-device writes, conflict/retry behavior,
    merged-size overflow, idempotence, and cross-device reads.
  - **Implement:** a strongly serialized self-owned storage boundary or an
    explicit conflict protocol that cannot silently discard another write.
  - **Verify:** local Worker integration, typecheck, audit, and dry-run.
  - **Acceptance covered:** 19.
  - **Commit boundary:** optional sync consistency contract and tests.

  <details>
  <summary>Verification evidence</summary>

  - Independent Worker integration: `npm test`
    → `31 passed in 3.68s`.
  - Independent TypeScript, dependency, and packaging gates:
    `npm exec tsc -- --noEmit` passed;
    `npm audit --audit-level=high` → `0 vulnerabilities`;
    `npm exec wrangler -- deploy --dry-run` passed with only
    `STATUS_COORDINATOR (StatusCoordinator)`.
  - Independent Python public contract:
    `.venv\Scripts\python.exe -m pytest -q tests\test_optional_cloudflare_sync_contract.py`
    → `6 passed in 0.16s`.
  - Acceptance 19 evidence: the fixed-owner SQLite Durable Object serializes
    GET/POST/DELETE, merges writes in `transactionSync`, and rejects a merged
    state above 500 records with `409 stored_state_limit_exceeded` before
    changing stored data. No deployment occurred.

  </details>

- [x] task-16: Align schemas, privacy scanning, and end-to-end release evidence.
  - **RED first:** runtime/schema bound parity, generic tracked spec metadata,
    all-tracked-text privacy scan, and complete public workflow smoke.
  - **Implement:** schemas/docs/spec sanitization and fail-closed release gates.
  - **Verify:** schema validators, Gitleaks/privacy scan, release script, and
    three-lens re-review.
  - **Acceptance covered:** 20 and release readiness for 14-19.
  - **Commit boundary:** schemas, privacy/release gates, and review evidence.

  <details>
  <summary>Verification evidence</summary>

  - RED contract tests preceded the implementation and remain in the published
    suite.
  - Focused schema/workflow/AI suite:
    `.venv\Scripts\python.exe -m pytest -q tests\test_public_release_contract.py tests\test_public_workflow.py tests\test_ai_review_pipeline.py`
    → `60 passed in 0.97s`.
  - Independent end-to-end: `scripts/verify-public-release.ps1` → exit `0`.
  - The release gate produced: run→tracking export→delete smoke `1 passed`,
    full Python `240 passed`, generated Dashboard inspection passed, root and
    optional npm audits `0 vulnerabilities`, Chromium `3 passed`, TypeScript
    passed, Worker `31 passed`, Wrangler Durable Object dry-run passed,
    Gitleaks `8.30.1` reported no leaks, tracked release-text privacy scan
    passed, and `git diff --check` passed.
  - Acceptance 20 evidence: published AI/sync schema limits now match enforced
    runtime caps; tracked Markdown/JSON/YAML/TOML/text/HTML is enumerated with
    `git ls-files`; spec metadata is generic; no production deployment
    occurred.

  </details>

- [x] task-17: Make configured AI review executable and hard-bounded.
  - **RED first:** installed CLI configured provider, configured release smoke,
    provider ignoring timeout, review runner ignoring timeout, total deadline,
    and Windows cleanup.
  - **Implement:** explicit provider/config CLI boundary and killable execution
    outside the blocking provider/review-runner call.
  - **Verify:** CLI subprocess smoke, wall-clock tests, no orphan processes,
    and full AI/workflow suite.
  - **Acceptance covered:** 21, 22.
  - **Commit boundary:** provider adapter/CLI/workflow timeout boundary and tests.

  <details>
  <summary>Verification evidence</summary>

  - RED configured-provider and deadline tests preceded implementation.
  - Installed `python -m job_radar review --provider-command ...` and
    `run --provider-command ...` execute the compact provider boundary without
    Python-only injection.
  - Provider and arbitrary review-runner hard-kill tests passed three
    consecutive runs and verified the Windows child PID no longer existed.
  - 2,000 hard rejects completed in `0.734s` with `21` durable writes instead
    of 2,000 whole-history rewrites.
  - Agent full Python receipt: `258 passed in 50.85s`; merged independent
    release receipt: `259 passed in 36.44s`.

  </details>

- [x] task-18: Bound retained review, lifecycle, source, and rejected UI scale.
  - **RED first:** 2,000 hard rejects/write count/time, 5k jobs plus 5k rejects,
    lifecycle retention with tracked preservation, and pre-IPC oversized source.
  - **Implement:** amortized durable checkpoints, rejected audit paging,
    documented lifecycle retention, and producer-side source caps.
  - **Verify:** deterministic scale tests, browser regression, Windows process
    cleanup, and full suite.
  - **Acceptance covered:** 23-26.
  - **Commit boundary:** scale/retention behavior and tests.

  <details>
  <summary>Verification evidence</summary>

  - RED scale and retention tests preceded implementation.
  - Focused Python: `65 passed`; Chromium: `3 passed`.
  - 5,000 jobs plus 5,000 rejects produced `3,352,957 bytes`, 20 initial
    rejected rows, and 50 initial job cards with load-more access preserved.
  - Untracked lifecycle entries are retained through day 120 and pruned on day
    121; tracked entries remained at day 184.
  - Official adapters enforce producer-side job ceilings and workers return a
    small oversized marker rather than a complete oversized IPC payload.
  - Merged independent release receipt: Chromium `3 passed`, full Python
    `259 passed`.

  </details>

- [x] task-19: Enforce hosted release gates and truthful architecture boundaries.
  - **RED first:** hosted workflow contract, all tracked source/release text
    privacy enumeration, and import-direction checks.
  - **Implement:** GitHub hosted CI, broader fail-closed privacy gate, and
    minimal dependency inversion or corrected architecture documentation backed
    by import tests.
  - **Verify:** workflow contract tests, local release gate, clean tracked scan,
    and three-lens re-review.
  - **Acceptance covered:** 27 and ship readiness for 21-26.
  - **Commit boundary:** CI/privacy/architecture enforcement and evidence.

  <details>
  <summary>Verification evidence</summary>

  - RED CI/privacy/application and concrete job-model tests preceded
    implementation.
  - Hosted `windows-latest` CI installs pinned runtimes/dependencies, verifies
    pinned Gitleaks `8.30.1`, and runs the same public release script on pushes
    and pull requests without a production deploy.
  - Privacy enumeration covers tracked release and source/script extensions;
    local scan returned no blocked metadata.
  - `Job` is a domain model, application code receives the Dashboard renderer
    through injection, and application/workflow import-direction tests pass.
  - Independent end-to-end `scripts/verify-public-release.ps1` → exit `0`:
    workflow smoke `1 passed`, full Python `259 passed`, Chromium `3 passed`,
    Worker `31 passed`, typecheck/audits/Wrangler dry-run/Gitleaks/privacy and
    diff checks passed.

  </details>

- [x] task-20: Harden external command execution and hard deadlines.
  - **RED first:** standalone review runner stall, noisy stdout/stderr,
    descendant process survival, timeout/overflow cleanup, and legacy AI
    command bounds.
  - **Implement:** one bounded streaming command/process-tree boundary reused by
    configured review and legacy command adapters; wrap standalone review in
    the outer killable runner.
  - **Verify:** Windows descendant PID tests, memory/output caps, repeated
    timeout tests, and installed CLI smoke.
  - **Acceptance covered:** 28, 29.
  - **Commit boundary:** external process boundary, CLI integration, and tests.

  <details>
  <summary>Verification evidence</summary>

  - RED external-process boundary tests preceded implementation.
  - Standalone and integrated review use the same outer hard-deadline process
    boundary; compact and legacy commands share bounded streaming capture.
  - stdout/stderr are capped independently at 1 MiB and overflow/timeout kills
    the complete Windows process tree; tests verified parent and descendant
    PIDs were no longer running.
  - Focused tests: `17 passed`; wider CLI/workflow/contracts: `55 passed`.
  - Merged full release receipt: Python `271 passed, 1 skipped`.

  </details>

- [x] task-21: Bound long-term rejected state and source cleanup.
  - **RED first:** retained-history cardinality/bytes, multi-day 2k rejects,
    SIGTERM-ignoring source, forced kill, and orphan cleanup.
  - **Implement:** deterministic rejected caps/compaction and bounded
    terminate→kill→join cleanup.
  - **Verify:** scale/retention benchmark, process cleanup tests, and full suite.
  - **Acceptance covered:** 30, 31.
  - **Commit boundary:** retained-state/source cleanup behavior and tests.

  <details>
  <summary>Verification evidence</summary>

  - RED retained-state and source-cleanup tests preceded implementation.
  - Rejected history applies 90-day pruning, then deterministic caps of 10,000
    records and 8 MiB serialized JSON at every checkpoint.
  - Source cleanup uses terminate, bounded 1-second join, kill, bounded final
    1-second join, connection close, and portable cleanup regression tests.
  - History-heavy 14k benchmark: `3.45s`; 2k current rejects: `2.48s`;
    byte-heavy audit: `0.47s`.
  - Combined AI/source/storage/contracts: `114 passed, 1 POSIX-only skipped`.

  </details>

- [x] task-22: Finish reproducible CI, complete privacy coverage, and layer boundaries.
  - **RED first:** extensionless/jsonc privacy fixtures, hashed Python lock,
    and AST/import tests forbidding concrete ATS/subprocess/filesystem
    orchestration in application code.
  - **Implement:** all-tracked-text detection, hash-locked Python CI install,
    and move concrete orchestration behind injected boundaries.
  - **Verify:** clean hosted-workflow contract, privacy scan, architecture
    tests, release gate, and final three-lens review.
  - **Acceptance covered:** 32-34.
  - **Commit boundary:** CI/privacy/architecture and final evidence.

  <details>
  <summary>Verification evidence</summary>

  - CI/privacy, architecture, and exact-license-allowlist RED tests preceded
    implementation.
  - `requirements-ci.lock` pins and SHA-256 verifies all hosted Windows Python
    packages; a clean `pip --require-hashes` target install succeeded.
  - Privacy gate content-inspects every `git ls-files` path, including LICENSE,
    `.gitignore`, and JSONC; only complete path+trimmed-line allowlists are
    accepted. The LICENSE author line is the sole author metadata allowance.
  - `application.py` owns pure scoring/injected use cases only. Concrete ATS,
    bounded command, atomic output, and legacy orchestration live in outer
    modules with AST import-direction enforcement.
  - Independent `scripts/verify-public-release.ps1` → exit `0`: workflow smoke
    `1 passed`, Python `271 passed, 1 skipped`, Chromium `3 passed`, Worker
    `31 passed`, audits/typecheck/Wrangler/Gitleaks/privacy/diff all green.

  </details>

- [x] task-23: Close AI disclosure, privacy-history, and cleanup deadline gaps.
  - **RED first:** local summary/risk leakage, synthetic privacy sentinel,
    UTF-16 tracked metadata, stalled taskkill, and stalled final wait/join.
  - **Implement:** public-only compact evidence, fail-closed text decoding,
    bounded cleanup tools/final waits, and a clean-root publication branch.
  - **Verify:** disclosure payload assertions, UTF-8/UTF-16 privacy fixtures,
    mocked cleanup stalls, full release gate, clean-history scan, and final
    three-lens review.
  - **Acceptance covered:** 35-37.
  - **Commit boundary:** final privacy/deadline behavior, clean publication
    history, and evidence.

  <details>
  <summary>Verification evidence</summary>

  - Disclosure/privacy, cleanup, and load-tolerant deterministic scale tests
    preceded implementation.
  - Compact requests now use explicit JD evidence, public location, and
    source-provenanced public skills only; local summary/risk/profile-derived
    skills, preferences, visa, and must-have rules are excluded.
  - Privacy scanner strictly decodes UTF-8/UTF-16LE/UTF-16BE, rejects unknown
    NUL-bearing text, uses synthetic positive controls, and allows only the
    exact LICENSE author line. It passed all `107` tracked files.
  - Cleanup stall tests bound taskkill, final waits, and multiprocessing joins
    to one second each while retaining process-tree cleanup.
  - Independent `scripts/verify-public-release.ps1` → exit `0`: workflow smoke
    `1 passed`, Python `278 passed, 1 POSIX-only skipped`, Chromium `3 passed`,
    Worker `31 passed`, audits/typecheck/Wrangler/privacy/Gitleaks/diff all
    green.
  - Publication-history proof is completed on the clean-root branch rather
    than this non-publishable development branch.

  </details>

- [x] task-24: Close final publication review findings.
  - **RED first:** require protocol-specific AI disclosure language; reproduce
    loaded-Windows wall-clock failures while retaining child-death assertions.
  - **Implement:** name both external AI protocols and make timing ceilings
    scheduler-tolerant without changing runtime deadlines or cleanup budgets.
  - **Verify:** focused policy/process tests, complete release gate, and a
    root-history publication scan with no removed private metadata.
  - **Acceptance covered:** 36 and 38.
  - **Commit boundary:** final review remediation and clean-root evidence.

  <details>
  <summary>Verification evidence</summary>

  - Protocol disclosure RED failed before `SOURCE_POLICY.md` named legacy
    `--ai-command` and compact `--provider-command` separately.
  - Privacy-gate tests failed before real maintainer markers became injected
    input and before Dashboard generation moved to a temporary artifact.
  - The PID helper race was reproduced with an empty visible file, then fixed
    by waiting for parseable content; returning-runner cleanup passed 10
    consecutive isolated runs and the affected suites passed `51` tests.
  - The clean-root candidate had no parent and contained one reachable commit;
    removed company/private-repo/deployment markers returned no tree or history
    matches.
  - Clean-root `scripts/verify-public-release.ps1` first exposed a second direct
    PID-read race, then exited `0` after all PID assertions used the bounded
    helper: workflow smoke `1 passed`, Python `291 passed, 1 skipped`, Chromium
    `3 passed`, Worker `31 passed`, audits/typecheck/Wrangler/privacy/Gitleaks,
    reproducible Dashboard comparison, and diff gates all green.
  - A final negative regression proved a blocked marker cannot hide in a
    copyright-shaped LICENSE line; only injected, case-sensitive
    `relative/path::exact complete line` entries are allowed.
  - The first hosted run passed all Python tests but exposed a Playwright
    `.venv`-only launcher. A RED contract, global-Python simulation, and the
    final local gate proved environment-selected Python plus explicit repo
    `PYTHONPATH`; Chromium remained `3 passed`.

  </details>

## Review and Ship checklist

- Every task has persisted evidence for each covered acceptance criterion.
- Spec, security/privacy/legal-boundary, and performance reviews have no
  unaccepted findings.
- No generated Dashboard or fixture contains a maintainer's real jobs, target companies,
  evaluations, application state, profile, aliases, URLs, or Cloudflare config.
- PR CI and secret scanning pass from a clean checkout.
- Merge before archiving `job-tracker-skill` or changing pins.
- Archive the completed spec and verify final public repo metadata and links.
