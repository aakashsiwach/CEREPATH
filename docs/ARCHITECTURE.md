# Architecture

## Product intent

Cerepath is an open-source, cloud-first personal intelligence platform. Each installation represents a user's explicitly approved identity and working preferences while using external knowledge and tools to extend capability. It does not reproduce consciousness or claim infallibility.

## Core design principles

- **Device-independent:** the PWA is a control surface; state and execution belong to backend services.
- **Model-independent:** reasoning providers are adapters, not the system's source of truth.
- **Memory with provenance:** every retained fact should have a source, timestamp and confidence.
- **Explicit consent:** adding, updating or deleting persistent information requires owner approval.
- **Read-only by default:** external tools begin with the smallest possible permissions.
- **Verifiable execution:** an action is not marked successful until evidence is captured.
- **Cost ceiling:** stop work when a free quota or local budget is exhausted; never silently switch to paid usage.
- **Recoverable:** memory and task state must be exportable and restorable.
- **Multi-user safety:** community features must not expose one user's private memories or credentials to another.

## Runtime services

```text
Phone / Laptop / Desktop
          |
       Cerepath PWA
          |
       Nginx proxy
          |
      FastAPI gateway ------------------ Browser agent (Playwright)
          |                                     |
    PostgreSQL + pgvector                  HTTPS GET only
          |                                     |
   Audit + approvals + memories             Egress proxy
                                                |
                                      DNS validation + IP pinning
                                                |
                                           Public Internet
```

Docker networks separate the database, control-plane and browser-egress paths. The browser has no direct outbound network; the egress proxy is the only service attached to the outbound network.

## Frontend

React + TypeScript + Vite + a minimal PWA manifest/service worker. The local starter stores the owner token in `sessionStorage` only. A production release must replace the static bearer token flow with passkeys/OIDC and short-lived server sessions.

## Backend

FastAPI is the control plane. It authenticates the owner, validates proposed operations, stores approval requests, applies approved memory changes transactionally and writes audit events. It does not contain model-provider credentials or call external model APIs in this milestone.

## Database

PostgreSQL is the source of truth. `pgvector` is enabled for future semantic retrieval, but embeddings are not generated in this starter. Memory content and metadata are stored with provenance. Approval requests and audit events are separate tables.

## Browser and egress proxy

The browser service creates a disposable Chromium context for each navigation. It accepts HTTPS URLs on port 443 only; browser routing aborts non-GET requests. Chromium runs as an unprivileged user with its sandbox enabled, a read-only container filesystem, dropped capabilities and a seccomp profile.

The browser container has no direct outbound network. Its only route to public websites is a CONNECT-only proxy. The proxy accepts TLS tunnels to port 443, resolves the hostname, rejects the entire DNS answer set if any address is non-global, and opens the TCP connection to a validated IP address. This reduces DNS-rebinding/SSRF exposure. It does not inspect encrypted HTTP payloads; browser request interception remains an additional policy layer, not a guarantee against a compromised browser.

## Intelligence design (future)

1. Retrieve verified memory and known skills.
2. Use a fast local model for routing, extraction or straightforward tasks where helpful.
3. Use optional external reasoning adapters only when configured and explicitly permitted.
4. Delegate independent read-only investigations in parallel only when this reduces latency.
5. Use a verifier to check claims, code, citations and task outcomes.
6. Store persistent knowledge only as a proposal awaiting owner approval.

Multiple agents should not be invoked for every request. Model routing must account for latency, privacy, context limits, free quota and task difficulty.

## Deployment posture

This bundle is local-only. The web UI binds to `127.0.0.1:5173`. The API, database, browser and proxy ports are not published. It contains no cloud provisioning scripts. Remote deployment is a later decision after threat-model review, backup/restore testing and provider free-tier validation.
