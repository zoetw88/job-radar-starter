# ADR: External AI scoring uses a shell-free JSON process boundary

Status: Accepted — 2026-07-15

## Context

The public single-developer edition needs optional AI scoring without choosing a model vendor, embedding credentials, uploading a resume automatically, or coupling the core package to an AI SDK.

## Decision

Launch a developer-selected executable directly, without a shell. Send one versioned JSON request on stdin and accept one validated JSON response on stdout.

The request contains structured preferences and public job fields. It excludes `resume_path`, resume contents, prior summaries, risks, and application state. Job identity, allowed fields, types, and score range are validated before output changes. Explicit local company and keyword exclusions cannot be overridden by AI output.

## Consequences

- The repository remains provider-neutral and stores no AI credentials.
- Developers can connect a local model or a hosted provider through code they control.
- Hosted-provider retention, training, sharing, disclosure, and deletion remain the developer's responsibility.
- AI command failures stop the run instead of silently publishing unreviewed or partial scoring.
