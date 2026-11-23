# Architecture

## Product intent

Aakash AI is a cloud-first personal intelligence platform that represents the owner's identity and working preferences while using external knowledge and tools to extend capability. It is not intended to reproduce consciousness or claim infallibility.

## Core design principles

- **Device-independent:** the PWA is a control surface; state and execution belong to backend services.
- **Model-independent:** reasoning providers are adapters, not the system's source of truth.
- **Memory with provenance:** every retained fact should have a source, timestamp and confidence.
- **Explicit consent:** adding, updating or deleting persistent information requires owner approval.
- **Read-only by default:** external tools begin with the smallest possible permissions.
- **Verifiable execution:** an action is not marked successful until evidence is captured.
- **Cost ceiling:** the system must stop work when a free quota or local budget is exhausted; never silently switch to paid usage.
- **Recoverable:** memory and task state must be exportable and restorable.

## Runtime services

```text
Phone / Laptop / Desktop
          |
      React PWA
          |
      Nginx proxy
          |
     FastAPI gateway ------------------ Browser agent (Playwright)
          |                                    |
     PostgreSQL + pgvector                 Public HTTP(S) only
          |
     Audit + approvals + memories
```

### Frontend

React + TypeScript + Vite + a minimal PWA manifest/service worker. The browser stores the owner token in `sessionStorage` only. A production release should replace the single static bearer token flow with passkeys/OIDC and short-lived server sessions.

### Backend

FastAPI is the control plane. It authenticates the owner, validates proposed operations, stores approval requests, applies approved memory changes transactionally and writes audit events. It does not contain model-provider credentials or call external model APIs in this milestone.

### Database

PostgreSQL is the source of truth. `pgvector` is enabled for future semantic retrieval, but embeddings are not generated in this starter. Memory content and metadata are stored with provenance. Approval requests and audit events are separate tables.

### Browser agent

A separate Playwright service has its own internal bearer token. It creates a disposable Chromium context for each navigation. Only public HTTP(S) destinations and GET requests are permitted. It does not preserve cookies, accept credentials, click, type or submit forms. DNS and request routing are checked to reduce server-side request forgery risks.

## Intelligence design (future)

The orchestration layer should choose the smallest sufficient path:

1. Retrieve verified memory and known skills.
2. Use a fast local model for routing, extraction or straightforward tasks where helpful.
3. Use an optional external reasoning adapter only when configured and explicitly permitted by the owner.
4. Delegate independent read-only investigations in parallel when doing so reduces latency.
5. Use a verifier to check claims, code, citations and task outcomes.
6. Store new persistent knowledge only as a proposal awaiting owner approval.

Multiple agents should not be invoked for every request. Model routing must account for latency, privacy, context limits, free quota and task difficulty.

## Deployment posture

This bundle is local-only. `docker-compose.yml` binds the web UI to `127.0.0.1:5173`; backend and browser ports are not published. It contains no cloud provisioning scripts. Remote deployment is a later decision after threat-model review, backup/restore testing and provider free-tier validation.
