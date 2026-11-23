# Cerepath

**Intelligence, built together.**

Cerepath is a local-first personal AI workspace built around user-owned identity, approved memory, model-independent chat and restricted browser access. The first real chat milestone is implemented: conversations are persisted, recent history is sent to the configured OpenAI-compatible model, and relevant approved memories can be added as bounded context.

> **Status: early development.** This is a personal, single-owner local application—not a finished autonomous agent or a public multi-user service. Chat uses one configured model provider and non-streaming completions. Semantic/vector retrieval, tool orchestration, browser interaction and production identity are still future work.

## Implemented

- React + TypeScript PWA with local owner sign-in.
- FastAPI backend and PostgreSQL/pgvector.
- Revocable HTTP-only sessions and CSRF protection.
- Owner-scoped persistent conversations and messages.
- OpenAI-compatible Bynara adapter.
- OpenAI-compatible Google Gemini Developer API adapter.
- Optional local Ollama through its OpenAI-compatible API.
- Approved-memory retrieval for chat context (bounded lexical matching in this version).
- No automatic provider fallback; a missing or failing provider returns an explicit error.
- Memory add/update/delete still require your approval.
- Read-only Playwright browser, HTTPS-only navigation and CONNECT egress proxy with DNS validation/IP pinning.

## AI provider configuration

The API key belongs in the server-side `.env` file only. Never paste it into frontend code, chat, an issue, or a commit.

Select exactly one provider with `AI_PROVIDER`: `bynara`, `gemini`, `ollama`, or `disabled`. The application never silently falls back to another service.

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

The Gemini Developer API free tier offers free input/output tokens for selected models, subject to model access and rate limits. Free-tier content may be used by Google to improve its products. **Do not send private memories, confidential information, credentials or sensitive personal data through a free-tier Gemini key.** Review Google's current [pricing](https://ai.google.dev/gemini-api/docs/pricing) and [terms](https://ai.google.dev/gemini-api/terms) before enabling it. Paid-tier data handling differs; verify the terms for your actual account tier.

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
| POST | `/api/chat` | Generate and persist one chat turn |
| GET | `/api/conversations` | List the owner's conversations |
| GET | `/api/conversations/{id}/messages` | Load one owner's conversation history |
| GET | `/api/memories` | List approved memories |
| GET | `/api/approvals` | List approval requests |
| POST | `/api/approvals` | Propose a memory add/update/delete |
| POST | `/api/approvals/{id}/decision` | Approve/reject one exact proposal |
| POST | `/api/browser/navigate` | HTTPS read-only browser navigation |

OpenAPI docs: `http://localhost:5173/api/docs`.

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
- Memory retrieval is lexical and bounded; pgvector embeddings and semantic/hybrid search are not implemented yet.
- No tool execution, multi-agent orchestration, automatic memory extraction or browser write actions.
- OIDC/passkeys, multi-user registration, PostgreSQL row-level security and device management are not implemented.
- No encrypted automated backups or restore drills.
- The browser remains read-only; it cannot click, type, submit forms or sign in.
- This is not a production security certification. Do not expose the local starter publicly.

Read [Architecture](docs/ARCHITECTURE.md), [Security](docs/SECURITY.md), [Operations](docs/OPERATIONS.md) and the [Roadmap](docs/ROADMAP.md) before extending or deploying it.

## Community

- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security reporting](SECURITY.md)

## License

Cerepath is distributed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for project attribution and third-party notices.
