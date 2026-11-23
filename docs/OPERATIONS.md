# Local operations

## Startup

```bash
cp .env.example .env
# edit .env and set unique random secrets
docker compose up --build -d
docker compose ps
```

## Logs

```bash
docker compose logs -f api
docker compose logs -f browser-agent
docker compose logs -f db
```

## Database export

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > aakash-ai-backup.sql
```

The shell performing the export must have `POSTGRES_USER` and `POSTGRES_DB` set, or replace them with the values from `.env`. Keep the resulting file encrypted and out of Git.

## Database restore

Restore only after verifying the backup and understanding that the target database will be overwritten. Use a fresh empty database or a deliberate restore procedure. Do not blindly pipe an unknown dump into a production database.

## Full local reset

```bash
docker compose down -v
```

This permanently deletes the database volume. Export first.

## Troubleshooting

- `401`: check the token pasted into the UI matches `CEREPATH_OWNER_TOKEN` in `.env`; restart `api` after changing environment values.
- Database unavailable: `docker compose ps` and `docker compose logs db`.
- Browser unavailable: inspect `docker compose logs browser-agent` and `docker compose logs egress-proxy`; check the proxy health and Docker shared memory/RAM.
- Frontend changes not visible: rebuild with `docker compose up --build -d web`.


## Database migrations

The Compose API service runs versioned SQL migrations at startup with `RUN_DB_MIGRATIONS=true`. Migrations are recorded in `schema_migrations`; do not edit an already-applied migration. Existing local volumes are upgraded automatically when the API starts. Back up the database before applying migrations to any installation containing valuable data.
