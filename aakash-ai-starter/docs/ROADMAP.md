# Roadmap

## Milestone 0 — Safe local foundation (this bundle)

- [x] React PWA shell
- [x] FastAPI control plane
- [x] PostgreSQL + pgvector schema
- [x] Exact-action memory approvals
- [x] Audit events
- [x] Separate read-only Playwright browser service
- [x] No cloud provisioning or external AI calls

## Milestone 1 — Owner identity and durable memory

- [ ] Passkeys/OIDC and device/session management
- [ ] Owner profile and editable identity model
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
- [ ] Explicit allowlists and hardened egress proxy
- [ ] Read-only browser regression suite
- [ ] Click/type/form actions disabled until action-level approval is implemented and tested

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
