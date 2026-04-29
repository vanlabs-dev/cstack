# Security policy

## Reporting

If you discover a security issue in cstack, please email
[leunis@vanlabs.dev](mailto:leunis@vanlabs.dev) rather than opening a
public issue. Include reproduction steps, the affected commit hash,
and any logs or output that help reproduce the issue.

You should expect an acknowledgement within five working days.

## Scope

cstack is currently V0.6 alpha software running against synthetic
fixtures only. It is not deployed to production environments and has
no public-facing surface. Security disclosure expectations track that
posture: the bar for "exploitable" is whatever an attacker with local
filesystem access could achieve against a developer machine running
cstack.

When the project enters Sprint 7 (live tenant integration) and gains a
production posture, this scope will expand and a published responsible
disclosure timeline will replace this note.

## Out of scope

- Vulnerabilities in upstream dependencies (Microsoft Graph SDK,
  scikit-learn, FastAPI, Next.js, Anthropic/OpenAI SDKs). Report those
  to the respective upstream projects.
- Findings from running cstack against production tenants without
  written authorisation from the tenant owner. cstack's certificate
  auth path requires explicit tenant admin enrolment; doing so without
  authorisation is unauthorised access regardless of cstack's role.
- Reports about the absence of features (no rate limiting on the dev
  API key, no automatic key revoke API). These are tracked in
  [docs/BACKLOG.md](./docs/BACKLOG.md) and are not security issues at
  the current project posture.
