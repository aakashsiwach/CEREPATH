# Cerepath

**Intelligence, built together.**

Cerepath is an open-source foundation for a device-independent personal intelligence platform. It combines user-controlled identity and memory, model-independent reasoning, browser-based tools, verifiable skills and explicit permission controls.

> **Status: early development.** This repository is a local foundation, not a finished AI assistant or hosted service. The chat panel is a placeholder. No LLM is configured, no messages are sent to an AI provider, and no chat transcript is persisted. The browser can navigate public HTTPS pages and capture screenshots; it cannot click buttons, type into websites, submit forms or modify external systems.

## Principles

- **User-owned identity:** personal profiles, memories and credentials belong to each user.
- **Privacy by default:** do not send private data to a model provider without an explicit, informed choice.
- **Model independence:** providers are adapters, not the source of truth.
- **Evidence before confidence:** distinguish verified, inferred, untested and unknown information.
- **Approval before mutation:** every persistent add, update or delete and every external side effect needs fresh approval for the exact action and payload.
- **No silent billing:** no automatic paid fallback, upgrade or trial dependency.
- **Recoverability:** user data and tasks must be exportable and restorable.
- **Community improvement:** shared skills and software improve the platform; one user's private memories never become another user's data.

## Current milestone

- React + TypeScript PWA shell for desktop, tablet and mobile.
- FastAPI control plane with owner-token authentication for local development.
- PostgreSQL with pgvector enabled.
- Memory add/update/delete proposals stored as pending approvals.
- Approval or rejection of one exact pending memory operation.
- Audit events for decisions and executed memory operations.
- Separate Playwright browser service using disposable browser contexts.
- HTTPS port 443 only; browser routing aborts non-GET requests.
- CONNECT-only egress proxy with DNS validation and pinned public IP connections.
- Browser container runs as a non-root user with Chromium sandbox, read-only filesystem, dropped capabilities and an upstream Playwright seccomp profile.
- Browser container has no direct outbound network; only the egress proxy has an outbound network.
- No external LLM integration, cloud provisioning or paid service configuration.

This is a development security baseline, not a production security certification. Read [Security](SECURITY.md) before exposing any service remotely.

## Architecture

```text
Phone / Laptop / Desktop
          |
       Cerepath PWA
          |
       Nginx proxy
          |
      FastAPI gateway ------------------ Browser agent
          |                                  |
    PostgreSQL + pgvector              HTTPS GET navigation
          |                                  |
   Memory / approvals / audit             Egress proxy
                                             |
                                    DNS validation + IP pinning
                                             |
                                        Public Internet
```

The browser uses a disposable session. The egress proxy accepts only HTTPS CONNECT tunnels to port 443, resolves destinations and rejects non-public IP answers before connecting to the resolved IP. Browser request interception separately aborts non-GET requests. The proxy does not inspect encrypted HTTP payloads; this design reduces network exposure but is not a guarantee against a compromised browser.

Read:
- [Architecture](docs/ARCHITECTURE.md)
- [Security model](docs/SECURITY.md)
- [Agent contract](docs/AGENT_CONTRACT.md)
- [Data model](docs/DATA_MODEL.md)
- [Roadmap](docs/ROADMAP.md)
- [Quota and cost policy](docs/QUOTA_AND_COST_POLICY.md)
- [Operations](docs/OPERATIONS.md)

## Requirements

- Docker Engine and Docker Compose plugin.
- 4 GB RAM minimum for a small local smoke test; 8 GB+ recommended for Chromium.
- A modern browser.

No cloud account is needed. No external AI API is called. Initial container builds and package installation need internet access. At runtime, the backend and database have no direct internet route; the browser can reach the public web only through the restricted egress proxy.

## Run locally

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Replace every `CHANGE_ME` value with a different long random secret. Generate values with:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Set `POSTGRES_PASSWORD`, `CEREPATH_OWNER_TOKEN` and `BROWSER_INTERNAL_TOKEN` separately. Never commit `.env`.

3. Start the stack:

   ```bash
   docker compose up --build -d
   docker compose ps
   ```

4. Open **http://localhost:5173** and paste `CEREPATH_OWNER_TOKEN` from `.env` into the sign-in field.

Health check:

```bash
curl http://localhost:5173/api/health
```

Stop the stack:

```bash
docker compose down
```

Stop and delete the local database volume (destructive):

```bash
docker compose down -v
```

The last command permanently deletes local PostgreSQL contents. Export or back up data first.

## API overview

All `/api/*` endpoints except `/api/health` require `Authorization: Bearer <CEREPATH_OWNER_TOKEN>`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/status` | Local configuration status |
| POST | `/api/chat` | Placeholder response; no model call or transcript persistence |
| GET | `/api/memories` | List approved memories |
| GET | `/api/approvals` | List pending/recent approval requests |
| POST | `/api/approvals` | Propose `memory.add`, `memory.update` or `memory.delete` |
| POST | `/api/approvals/{id}/decision` | Approve or reject one exact proposal |
| POST | `/api/browser/navigate` | HTTPS read-only navigation and screenshot |

OpenAPI docs: `http://localhost:5173/api/docs`.

## Tests

Install development dependencies and run each suite:

```bash
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest -q
cd ../browser_agent
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest -q
cd ../egress_proxy
python -m pip install -r requirements-dev.txt
pytest -q
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

GitHub Actions runs Python tests, the frontend TypeScript/production build, and container build checks on pushes and pull requests.

## Community

- Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- Report vulnerabilities privately using [SECURITY.md](SECURITY.md); do not publish exploit details in an issue.
- Use the issue templates for bugs and feature proposals.

## Privacy and data ownership

- Approved memory belongs to the user account/installation.
- Do not place credentials, API keys, private tokens or highly sensitive information into memory.
- Chat transcripts are not persisted in this milestone.
- Browser page content and screenshots are returned to the current client but are not automatically saved as memories.
- Local database contents are not backed up automatically.
- Multi-user identity and tenant isolation are not implemented yet. Do not expose this starter as a public multi-user service.

## License

Cerepath is distributed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for project attribution and third-party notices.
