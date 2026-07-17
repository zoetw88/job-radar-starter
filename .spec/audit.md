# integrate-job-tracker review audit

Reviewed after all nine implementation tasks and the public release gate passed.
The branch is **not ready to ship** until the accepted findings below are fixed
or explicitly waived.

## P1 findings

1. The documented CLI pipeline is not integrated. Resilient `scan` writes a
   versioned envelope, while `score` and `build-dashboard` accept only a
   top-level jobs list. `run` still uses the legacy pipeline, `review` is always
   disabled, and tracking/lifecycle/versioned Dashboard commands have no public
   caller.
2. Status-changing application events are not atomic: the application document
   is written before the event document, so a second-write failure leaves a
   status without its audit event.
3. Windows source orchestration starts every company process at once. A large
   public catalog can exhaust process, handle, CPU, or memory limits.
4. AI provider calls have no enforced timeout, cancellation, total deadline, or
   fast-call budget; one hung provider can block the daily run indefinitely.
5. Dashboard output duplicates jobs across HTML and embedded JSON and performs
   repeated rejected-history scans. Synthetic output reached about 3 MB for
   1,000 jobs and 15 MB for 5,000 jobs.
6. Rejected history and review cache have no retention/pruning, and current
   rejected lookup is quadratic in history versus current jobs.
7. Cloudflare KV read-modify-write can permanently lose concurrent updates from
   two devices.

## P2 findings

1. Conflicting retries reuse the same event identity without checking the
   requested status transition.
2. The release gate does not exercise the advertised end-to-end
   scan-to-Dashboard/tracking workflow and therefore missed the CLI integration
   break.
3. Published JSON Schemas are looser than runtime validation.
4. `.spec/current.md` includes private repository, personal name, local path,
   and personal-site context; the privacy gate scans only selected public data
   folders.
5. Source workers put the full job list into a multiprocessing queue while the
   parent joins before draining it, which can deadlock or false-timeout for
   large valid payloads.
6. The Worker validates each request at 500 statuses but does not re-check the
   merged stored document, allowing unbounded growth across requests.

## P3 findings

1. Worker abuse/rate controls are documented but not enforced by the template.
2. GitHub Actions use floating action tags and Gitleaks excludes artifact-like
   paths broadly enough that a force-added tracked secret could be skipped.

## Verified positive controls

- `scripts/verify-public-release.ps1` completed with exit 0.
- Python: 200 passed.

## Fresh remediation re-review after task 16

The second three-lens review found additional unaccepted issues; the branch is
still not ready to ship.

### P1

1. Installed CLI review remains disabled unless a Python caller injects a
   `review_runner`.
2. Provider and review-runner deadlines are cooperative and cannot terminate a
   blocking implementation.
3. Rejected progress rewrites and sorts the complete retained history for every
   rejected job, producing quadratic runtime.

### P2

1. Release smoke does not exercise configured compact review and hosted CI runs
   only Gitleaks.
2. Privacy enumeration excludes tracked source and script text.
3. Documented dependency direction does not match executable imports.
4. Rejected audit HTML is unwindowed and exceeds the 5k artifact budget when
   rejected history is also large.
5. Expired untracked lifecycle state grows without retention pruning.
6. Per-source caps are checked only after complete materialization and IPC.

Tasks 17-19 and acceptance criteria 21-27 cover these findings. No merge,
deployment, archive, or pin action is authorized before another clean review.

## Final review after tasks 17-19

No P1 remained, but reviewers found additional P2 gaps:

1. Standalone review lacked the integrated outer hard deadline.
2. Provider and legacy command output limits were checked after unbounded
   buffering; descendant process cleanup was not proven.
3. Source termination used an unbounded join without forced-kill fallback.
4. Rejected retention lacked count/serialized-byte ceilings.
5. Privacy enumeration omitted extensionless and JSONC tracked files.
6. Hosted Python dependencies were not installed from a hash-verified lock.
7. Application code still contained concrete ATS, subprocess, and filesystem
   orchestration despite the documented dependency direction.

Tasks 20-22 and acceptance criteria 28-34 cover these findings. The green local
release receipt remains historical evidence only.

## Release-gate review after tasks 20-22

No P1 remained. Reviewers found three final P2 gaps:

1. Compact AI evidence forwarded locally derived summary/risk text and could
   disclose private preference/scoring rules.
2. Privacy tests still contained real identifiers, UTF-16 text could bypass the
   NUL-based classifier, and removed private metadata remained in branch
   history.
3. Windows cleanup commands and final wait/join calls could themselves block
   beyond the hard deadline.

Task 23 and acceptance criteria 35-37 cover these gaps. The current development
branch must not be pushed; publication requires a clean squash/new-root branch.

## Clean-root release closure after task 24

Final reviewers found and the implementation closed these additional P2 gaps:

1. Publication ancestry still reached removed private company metadata; the
   candidate is now one root commit with no parent.
2. Legacy and compact AI protocols had ambiguous disclosure language; policy
   now names their different payload boundaries.
3. Committed privacy checks reconstructed maintainer identifiers, and the gate
   overwrote the tracked Dashboard before scanning; real markers are now
   injected externally, scanning happens first, and a temp build must match the
   tracked artifact byte-for-byte.
4. PID-file readers raced file creation against content flush; the race has a
   regression test and all PID assertions wait for parseable content.
5. A copyright-shaped LICENSE line could bypass blocked-marker checks; allowed
   exceptions are now injected and matched by exact relative path plus exact
   complete line.
6. The first hosted run exposed a Playwright fixture launcher hard-coded to a
   local `.venv`; it now selects injected, local-venv, or hosted Python and
   supplies the repository root through `PYTHONPATH`.

The clean-root release gate then passed: workflow smoke `1 passed`, Python
`291 passed, 1 skipped`, Chromium `3 passed`, Worker `31 passed`, dependency
audits, typecheck, Wrangler dry-run, Gitleaks, tracked privacy, reproducible
Dashboard comparison, and diff checks. Remote publication and hosted CI remain
separate release actions.
