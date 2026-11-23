# Contributing to Aakash AI

This project is private-first and safety-sensitive. Before proposing a change:

1. Read `docs/ARCHITECTURE.md` and `SECURITY.md`.
2. Keep secrets out of the repository, issues, logs and screenshots.
3. Do not introduce cloud provisioning, paid APIs, external model calls or automatic paid fallback without explicit owner approval.
4. Do not bypass the backend approval gateway for memory or external mutations.
5. Preserve read-only browser behavior until the action approval design and its security tests are accepted.
6. Add tests for policy changes and update documentation when behavior changes.
7. Run backend tests and frontend production build locally.

Pull requests should explain the threat model, test evidence, rollback approach and any new data collected.
