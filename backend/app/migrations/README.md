# Database migrations

Migrations are applied in filename order and recorded in `schema_migrations`.
The API runs them at startup only when `RUN_DB_MIGRATIONS=true`. Docker Compose
enables this for the local stack. CI tests do not require a live PostgreSQL server.

Migrations must be additive and safe to run on databases created by earlier
Cerepath versions. Do not edit a migration after it has been applied; add a new
versioned SQL file instead.
