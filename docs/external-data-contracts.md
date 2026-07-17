# External data contracts

Only contract version 1 is implemented. Unknown versions and extra fields fail
validation instead of being silently accepted.

## Compact `review` pipeline

Each fast or strong review request contains exactly:

- `contract_version`
- `stable_id`
- `title`
- `company`
- `country`
- `local_fit`
- `jd_evidence`

The pipeline truncates bounded JD evidence before invoking the configured
provider. Not sent: `full_jd`. Not sent: `resume contents`. Not sent:
`application_history`. Not sent: `interview notes`. Not sent: `job url`. The
local cache inputs `jd_hash` and `profile_rubric_hash` are not sent. Not sent:
`local summary`. Not sent: `local risk`. `jd_evidence` is built only from explicit
public posting evidence plus public location and source-provenanced
`public_skills`; the ordinary `skills` field is excluded because local scoring
may derive it from the profile. Evidence never includes locally derived company
preferences, must-have rules, visa preferences, or other scoring explanations.

Responses contain exactly `contract_version`, `stable_id`, `decision`, `score`,
`reason_codes`, and `summary`. See the request and response schemas in
[`schemas/`](schemas/).

The installed CLI accepts the compact provider as an explicit external command:

```text
job-radar review ... --provider-command <executable> [arguments...]
job-radar run ... --provider-command <executable> [arguments...]
```

`--provider-command` must be the final Job Radar option. Each invocation
receives one request object on stdin and returns one response object on stdout.
The adapter uses no shell, incrementally bounds both stdout and stderr to 1 MiB,
and terminates the complete provider process tree immediately when either
stream overflows or the configured per-call timeout expires. Both standalone
`review` and integrated `run` separately enforce the total review deadline
around the complete configured runner.

## Legacy `--ai-command`

The legacy scoring command receives a larger stdin JSON payload. Its
configuration fields are `profile.skills`, `preferences.countries`,
`preferences.roles`, `preferences.tracks`, `preferences.visa_required`,
`companies.preferred`, `companies.excluded`, `matching.minimum_score`,
`matching.must_have`, and `matching.exclude_keywords`, plus `jobs`.

Each item in `jobs` includes source, external ID, company, title, location, job
URL, publication date, country, category, salary, tracks, skills, first-seen
date, and visa-support state. Use the compact `review` pipeline when minimizing
provider data is the priority. The legacy process boundary nevertheless uses
the same isolated process group, streaming stdout/stderr limits, timeout, and
descendant cleanup as compact review.

## Optional Cloudflare status sync

The POST body contains exactly `contract_version`, `statuses`, and
`legacy_keys`. `statuses` maps each stable job ID to a status value:
`interested`, `applied`, `skip`, or `dead`. `legacy_keys` lists obsolete keys
that the Worker removes before merging the new statuses.

GET returns `contract_version` and `statuses`; DELETE removes the single
operator-owned document. The Worker deliberately does not accept applications,
events, resume data, interview notes, job descriptions, or review cache data.

Cloudflare is a third party when this optional template is enabled. The
operator is responsible for provider retention, training, sharing, deletion,
credentials, disclosure, and applicable law. This documentation is not legal
advice.
