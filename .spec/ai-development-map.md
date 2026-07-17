# integrate-job-tracker AI development map

## Human-approved scope

- `.spec/current.md`
- `.spec/tasks.md`
- Publication branch: `codex/publish-job-radar-starter`

## Implementation provenance

Tasks were developed with RED tests before implementation. The publication
branch intentionally squashes those private development checkpoints into one
reviewable commit over `origin/main`. Reproducible commands, observed results,
and acceptance mappings remain in `.spec/tasks.md` and
`.spec/verify-state.json`; development-only commit IDs are not publication
evidence because they are not ancestors of the squash branch.

## Independent verification

- Main agent reran focused and full tests after each task.
- Main agent independently ran `scripts/verify-public-release.ps1` after task 9.
- Dashboard screenshots were visually inspected at desktop and 390 px mobile.
- Three read-only reviewers audited spec/integration, security/privacy/legal
  boundaries, and performance/operability.

## Review decision boundary

All previously accepted remediation tasks are represented in the clean
publication squash. There are currently no known unaccepted P1/P2 findings in
that prepared content; final clean-branch re-review and hosted PR checks remain
required before merge. A local green receipt is not proof that GitHub-hosted CI
has passed, and no merge, production deployment, repository archive, pin
change, or public metadata change is recorded here.

The publication commit must use the GitHub noreply author address. Author
metadata already present on `origin/main` is pre-existing public history and is
outside this branch patch's privacy boundary. The branch patch and its reachable
content still require the tracked privacy scan, Gitleaks history scan, and final
review before push or merge.
