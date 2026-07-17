# Security and responsibility notes

- Authentication fails closed when the Bearer secret or Durable Object binding
  is absent.
- The Worker uses a fixed single developer owner key and does not trust a
  client-provided identity.
- Responses use `Cache-Control: private, no-store`; CORS is closed by default.
- Errors are fixed codes and do not return secrets, internal exceptions, or
  stack traces.
- POST accepts at most 64 KiB and 500 bounded status items. The SQLite-backed
  Durable Object also rejects a merge that would store more than 500 statuses.
  Consider Cloudflare rate limiting and abuse monitoring before exposing a
  public route.
- `DELETE /v1/statuses` is the explicit data deletion path. Retention,
  third-party sharing, backup removal, and account deletion remain the
  operator's responsibility.
- One fixed-owner Durable Object serializes concurrent device merges and stores
  state in SQLite. It prevents unrelated updates from being silently lost, but
  it is not shared-tenancy conflict resolution. Do not use this template for
  payments, authorization decisions, or multi-user state.
- Finding this template does not grant authorization to synchronize another
  person's data. Operators remain responsible for privacy disclosure, terms,
  applicable law, and independent legal review; this documentation is not
  legal advice.
