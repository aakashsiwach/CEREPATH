# Local operations

## Startup

```bash
cp .env.example .env
# edit .env and set unique random secrets plus your AI provider settings
docker compose up --build -d
docker compose ps
```

## Configure Google Gemini

Create an API key in Google AI Studio and set:

```dotenv
AI_PROVIDER=gemini
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
GEMINI_MODEL=gemini-3.8-flash
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
AI_HTTP_PROXY=http://egress-proxy:3128
```

The API uses Google's OpenAI-compatible Chat Completions endpoint. The key remains in the API container environment and is sent as a Bearer token; it is never passed to the browser. The Gemini requests use the HTTPS CONNECT egress proxy.

The Gemini Developer API free tier has model-specific access and rate limits. Google states that free-tier content may be used to improve its products. Do not send private memories, confidential information, credentials or sensitive personal data through a free-tier key. Check the current provider pricing and terms before using the API.

Recreate the API after changing environment values:

```bash
docker compose up -d --force-recreate api
docker compose logs -f api
```

## Configure Bynara

In `.env`, set:

```dotenv
AI_PROVIDER=bynara
BYNARA_BASE_URL=https://router.bynara.id/v1
BYNARA_MODEL=gpt-5.6-luna
BYNARA_API_KEY=YOUR_BYNARA_API_KEY
AI_HTTP_PROXY=http://egress-proxy:3128
```

Recreate the API after environment changes:

```bash
docker compose up -d --force-recreate api
docker compose logs -f api
```

The API reads the key from its environment. It is not persisted in the database or sent to the browser. Bynara receives the current prompt, recent chat context and selected approved memories. Review provider privacy and billing terms before sending personal information.

## Configure local Ollama

Install Ollama on the host, pull the model, and set:

```bash
ollama pull qwen2.5:7b
```

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODEL=qwen2.5:7b
AI_HTTP_PROXY=
```

The API container maps `host.docker.internal` to the Docker host gateway. Restart the API after editing `.env`. Ollama traffic does not use the public proxy.

## Disable AI calls

Set `AI_PROVIDER=disabled` and recreate the API container. No provider fallback occurs when the selected provider is unavailable or misconfigured.

## Logs

```bash
docker compose logs -f api
docker compose logs -f browser-agent
docker compose logs -f egress-proxy
docker compose logs -f db
```

Avoid sharing logs without checking for sensitive information first. Provider keys and prompts must not be logged.

## Database export

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > cerepath-backup.sql
```

The shell performing the export must have `POSTGRES_USER` and `POSTGRES_DB` set, or replace them with the values from `.env`. Keep the resulting file encrypted and out of Git.

## Database restore

Restore only after verifying the backup and understanding that the target database will be overwritten. Use a fresh empty database or a deliberate restore procedure. Do not blindly pipe an unknown dump into a valuable database.

## Full local reset

```bash
docker compose down -v
```

This permanently deletes the database volume. Export first.

## Troubleshooting

- `401` from login: check the token pasted into the UI matches `CEREPATH_OWNER_TOKEN` in `.env`.
- `503` from chat: check `AI_PROVIDER` and make sure the selected provider's API key/model is configured.
- `502` from chat: check the selected provider key/model, DNS and `docker compose logs egress-proxy`. The API deliberately does not return upstream response bodies.
- `403` from a provider: check the account's model entitlement, API plan and account status. Do not assume a public model catalogue guarantees key-level access.
- Gemini free-tier privacy: don't send private memory or confidential data; the provider may use free-tier content to improve products.
- Ollama connection error: ensure Ollama is running on the host, the model is pulled, and `OLLAMA_BASE_URL` points to the host runtime.
- Database unavailable: inspect `docker compose ps` and `docker compose logs db`.
- Browser unavailable: inspect browser-agent and egress-proxy logs; check shared memory and RAM.
- Frontend changes not visible: rebuild with `docker compose up --build -d web`.

## Database migrations

The Compose API service runs versioned SQL migrations at startup with `RUN_DB_MIGRATIONS=true`. Migrations are recorded in `schema_migrations`; do not edit an already-applied migration. Existing local volumes are upgraded automatically when the API starts. Back up the database before applying migrations to any installation containing valuable data.
