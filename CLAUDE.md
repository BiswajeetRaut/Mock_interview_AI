# Mock Interview AI — working context

Read this first in any new session. It's the continuity document for an
ongoing initiative, not general codebase docs — it exists so a fresh Claude
Code session (new device, new window, whatever) can pick up exactly where
the last one left off without re-deriving everything from scratch.

## What this project is

An AI mock-interview platform: React/Chakra frontend, FastAPI backend, a
LangGraph-orchestrated multi-agent interview pipeline (supervisor + code /
resume / HR agents), browser-side speech (STT/TTS never touch the server).
See `mock-interview-backend/` and `mock-interview-frontend/`.

## The three documents that actually matter — read these, don't ask me to re-derive them

Everything about the current architecture, the scaling plan, and the
execution backlog already exists as three detailed HTML docs in `docs/`.
**Read them before doing anything else.** Don't re-audit the codebase from
scratch or re-litigate decisions already made in them — extend them.

- **`docs/current-state-architecture.html`** — teardown of the pre-Phase-2
  system: every component, the LLM call chain per turn, load ceilings
  (threadpool/memory/provider quota math), and every blocking issue found.
- **`docs/phase-2-design.html`** — the actual design: 8 numbered decisions
  (D-01 through D-08) with rejected alternatives, target architecture
  diagrams for end-of-2A and end-of-2B, the three-tier agent memory design,
  the six-week roadmap, capacity math, risks, and a Phase 3 sketch. This is
  where **why** any infra choice was made lives.
- **`docs/phase-2-backlog.html`** — the actual worklist: 45 sized stories
  (`P2-1xx` through `P2-6xx`) across 6 epics, each with acceptance criteria,
  file paths, and dependencies. **This is the source of truth for what's
  done and what's next** — check it before starting or claiming a story.

These are published as Artifacts too (ask the user for the links if you
need to view them rendered rather than as raw HTML).

## Current status (update this section as work continues)

**Phase 2A, Epic 1 (Security lockdown) — in progress.**

Done: P2-101 (coding-runner kill switch), P2-102/103 (auth + session
ownership, done together), P2-104 (SSRF-safe resume fetching), P2-105
(CORS allowlist), P2-106 (Redis rate limiting). All committed and pushed to
`origin/main` as of commit `f2f2b2e`.

Remaining in Epic 1: **P2-107** (secrets out of repo/image), **P2-108**
(fail loudly on missing creds), **P2-109** (test suite — already
substantially seeded: 50 tests exist across `tests/test_cors.py`,
`tests/test_session_authz.py`, `tests/test_ssrf_guard.py`,
`tests/test_rate_limit.py`, built story-by-story rather than as one batch).

After Epic 1: Epic 2 (persistence — Postgres/Neon, kills the in-memory
session store), Epic 3 (delivery pipeline — Docker/CI/K8s), Epic 4
(observability + async), Epic 5 (cost/chain reduction), Epic 6 (load test).
Full detail in the backlog doc.

## Infra decisions already made (not yet built — these are commitments, not code yet)

- **K8s: GKE Autopilot.** Google manages node provisioning; strong support
  for the custom-metric HPA the capacity plan needs.
- **Postgres: Neon.** Atlas-like managed Postgres — pooled connection
  string, branching, pgvector for the agent-memory design. Outside GCP's
  VPC (accepted tradeoff at 2A scale).
- **Redis: GCP Memorystore**, not Redis Cloud — same VPC as GKE, chosen
  specifically because Redis is hit on every rate-limited request (unlike
  Postgres, hit once per turn), and becomes the Streams broker in 2B.

None of these are provisioned yet. Provisioning real cloud resources
(creating the GCP project, billing) is the user's action, not something to
do autonomously — surface the need, don't just go create accounts.

## How we work — conventions established this session, keep following them

- **Work the backlog one story at a time.** Don't jump ahead or batch
  multiple stories into one change unless they're tightly coupled enough
  that shipping one without the other leaves a broken intermediate state
  (that's why P2-102/103 were done together, and why P2-104/105/106 were
  each done separately).
- **Verify live, not just with unit tests, before calling a story done.**
  Every story so far has been proven end-to-end against the real running
  app — real HTTP requests, real Firebase tokens (minted via a real custom
  token + the real identitytoolkit REST API, not mocked), a real local
  redis-server, real attack payloads fired at the actual vulnerable
  endpoint. Mocked unit tests are the floor, not the ceiling — when
  something can be proven for real cheaply, prove it for real.
- **Flag scope creep honestly, don't silently absorb or silently skip it.**
  Multiple stories surfaced real bugs adjacent to the story's stated scope
  (e.g. P2-102 surfaced a `Header(...)` bug in `deps.py` and a genuine
  React race condition in `AuthContext.jsx` that the new route guard would
  have hit on every page reload). Fix them and say so explicitly, don't
  bundle them in silently or ignore them because they're "not the ticket."
- **Don't fix what a linter flags if the linter is wrong.** FastAPI's
  `Depends(...)` in argument defaults is the correct, idiomatic pattern —
  a generic linter flags it as a bug (function-call-in-default-arg); that's
  a false positive, not a real issue. Know the difference before "fixing"
  a lint warning.
- **Ask before git push, always.** Never commit or push without the user
  explicitly asking in that turn — a prior approval doesn't carry forward
  to the next push. When staging, check `git status`/diff for anything
  unrelated or sensitive before adding — don't blanket `git add -A`.
- **Respect existing project conventions even when they seem technically
  unnecessary.** `firebase.js` carries a Firebase *web* API key, which is
  technically safe to expose publicly (Firebase's own security model
  relies on Security Rules + backend token verification, not hiding this
  key) — but the project's own `.gitignore` explicitly excludes it twice,
  a clear pre-existing signal it was meant to stay uncommitted. Respected
  that instead of overriding it on a technicality.
- **Collaboration style**: the user is an SDE-2 on this project; treat
  discussion of tradeoffs as a principal-engineer-to-SDE-2 conversation —
  give a real recommendation with the honest tradeoff, not an exhaustive
  neutral menu, and call out disagreements or better alternatives directly
  rather than deferring by default.

## Local environment notes

- Backend venv: `mock-interview-backend/venv/` (also a `.venv/` exists —
  `venv/` is the one actually used; both are gitignored).
- Copy `mock-interview-backend/.env.example` → `.env` and fill in
  `GROQ_API_KEY` at minimum. Every var is documented inline with what
  happens if it's left unset.
- Run the backend test suite: `cd mock-interview-backend && ./venv/bin/python -m pytest tests/ -v`
  (50 tests as of the last commit). A subset in `tests/test_rate_limit.py`
  needs a real `redis-server` reachable on `localhost:6379` to run — they
  skip cleanly (not fail) if it's not running.
- Local Redis for testing: `brew install redis` (or reinstall equivalent on
  a non-Mac device), then `redis-server --daemonize yes --port 6379`.
- Frontend: standard `npm install` / `npm run dev` in `mock-interview-frontend/`.
- Backend dev server: `uvicorn main:app --port 8000` from
  `mock-interview-backend/` — the frontend's axios client is hardcoded to
  `http://127.0.0.1:8000` (`src/api/client.js`) until P2-302 fixes that.

## What did NOT come over from the previous device on purpose

- `.env` (real secrets — gitignored, recreate manually)
- `mock-interview-frontend/src/firebase.js`'s filled-in config (gitignored,
  pre-existing local-only change unrelated to Phase 2 work — recreate if
  you want it, or leave the committed empty-config version as-is)
- Anything running locally (redis-server, dev servers) — just needs
  restarting on the new machine, nothing persists across devices for these
