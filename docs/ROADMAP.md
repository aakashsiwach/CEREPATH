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

## Milestone 0.1 — Community foundation

- [x] CEREPATH branding
- [x] Apache-2.0 license and NOTICE
- [x] Community contribution and conduct files
- [x] Issue and pull-request templates
- [x] CI for Python tests, frontend build and container builds
- [x] Browser egress separation and policy tests
- [ ] Host-level egress firewall verification

## Milestone 1 — Personal identity and durable memory

The first release remains local and single-owner.

- [x] Single local owner identity and revocable HTTP-only sessions
- [x] CSRF protection for cookie-authenticated writes
- [x] User ownership columns and application-level query scoping
- [x] PostgreSQL migration integration test with existing-record backfill and repeatability checks
- [x] Owner-scoped persistent chat conversations and messages
- [x] Conversation history list and reload in the UI
- [ ] Passkeys/OIDC, account provisioning and device/session management UI
- [ ] PostgreSQL row-level security and multi-user tenant-isolation integration tests
- [ ] User profile and editable identity model
- [x] Owner-initiated document import with original-file retention and source provenance
- [ ] Provenance and confidence review UI
- [ ] Memory export, encrypted backup and restore drills
- [x] Optional local Ollama embeddings and lexical/vector hybrid recall

## Milestone 1.1 — Digital Mind cognitive kernel

- [x] Bounded working memory inspired by Baddeley and Hitch
- [x] Episodic trace hashing and provenance inspired by hippocampal indexing / complementary learning systems
- [x] Owner-taught semantic knowledge with duplicate-aware reinforcement
- [x] Goal-directed selective attention and relevance ranking
- [x] Metacognitive retrieval-coverage reporting
- [x] Explicit owner feedback and reward-prediction-error metric
- [x] Incorrect knowledge quarantine and review status
- [x] Chat pipeline integration with local knowledge retrieval
- [x] Owner-scoped cognitive experience history
- [x] Episodic indexing of completed chat turns and cross-conversation recall
- [x] Owner-rated active recall with SM-2-inspired spaced review schedule
- [x] PDF, DOCX, PPTX, XLSX, TXT, Markdown, RST, CSV, JSON, XML, YAML and HTML ingestion with page/slide-aware chunking
- [x] Local all-minilm embeddings and pgvector hybrid retrieval
- [x] Owner-created concepts and provenance-backed typed relations
- [ ] Safe consolidation/replay jobs with provenance and rollback
- [ ] Predictive-processing experiments with measurable prediction-error tasks
- [ ] Learning/evaluation curriculum and regression benchmark
- [ ] Local language model packaging and offline capability checks

## Milestone 2 — Intelligence orchestration

- [x] Provider adapter interface
- [x] OpenAI-compatible hosted adapter for Bynara
- [x] Optional local Ollama-compatible adapter
- [x] Explicit environment-based provider selection and no automatic fallback
- [x] Persistent chat completion with bounded recent history
- [x] Bounded retrieval of approved memories into model context (lexical v1)
- [ ] Streaming responses
- [ ] Fast/deep task routing
- [ ] Bounded specialist roles and verifier
- [ ] Token, compute and free-quota budget enforcement
- [ ] No automatic provider fallback that can incur charges (policy is implemented; add budget controls)

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
