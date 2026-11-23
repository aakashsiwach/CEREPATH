# Roadmap

## Milestone 0 — Safe local foundation

- [x] React PWA shell
- [x] FastAPI control plane
- [x] PostgreSQL + pgvector schema
- [x] Exact-action memory approvals
- [x] Audit events
- [x] Separate read-only Playwright browser service
- [x] HTTPS-only browser navigation and GET interception
- [x] Isolated CONNECT egress proxy with DNS validation and IP pinning
- [x] Non-root browser container, sandbox, read-only filesystem and seccomp
- [x] No cloud provisioning or external AI calls

## Milestone 0.1 — Community foundation (this branch)

- [x] CEREPATH branding
- [x] Apache-2.0 license and NOTICE
- [x] Community contribution and conduct files
- [x] Issue and pull-request templates
- [x] CI for Python tests, frontend build and container builds
- [x] Browser egress separation and policy tests
- [ ] Production identity system
- [ ] Full integration tests against PostgreSQL
- [ ] Host-level egress firewall verification

## Milestone 1 — User identity and durable memory

The first PR establishes a local single-owner identity/session substrate. It does not enable public multi-user registration or production identity.

- [x] Single local owner identity and revocable HTTP-only sessions
- [x] CSRF protection for cookie-authenticated writes
- [x] User ownership columns and application-level query scoping
- [x] PostgreSQL migration integration test with existing-record backfill and repeatability checks
- [ ] Passkeys/OIDC, account provisioning and device/session management UI
- [ ] PostgreSQL row-level security and multi-user tenant-isolation integration tests
- [ ] User profile and editable identity model
- [ ] Document import with explicit consent
- [ ] Provenance and confidence review UI
- [ ] Memory export, encrypted backup and restore drills
- [ ] Semantic embeddings (local model first) and hybrid retrieval

## Milestone 2 — Intelligence orchestration

- [ ] Provider adapter interface
- [ ] Local-model adapter and capability/latency benchmarks
- [ ] Optional external model adapter, disabled by default
- [ ] Fast/deep task routing
- [ ] Bounded specialist roles and verifier
- [ ] Token, compute and free-quota budget enforcement
- [ ] No automatic provider fallback that can incur charges

## Milestone 3 — Browser agent

- [ ] Persistent isolated browser sessions
- [ ] Visible activity stream and screenshots
- [ ] Page text extraction with prompt-injection isolation
- [ ] Hardened egress proxy and network verification
- [ ] Read-only browser regression suite
- [ ] Click/type/form actions disabled until action-level approvals are implemented and tested

## Milestone 4 — Skill Forge and Research Lab

- [ ] Versioned skills with preconditions and postconditions
- [ ] Sandboxed experiments
- [ ] Evaluation datasets and regression harness
- [ ] Skill proposal and owner approval
- [ ] Evidence-backed skill promotion and rollback

## Milestone 5 — Controlled autonomy

- [ ] Task graph and resumable checkpoints
- [ ] Narrow per-tool permissions
- [ ] One-action, one-payload approval records
- [ ] Emergency stop and credential revocation
- [ ] Independent security review before any broad autonomy

## Release gates

A milestone is not complete because a demo looks good. It needs automated tests, documented limitations, rollback/recovery instructions and a security review proportionate to its privileges.
