# Source policy

## Built-in sources

Job Radar Starter only bundles adapters for documented public job-board endpoints:

- Greenhouse Job Board API
- Lever Postings API
- Ashby public job posting API

Their documentation links live beside the source definitions in `catalog/sources.yaml`. An endpoint being public does not remove its rate limits or terms; maintainers and users must re-check those terms when behavior changes.

## Multi-channel integration policy

The public edition supports multiple discovery channels, but each channel needs its own adapter boundary:

| Channel | Public-edition mode | Boundary |
|---|---|---|
| Greenhouse, Lever, Ashby, or another documented ATS API | Built-in automated scan | Use the documented endpoint, identify the client, bound response size and request frequency, and link back to the employer post. |
| Employer career page or authorized feed | Adapter after verification | Require documented permission, a feed contract, or an employer-owned public endpoint. |
| Web search | Link discovery through an authorized search API | Store the employer/ATS destination URL; do not scrape or republish a search result page, and follow API quota, attribution, retention, and caching terms. |
| 104, LinkedIn, Indeed, or Google Jobs | Manual URL/JSON import or official connector/API | Do not automate login, reuse session cookies, bypass controls, or bundle an unofficial scraper. |
| Developer-owned files | Local JSON import | Keep personal notes, status, and preferences in gitignored local storage. |

This is why the architecture does not use one universal crawler. A normalized `Job` contract can combine the results, while each source adapter retains its own authorization, request, and data-use rules.

## Sources excluded from the public edition

The repository does not bundle or recommend automated access to LinkedIn, Indeed, Google Jobs, or 104. Their absence is intentional: permission for the private workflow's access methods has not been established for a reusable public tool.

A third-party GitHub scraper does not grant permission to access the underlying service. Users who add adapters are responsible for obtaining authorization, respecting robots and service terms where applicable, limiting request volume, and complying with local law.

This repository's source list is a technical allowlist, not a legal conclusion. Public availability of an endpoint does not guarantee that every jurisdiction, use case, request rate, or downstream republication is permitted. Operators must re-check current terms and obtain legal advice when their risk requires it.

## Applicant data

Built-in adapters fetch public job-posting data only. They do not submit applications or send resume, identity, salary, interview, or tracking data to employers or job boards.

The optional AI-command protocol excludes the resume path, resume contents, prior summaries, risks, and application state. It does send structured skills, preferences, company boundaries, and public job data to the developer-selected executable. If that executable calls a third party, the developer is responsible for disclosure, retention, sharing, training-use, and deletion behavior at that provider.

The generated dashboard stores tracking status in browser local storage. Export occurs only when the user presses **Export status**. Deleting the browser's site data deletes the locally stored state; exported files remain under the user's control.

## Accuracy and affiliation

AI scores and explanations are decision aids, not facts. Verify job status, location, compensation, work authorization, and application requirements on the official posting.

Job Radar Starter is independent and is not affiliated with or endorsed by any ATS provider, job board, employer, or government agency.

The software and generated scores are provided under the MIT License without warranty. This source policy describes project boundaries and is not legal advice.
