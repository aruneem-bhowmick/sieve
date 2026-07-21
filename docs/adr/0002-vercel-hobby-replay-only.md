# ADR 0002 — Host only replay on Vercel Hobby

**Status:** Accepted

## Context

ADR 0001 described an optional Vercel service for private live audits. Vercel
Hobby is the only hosted runtime currently available, and it is not an
appropriate deployment target for the required durable worker, scheduled
cleanup, private storage, quota enforcement, and isolated execution. Shipping
any reduced live path would blur the boundary between recorded evidence and
untrusted execution.

## Decision

Supersede ADR 0001's Vercel-hosting consequence. The Vercel Hobby project is
static replay only: it builds the deterministic Vite artifact in `public/`,
excludes `api/`, and has no Vercel functions, cron jobs, storage integrations,
or live-service secrets. The browser may replay bundled 5×3 evidence and
locally edit, import, and export a five-task suite. It must not submit,
execute, queue, poll, or otherwise send the suite to an API; local edits never
alter recorded evidence.

GitHub Pages remains the canonical deterministic report. The existing `api/`
implementation, shared server contracts, and server-side tests remain in this
repository as deferred work and are not part of the Hobby deployment artifact.

## Consequences

A future live service needs a supported isolated backend before it can be
enabled. It must retain ADR 0001's security posture: server-only credentials,
private expiring reports, authenticated ownership, quotas and global locking,
bounded model requests, isolated sandbox execution, and no live call in CI.
No browser-execution substitute or Hobby secret configuration is authorized by
this decision.

## Alternatives considered

Keeping the prior live endpoints on Hobby is unsupported and risks exposing
incomplete controls. Running uploaded code in the browser cannot provide the
Python harness or protect a billable credential. Both alternatives are
rejected.
