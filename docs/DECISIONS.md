# Architecture decision records

## ADR-001: Local-first starter before cloud deployment

**Decision:** The first bundle runs locally in Docker Compose. No cloud provisioning scripts are included.

**Reason:** Validate behavior, memory approvals, browser isolation and resource use before selecting a permanent hosting path. Avoid accidental charges and avoid tying the design to one provider's free-tier conditions.

## ADR-002: PostgreSQL + pgvector as the initial source of truth

**Decision:** Use one PostgreSQL service with the vector extension rather than introducing separate managed database, cache and vector services.

**Reason:** Fewer moving parts and straightforward export/restore. Embeddings are a future capability; the starter stores no generated vectors.

## ADR-003: Read-only browser in milestone 0

**Decision:** Browser service only permits public HTTP(S) GET navigation and screenshots.

**Reason:** Browser interactions can trigger external side effects. Click/type/submit is postponed until exact-action approvals, egress controls and replay protection are independently tested.

## ADR-004: No model-provider dependency in milestone 0

**Decision:** Chat is a local placeholder. No model API adapter is configured or called.

**Reason:** Confirm the product/security foundation first; preserve a ₹0 target and avoid data disclosure or unexpected billing. Add model adapters later behind an explicit budget and privacy policy.

## ADR-005: Persistent memory writes require approval

**Decision:** Memory add/update/delete are stored as proposals; approved changes are executed transactionally.

**Reason:** The owner's explicit permission policy must be enforced in backend code, not only in model prompts or frontend conventions.


## ADR-006: Isolated browser egress

**Decision:** The browser container is attached only to an internal control network. A separate non-root CONNECT proxy is the only service attached to an outbound network. The proxy accepts TLS tunnels to port 443, validates all resolved IP addresses and connects to a pinned public IP. The browser runs as the Playwright `pwuser` with sandboxing, seccomp, dropped capabilities and a read-only filesystem.

**Reason:** Application-level URL checks alone are not sufficient against DNS rebinding or browser compromise. Network separation and IP pinning add independent defense-in-depth layers. The proxy does not inspect encrypted HTTP methods; the browser's request interception remains an additional read-only policy control, not a production guarantee.
