# Public release audit

## Data boundary

Public code may contain source metadata, example configuration, and documented API adapters. User resumes, preferences, company priorities, application history, scan output, credentials, and tokens live under gitignored `user-data/` or environment variables.

## Source policy

Built-in adapters require a documented API, government open-data endpoint, or authorized feed. Undocumented endpoints and services whose terms prohibit automated collection are excluded even if a third-party GitHub scraper exists.

## Verification evidence

- The clean publication candidate is one root commit with no parent. It does
  not inherit the old public `main` history.
- `scripts/verify-public-release.ps1` passed on that root snapshot: workflow
  smoke `1 passed`; Python `291 passed, 1 skipped`; Chromium `3 passed`; Worker
  `31 passed`; typecheck, dependency audits, Wrangler dry-run, Gitleaks,
  tracked privacy, generated-artifact, and whitespace gates all passed.
- Privacy and Gitleaks inspect the committed tree before generation. Dashboard
  output is generated to a temporary file and must match the tracked artifact
  byte-for-byte; the gate does not overwrite reviewed evidence.
- Maintainer-specific privacy markers are injected from uncommitted input. The
  repository contains synthetic scanner markers only. Any exception is also
  injected and must exactly match `relative/path::complete line`.
- A clean virtual environment installed the package and the `job-radar`
  console entry point responded to `--help`.
- The tracked privacy scanner passed all publication files, and a Gitleaks
  history scan of the publication branch found no leaks.
- The clean-root publication candidate contains no removed private metadata in
  its reachable content or ancestry. The only allowed maintainer text is the
  exact LICENSE author line.
- The root publication commit uses the GitHub noreply author address and has no
  parent. Replacing the existing remote history remains an explicit,
  destructive release action and is not implied by local verification.

## Data behavior

- Retention: status remains in browser local storage until the user clears site data or replaces it.
- Sharing: the generated page sends no applicant or status data to a third party.
- Export: status leaves the browser only when the user presses `Export status`; exported files are user-controlled.
- Deletion: clearing browser site data deletes local status. Exported copies must be deleted separately by the user.
- AI providers: legacy `score`/`run --ai-command` sends structured preferences
  and public job fields; compact `review --provider-command` sends bounded
  public posting evidence only. Neither sends `resume_path`, resume contents,
  prior notes, or application state. Any downstream provider retention,
  training, sharing, disclosure, and deletion remain the developer's
  responsibility.

## Remaining publication boundary

- `origin/main` still exposes its old history. Publishing the clean root
  requires an explicitly approved history replacement; a normal PR cannot
  remove those reachable objects.
- The clean-root candidate may be pushed as a separate branch for hosted
  checks. Confirm those checks against the exact final SHA and verify the
  remote object graph after any approved history replacement; local evidence
  does not substitute for hosted CI.
- Official API availability and terms can change and must be rechecked before
  expanding request volume.
