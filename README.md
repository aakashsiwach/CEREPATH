# Aakash AI — Starter Project

A cloud-first, cross-device personal intelligence platform scaffold. This first milestone runs locally so the architecture can be tested without provisioning cloud resources, using paid services, or calling external AI APIs.

> **Current status:** foundation scaffold, not a finished digital twin. Chat is intentionally a local placeholder. No LLM is configured, no messages are sent to an AI provider, and no chat transcript is persisted. The browser service can only navigate to public HTTP(S) pages using GET requests and capture a screenshot. It cannot click buttons, submit forms, type into websites, or modify external systems.

## Non-negotiable safety rules

1. Every persistent memory addition, update or deletion requires an explicit owner approval.
2. Browser navigation is read-only in this milestone. Browser requests other than GET are blocked.
3. The browser blocks non-public IP destinations to reduce SSRF risk. This is defense-in-depth, not a substitute for a hardened production network.
4. No external model API, paid service, cloud resource or deployment is configured.
5. The owner token is required for application APIs. Keep it secret; use HTTPS and a stronger identity system before exposing the app outside localhost.
6. Approval is exact-action approval. It does not grant blanket or future permissions.

Read [the architecture](docs/ARCHITECTURE.md), [security model](docs/SECURITY.md), [data model](docs/DATA_MODEL.md), and [roadmap](docs/ROADMAP.md) before extending the system.

## Requirements

- Docker Engine and Docker Compose plugin
- 4 GB RAM minimum for a small local smoke test; 8 GB+ recommended for Chromium
- A modern browser

No cloud account is needed for local development. Docker image downloads and package installation require internet access when you first build the containers, but the application itself makes no external AI API calls.

## Start locally

```bash
cp .env.example .env
```

Edit `.env` and replace all three `CHANGE_ME` values with long random strings. For example, generate tokens with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate separate values for `POSTGRES_PASSWORD`, `AAKASH_ADMIN_TOKEN`, and `BROWSER_INTERNAL_TOKEN`.

Then run:

```bash
docker compose up --build -d
docker compose ps
```

Open **http://localhost:5173**. Paste the `AAKASH_ADMIN_TOKEN` value from `.env` into the sign-in field. The token is kept in the current browser tab's `sessionStorage` and is cleared when that tab session ends.

Health check:

```bash
curl http://localhost:5173/api/health
```

Stop the stack:

```bash
docker compose down
```

Stop and remove local database contents (destructive):

```bash
docker compose down -v
```

The last command deletes the local PostgreSQL volume. Export or back up any data first.

## What works in this milestone

- Responsive React PWA shell for phone, tablet and desktop.
- Bearer-token-protected API endpoints.
- PostgreSQL with the `vector` extension enabled and a starter memory table.
- Memory add/update/delete proposals stored as pending approvals.
- Approval or rejection of the exact pending memory operation.
- Audit events for decisions and executed memory operations.
- Separate Playwright browser service for public, read-only navigation and screenshots.
- Browser-side checks for HTTP(S), public DNS/IP destinations and GET-only requests.
- Local health/status endpoints.
- No external LLM integration.

## What does not work yet

- The chat panel is a placeholder, not a reasoning model.
- No automatic profile/conversation ingestion. We must not silently turn conversations into permanent memories.
- No Gmail, GitHub, cloud, desktop or mobile-native integrations.
- No form submission, clicking, typing, purchasing, sending, deploying, committing or merging through the browser.
- No production-grade multi-user identity, OAuth, passkeys, device enrollment or remote access setup.
- No cloud infrastructure deployment scripts.

## API overview

All `/api/*` endpoints except `/api/health` require `Authorization: Bearer <AAKASH_ADMIN_TOKEN>`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/status` | Local configuration status |
| POST | `/api/chat` | Local placeholder response; does not persist the transcript |
| GET | `/api/memories` | List approved memories |
| GET | `/api/approvals` | List pending/recent approval requests |
| POST | `/api/approvals` | Propose `memory.add`, `memory.update` or `memory.delete` |
| POST | `/api/approvals/{id}/decision` | Approve or reject one exact proposal |
| POST | `/api/browser/navigate` | Read-only public web navigation and screenshot |

The API's OpenAPI documentation is available at `http://localhost:5173/api/docs` while the local stack is running.

## Tests

Run unit tests without Docker:

```bash
cd backend
python -m pip install -r requirements-dev.txt
pytest -q
cd ../browser_agent
python -m pip install -r requirements-dev.txt
pytest -q
```

Or run both suites with `make test` after installing each service's development requirements.

Run Python syntax checks:

```bash
python -m compileall backend/app browser_agent/app
```

Run frontend checks after installing dependencies:

```bash
cd frontend
npm install
npm run build
```

## Privacy and data ownership

- Memory rows belong to the owner and can be exported through PostgreSQL tools.
- Do not place credentials, API keys, private tokens or highly sensitive information into memory.
- The database volume is local in this starter. It is not backed up automatically.
- Before any remote deployment, implement encrypted off-host backups, a tested restore procedure, HTTPS, stronger authentication, rate limits, monitoring, and a threat-model review.

## License

No open-source license is included. Treat this starter as private and all-rights-reserved unless you choose a license later.
