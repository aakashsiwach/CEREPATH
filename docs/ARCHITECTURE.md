# Architecture

## Product intent

Cerepath is a local-first personal intelligence platform. Each installation represents a user's explicitly approved identity and working preferences while using a configured model and external knowledge to extend capability. It does not reproduce consciousness or claim infallibility.

## Core design principles

- **Device-independent:** the PWA is a control surface; state and execution belong to backend services.
- **Model-independent:** providers are adapters, not the system's source of truth.
- **Memory with provenance:** retained facts have owner approval and should carry source, timestamp and confidence.
- **Explicit consent:** persistent memory changes and external side effects require owner approval.
- **Read-only by default:** external tools begin with the smallest possible permissions.
- **Verifiable execution:** an action is not marked successful until evidence is captured.
- **Cost ceiling:** use only the configured provider; never silently switch to another or paid service.
- **Recoverable:** memory and task state should be exportable and restorable.
- **Multi-user safety:** private memories and credentials must remain isolated.

## Runtime services

```text
Phone / Laptop / Desktop
          |
       Cerepath PWA
          |
       Nginx proxy
          |
      FastAPI gateway ------------------ Browser agent (Playwright)
          |                                      |
    PostgreSQL + pgvector                  HTTPS GET only
          |                                      |
 Conversations / memories / approvals        Egress proxy
          |                                      |
   OpenAI-compatible provider          DNS validation + IP pinning
  (Bynara, Gemini or local Ollama)                  |
          |                                  Public Internet
```

The API and database have no direct outbound route. Bynara and Gemini calls use the CONNECT-only egress proxy on HTTPS port 443. Ollama can be reached through the Docker host gateway and does not use the public proxy. The browser uses the same restricted proxy for public HTTPS navigation.

## Frontend

React + TypeScript + Vite + a minimal PWA manifest/service worker. The local starter exchanges the owner bootstrap credential for a random, opaque server-side session. The session cookie is HTTP-only, SameSite=Strict, time-limited and revocable. State-changing cookie-authenticated requests require a CSRF token. The bootstrap flow is local-only; production identity must use reviewed OIDC/passkey authentication and account provisioning.

The chat interface lists saved owner conversations, loads message history and creates a new conversation when the user starts a chat without selecting an existing conversation. Provider credentials never reach the browser.

## Backend

FastAPI authenticates the owner, scopes conversation and memory queries by user ID, validates proposed memory operations, stores approvals, applies approved memory changes transactionally and writes audit events.

The intelligence layer exposes a small provider protocol and a shared OpenAI-compatible adapter. Supported hosted providers are Bynara and Google's Gemini Developer API; optional Ollama targets a local OpenAI-compatible endpoint. Gemini uses Google's documented `/v1beta/openai/chat/completions` compatibility path and Bearer API-key authentication. Only one provider is selected per API process; no automatic fallback is performed. Provider keys are read from the server environment and are not stored in PostgreSQL.

Chat requests store the user message before calling the provider, then persist the assistant reply and provider/model metadata. Failed provider calls leave a failed user-message record rather than silently losing the prompt. The model receives a bounded recent conversation. Approved memories are retrieved only for local Ollama by default; hosted-provider memory sharing requires the explicit `REMOTE_PROVIDER_MEMORY_SHARING=true` setting and includes only lexically matching approved memories. There is no unrelated-recent-memory fallback. Owner knowledge and imported documents use PostgreSQL full-text retrieval. When `EMBEDDING_PROVIDER=ollama`, the API calls the local Ollama `/api/embed` endpoint and stores 384-dimensional `all-minilm` vectors in pgvector. Vector and lexical candidates are combined through the attention controller. Embedding outages fall back to full-text retrieval, never to a hosted embedding service.

## Database

PostgreSQL is the source of truth. User, session and migration tables establish identity and revocable authentication. Memories, approvals, audit events, chat conversations and chat messages carry non-null user ownership. A composite foreign key ties each message to a conversation belonging to the same user. `pgvector` is enabled for future semantic retrieval, but embeddings are not generated in this starter.

## Browser and egress proxy

The browser service creates a disposable Chromium context for each navigation. It accepts HTTPS URLs on port 443 only; browser routing aborts non-GET requests. Chromium runs as an unprivileged user with its sandbox enabled, a read-only container filesystem, dropped capabilities and a seccomp profile.

The CONNECT-only proxy resolves the hostname, rejects the entire DNS answer set if any address is non-global, and opens the TCP connection to a validated IP address. This reduces DNS-rebinding/SSRF exposure. It does not inspect encrypted HTTP payloads. Browser request interception remains an additional policy layer, not a guarantee against a compromised browser.

## Digital Mind cognitive architecture

The cognitive kernel is an explicit software architecture inspired by selected neuroscience and cognitive-science models. It is not a biological brain simulation or consciousness claim.

| Cognitive subsystem | Implementation |
|---|---|
| Working memory | `BaddeleyWorkingMemory` bounds recent dialogue by item and character budgets |
| Episodic encoding | `HippocampalIndexer` computes a normalized-content trace hash and preserves lesson provenance |
| Semantic memory | Owner-taught concepts live in the owner-scoped `semantic_knowledge` table |
| Selective attention / executive control | `PrefrontalCognitiveController` ranks goal-relevant knowledge |
| Metacognitive monitoring | `MetacognitiveMonitor` exposes local retrieval coverage, not answer truth |
| Feedback / reward-prediction-error analogy | `RewardPredictionError` records explicit owner feedback; incorrect records move to review |
| Integration | `DigitalMind` builds the cognitive context used by the chat pipeline |

The owner explicitly teaches knowledge through `POST /api/mind/teach`. Documents can be imported through `POST /api/mind/documents`; originals are stored as bytes in PostgreSQL and extracted text is split into overlapping page-aware chunks. Source IDs, page numbers and filenames flow through retrieval for citation. Concepts and relations use separate owner-scoped tables and require owner confirmation. Chat uses local full-text retrieval plus the attention controller when the configured provider is local, or when `REMOTE_PROVIDER_MEMORY_SHARING=true`. This preserves the existing privacy default: hosted Gemini/Bynara providers do not receive approved memories or semantic knowledge unless the owner explicitly opts in. Conversation prompts and bounded chat history are still sent to a hosted provider when one is configured.

The hippocampal/neocortical complementary-learning-systems theory motivates separating experience traces from durable semantic knowledge. The current implementation does not perform neural replay, sleep, biological consolidation or automatic concept extraction. See [Neuroscience Foundations](NEUROSCIENCE_FOUNDATIONS.md) for the evidence map, selected literature and scientific boundaries.

## Intelligence roadmap

1. Improve retrieval with locally generated embeddings and hybrid ranking.
2. Add streaming responses and conversation controls.
3. Add fast/deep routing only after baseline provider behavior is measurable.
4. Add bounded tools and agent roles with explicit permissions.
5. Add verifiers and regression evaluation datasets.
6. Store durable knowledge only through an owner-approved memory operation.

Multiple agents should not be invoked for every request. Model routing must account for latency, privacy, context limits and cost.

## Deployment posture

This bundle is local-only and single-owner. OIDC/passkeys, account recovery, multi-user registration and database row-level security remain future work. The web UI binds to `127.0.0.1:5173`. The API, database, browser and proxy ports are not published. Do not expose this starter publicly before threat-model review, backup/restore testing and independent security validation.
