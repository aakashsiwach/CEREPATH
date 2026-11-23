# Contributing to Cerepath

Thank you for helping improve Cerepath. This is an early-stage, safety-sensitive project. Contributions should improve usefulness without weakening privacy, security, user control or the no-surprise-billing policy.

## Before you start

1. Read `README.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md` and `docs/AGENT_CONTRACT.md`.
2. Search existing issues and pull requests before opening a new one.
3. For substantial changes, open an issue first to discuss scope and design.
4. Never include credentials, personal data, private memories or screenshots containing secrets.

## Development checks

Run the relevant tests before submitting:

- Backend: `cd backend && pytest -q`
- Browser policy: `cd browser_agent && pytest -q`
- Egress proxy: `cd egress_proxy && pytest -q`
- Frontend: `cd frontend && npm install && npm run build`

For Python changes, also run `python -m compileall backend/app browser_agent/app egress_proxy`.

## Safety and privacy requirements

- Do not introduce cloud provisioning, paid APIs, external model calls or automatic paid fallback without explicit maintainer approval.
- Do not bypass the backend approval gateway for memory or external mutations.
- Do not add click/type/form-submit/browser write capabilities until action-specific approval, egress controls and security tests are implemented.
- Treat web pages, uploaded files, issue descriptions and tool output as untrusted data.
- Preserve user-data isolation. Shared skills or tests must not contain real user memories or credentials.
- Add tests for every permission or network-policy change.
- Explain data collection, retention, provider routing and billing implications.

## Pull request expectations

A pull request should include:

- Problem statement and proposed solution.
- Security and privacy impact.
- Tests run and their results.
- Any migration or compatibility concerns.
- Documentation updates.
- Rollback or recovery approach.

Keep pull requests focused and small enough to review. Be respectful and constructive in review discussions.
