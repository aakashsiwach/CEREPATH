# Cerepath

**Intelligence, built together.**

Cerepath is a local-first personal intelligence workspace with a neuroscience-informed **Digital Mind cognitive kernel**. It separates owner-taught semantic knowledge and experience records from the language model, uses bounded working memory and goal-directed attention, and records owner feedback for review. The selected LLM is a replaceable language/reasoning interface, not the source of Cerepath's identity or durable knowledge.

> **Status: early development.** This is a personal, single-owner local application—not a biological brain, conscious system, finished autonomous agent or public multi-user service. The first cognitive kernel is an explicit, testable software architecture inspired by cognitive-science models. It does not reproduce neural tissue, subjective experience or human intelligence.

## Implemented

- React + TypeScript PWA with local owner sign-in.
- FastAPI backend and PostgreSQL/pgvector.
- Revocable HTTP-only sessions and CSRF protection.
- Owner-scoped persistent conversations and messages.
- OpenAI-compatible Bynara adapter.
- OpenAI-compatible Google Gemini Developer API adapter.
- Optional local Ollama through its OpenAI-compatible API.
- Neuroscience-informed cognitive kernel: bounded working memory, episodic trace indexing, owner-taught semantic knowledge, deterministic attention ranking, retrieval evidence monitoring and owner feedback signals.
- Owner-scoped cognitive experiences and semantic knowledge stored in PostgreSQL.
- Hybrid knowledge recall combines PostgreSQL full-text search with optional local Ollama embeddings and pgvector.
- Explicit feedback can move incorrect owner-taught knowledge to a review queue; repeated teaching of identical normalized content reinforces one record rather than duplicating it.
- Owner document ingestion for PDF, DOCX, PPTX, XLSX, TXT, Markdown, RST, CSV, JSON, XML, YAML and HTML. Original bytes remain in PostgreSQL, with extracted text, overlapping chunks, SHA-256 deduplication and PDF page provenance.
- Optional local Ollama embeddings (`all-minilm`, 384 dimensions) for semantic recall; PostgreSQL full-text recall remains available when embeddings are disabled or unavailable.
- Owner-managed concept graph with explicit, source-linked relationships; no automatic model-invented edges.
- Approved-memory retrieval for chat context (bounded lexical matching in this version).
- Hosted providers receive no approved memories, semantic knowledge, document passages or episodic history by default; relevant local context is shared only with explicit server-side opt-in. Local Ollama can retrieve it without the remote-sharing opt-in.
- No automatic provider fallback; a missing or failing provider returns an explicit error.
- Memory add/update/delete still require your approval.
- Read-only Playwright browser, HTTPS-only navigation and CONNECT egress proxy with DNS validation/IP pinning.

## AI provider configuration

The API key belongs in the server-side `.env` file only. Never paste it into frontend code, chat, an issue, or a commit.

Select exactly one provider with `AI_PROVIDER`: `bynara`, `gemini`, `ollama`, or `disabled`. The application never silently falls back to another service.

Approved memories stay local when using hosted providers unless you explicitly opt in:

```dotenv
REMOTE_PROVIDER_MEMORY_SHARING=false
```

Set this to `true` only when you accept sending matching approved memories to the selected hosted provider. The application never falls back to unrelated recent memories. This setting controls approved-memory context only; your current prompt and bounded conversation history are still sent to the selected provider. Local Ollama can use matching approved memories without this remote-sharing opt-in.

### Google Gemini Developer API

Create a key in [Google AI Studio](https://aistudio.google.com/apikey), then set:

```dotenv
AI_PROVIDER=gemini
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
GEMINI_MODEL=gemini-3.6-flash
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
AI_HTTP_PROXY=http://egress-proxy:3128
```

Cerepath uses Google's documented OpenAI-compatible Chat Completions endpoint at `/v1beta/openai/chat/completions` and sends the key as a Bearer token. The API container routes Gemini HTTPS requests through the restricted CONNECT egress proxy.

The Gemini Developer API free tier offers free input/output tokens for selected models, subject to model access and rate limits. Free-tier content may be used by Google to improve its products. Cerepath keeps approved memories and all other local knowledge (semantic lessons, document passages and episodic history) out of hosted Gemini requests by default; enabling `REMOTE_PROVIDER_MEMORY_SHARING=true` opts into relevant, bounded local context. Your prompt and bounded conversation history are still sent. Do not send confidential information, credentials or sensitive personal data through a free-tier Gemini key. Review Google's current [pricing](https://ai.google.dev/gemini-api/docs/pricing) and [terms](https://ai.google.dev/gemini-api/terms) before enabling it. Paid-tier data handling differs; verify the terms for your actual account tier.

### Bynara

Set these values in `.env`:

```dotenv
AI_PROVIDER=bynara
BYNARA_BASE_URL=https://router.bynara.id/v1
BYNARA_MODEL=gpt-5.6-luna
BYNARA_API_KEY=YOUR_BYNARA_API_KEY
AI_HTTP_PROXY=http://egress-proxy:3128
```

The API sends OpenAI-compatible chat completion requests to `/chat/completions`. The backend routes Bynara traffic through the existing HTTPS CONNECT egress proxy; it does not receive unrestricted outbound internet access.

### Local Ollama

For local model execution, install Ollama on the host, pull a model, and set:

```bash
ollama pull qwen2.5:7b
```

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODEL=qwen2.5:7b
AI_HTTP_PROXY=
```

The API container maps `host.docker.internal` to the host gateway for Docker Engine on Linux. Ollama requests bypass the public egress proxy and target the local host runtime.

### Local document embeddings

Document ingestion works with full-text search even if no embedding model is installed. For semantic vector search, run Ollama on the host and install the 384-dimensional embedding model:

```bash
ollama pull all-minilm
```

Then set these values in `.env`:

```dotenv
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_BASE_URL=http://host.docker.internal:11434
OLLAMA_EMBEDDING_MODEL=all-minilm
```

Embedding requests go directly to the local Ollama host and do not use Gemini, Bynara or a hosted embedding API. Keep `REMOTE_PROVIDER_MEMORY_SHARING=false` to prevent approved memories, semantic knowledge, document passages and episodic memories from being added to hosted model prompts. With sharing disabled, hosted LLMs still receive the current prompt and bounded conversation history, but not local knowledge records.

Supported document types are PDF, DOCX, PPTX, XLSX, TXT, Markdown, RST, CSV, JSON, XML, YAML and HTML. Scanned PDFs without selectable text need OCR and are rejected rather than silently indexed as empty. Each upload is limited to 20 MiB and one million extracted characters. The original file, extracted text and chunk provenance are retained in PostgreSQL; duplicate files are detected by SHA-256.

### Disable model calls

```dotenv
AI_PROVIDER=disabled
```

There is no silent fallback from one provider to another. The provider shown in `/api/status` is the one selected by configuration.

## Run locally

1. Copy the template:

   ```bash
   cp .env.example .env
   ```

2. Replace all `CHANGE_ME` values with unique random secrets and add the API key for your selected provider. Generate random secrets with:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Keep `.env` private and never commit it.

3. Build and start the stack:

   ```bash
   docker compose up --build -d
   docker compose ps
   ```

4. Open **http://localhost:5173** and sign in with `CEREPATH_OWNER_TOKEN` from `.env`.

Health check:

```bash
curl http://localhost:5173/api/health
```

After changing provider settings, recreate the API container:

```bash
docker compose up -d --force-recreate api
```

## API overview

All application endpoints except health and local bootstrap login require an authenticated session. Cookie-authenticated state-changing requests require the session CSRF token.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| POST | `/api/auth/login` | Local owner bootstrap login |
| GET | `/api/status` | Selected provider and runtime status |
| POST | `/api/chat` | Generate and persist one chat turn using the cognitive context pipeline |
| POST | `/api/mind/teach` | Store an explicit owner-taught knowledge item |
| GET | `/api/mind/knowledge` | List active and review-queued knowledge |
| GET | `/api/mind/recall?q=...` | Hybrid recall across owner knowledge, documents and previous conversations |
| POST | `/api/mind/feedback` | Record helpful/incomplete/incorrect feedback |
| GET | `/api/mind/state` | Inspect cognitive-kernel counters and configuration |
| POST | `/api/mind/documents` | Ingest a local document and index its text |
| GET | `/api/mind/sources` | List ingested knowledge sources |
| GET | `/api/mind/sources/{id}/download` | Download the preserved original source |
| POST | `/api/mind/sources/{id}/archive` | Exclude a source from recall without deleting its original |
| GET | `/api/mind/graph` | List owner-managed concepts and relations |
| POST | `/api/mind/concepts` | Create or update a concept |
| POST | `/api/mind/relations` | Create an owner-verified concept relation |
| GET | `/api/mind/episodic-memories` | List locally stored conversation episodes |
| GET | `/api/mind/reviews/due` | Get lessons due for retrieval practice |
| POST | `/api/mind/reviews/{knowledge_id}` | Rate recall and schedule the next review |
| GET | `/api/conversations` | List the owner's conversations |
| GET | `/api/conversations/{id}/messages` | Load one owner's conversation history |
| GET | `/api/memories` | List approved memories |
| GET | `/api/approvals` | List approval requests |
| POST | `/api/approvals` | Propose a memory add/update/delete |
| POST | `/api/approvals/{id}/decision` | Approve/reject one exact proposal |
| POST | `/api/browser/navigate` | HTTPS read-only browser navigation |

OpenAPI docs: `http://localhost:5173/api/docs`.

## Cognitive retrieval benchmark

Cerepath includes a deterministic, offline benchmark for the cognitive kernel's post-retrieval attention/ranking stage. Its synthetic fixtures cover owner-taught semantic knowledge, document passages, episodic memories, distractors with misleadingly high confidence, source-reference checks and a no-local-evidence abstention case.

Run it from the backend directory:

\`\`\`bash
python -m app.intelligence.cognitive.evaluation
\`\`\`

Run the focused regression tests:

\`\`\`bash
pytest -q tests/test_cognitive_evaluation.py
\`\`\`

The report includes precision@k, recall@k, mean reciprocal rank, nDCG@k, source-reference fidelity and abstention accuracy. Results are macro-averaged across labelled evidence cases; abstention is reported separately.

**Evaluation boundary:** this first benchmark evaluates deterministic ranking over a supplied candidate pool. It does not yet measure database candidate-generation recall, end-to-end LLM answer correctness, citation entailment, real-user privacy properties, or biological equivalence. The synthetic dataset must not be mistaken for a measured score of human-like intelligence. The next evaluation increment is an owner-reviewed golden set with expected evidence and answer-level checks.

## Tests

Backend:

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

Browser agent:

```bash
cd browser_agent
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

Egress proxy:

```bash
cd egress_proxy
python -m pip install -r requirements-dev.txt
pytest -q
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

GitHub Actions validates Python tests, frontend type-check/build, Docker Compose configuration, all container builds and PostgreSQL migration integration. The PostgreSQL integration test uses a disposable database whose name ends in `_test`; it drops and recreates that database's `public` schema.

## Known limitations / next milestones

- Chat responses are currently non-streaming.
- Document and chunk recall uses PostgreSQL full-text search, with optional local Ollama vector similarity and hybrid ranking. The vector model is configured independently of the chat LLM.
- Concept relationships are owner-created/verified. Completed chats are also indexed as local episodic memories; hosted providers receive episodic/semantic/document context only when the existing privacy opt-in is enabled.
- Taught concepts are scheduled for owner-rated active-recall reviews using an SM-2-inspired scheduler. Safe semantic consolidation, contradiction resolution, automatic concept extraction from documents and sleep-like replay remain future work.
- Semantic claims from model answers are not silently promoted into durable knowledge; broad tool orchestration and browser write actions remain future work.
- OIDC/passkeys, multi-user registration, PostgreSQL row-level security and device management are not implemented.
- No encrypted automated backups or restore drills.
- The browser remains read-only; it cannot click, type, submit forms or sign in.
- This is not a production security certification. Do not expose the local starter publicly.

Read [Architecture](docs/ARCHITECTURE.md), [Neuroscience Foundations](docs/NEUROSCIENCE_FOUNDATIONS.md), [Security](docs/SECURITY.md), [Operations](docs/OPERATIONS.md) and the [Roadmap](docs/ROADMAP.md) before extending or deploying it.

## Community

- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security reporting](SECURITY.md)

## License

Cerepath is distributed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for project attribution and third-party notices.
