# Security model and owner permission contract

Cerepath is a personal intelligence workspace. Personal profiles, memories, chat history, credentials, tasks and browser sessions must remain isolated per user in any future multi-user deployment.

## Permission contract

The system may read and analyze information only within the explicitly configured scope. The following operations require fresh owner approval for the exact operation and payload:

- Add, update or delete persistent memory or files.
- Send messages or submit forms.
- Create, update or delete external resources.
- Commit, push, merge, publish or deploy code.
- Spend money, make purchases or trigger billable usage.
- Change permissions, credentials, security settings or infrastructure.

An approval is one-time and payload-specific. It cannot authorize a different payload, target, resource or later action. No component may approve its own proposal. The application does not have a generic shell-execution endpoint.

## Implemented in this starter

- One local owner identity with revocable HTTP-only sessions and CSRF validation.
- Direct bearer-token compatibility restricted to `APP_ENV=local`.
- Conversation and message records scoped to the authenticated owner in application queries and linked through an owner-aware database foreign key.
- Model provider credentials are read from the API process environment and are never sent to the frontend or stored in chat history.
- Only one configured model provider is active; there is no automatic paid-provider fallback.
- Bynara and Gemini HTTPS requests use the CONNECT-only egress proxy, which validates DNS results and pins the upstream TCP connection to public IPs on port 443.
- Optional Ollama requests target a local host runtime and bypass the public proxy.
- When Bynara or Gemini is enabled, current chat text, bounded recent conversation history and up to eight relevant approved memories can be sent to the selected provider.
- Gemini Developer API free-tier content may be used by Google to improve its products. Do not send private memories, confidential information or credentials through a free-tier Gemini key. Review the provider's current terms and pricing before enabling it.
- Browser uses a disposable context without retained cookies.
- Browser allows HTTPS on port 443 only and aborts non-GET requests.
- Browser container runs as non-root with Chromium sandbox, read-only filesystem, dropped capabilities, resource limits and seccomp.
- Memory add/update/delete operations are proposals until the owner approves them.
- Approval decision and memory mutation occur in one database transaction; audit events record decisions and executed changes.
- Database and control networks are marked internal; the egress proxy is the only service attached to the outbound network.

## Identity implementation boundary

The current release is intentionally single-owner and local-only. It does not yet implement OIDC, passkeys, account registration, email verification, recovery flows, device management UI or PostgreSQL row-level security. User IDs are attached to memory, approval, audit and chat records, and application queries are scoped to the authenticated user. This is groundwork, not a completed multi-user identity system.

## Important gaps before remote exposure

This is a development scaffold, not a production security certification. Before exposing it to the internet:

1. Replace local bootstrap authentication with reviewed OIDC/passkey authentication, account provisioning, recovery and device/session management.
2. Put the application behind HTTPS and a hardened reverse proxy/WAF.
3. Add rate limiting, brute-force protection and token rotation.
4. Review the seccomp profile whenever the Playwright image is upgraded.
5. Add host/firewall egress controls; Compose network separation is defense-in-depth, not a substitute for a hardened production network.
6. Review whether untrusted browser content can reach control-plane peers on the shared control network; further isolate control traffic.
7. Keep browser sessions isolated; do not import personal cookies or password vaults by default.
8. Add encrypted backups, restore drills, retention controls and key management.
9. Add security tests for redirects, DNS rebinding, browser subresources, prompt injection and approval replay.
10. Ensure logs never include API keys, bootstrap credentials, session cookies, CSRF tokens, full private documents or unnecessary personal data.
11. Review dependencies and container images, pin digests for production, and scan for known vulnerabilities.
12. Set explicit provider budgets and test provider behavior before using real personal data. Do not assume the model provider will not retain prompts.

## Threats to design against

- Prompt injection in web pages, memories and uploaded documents.
- SSRF, DNS rebinding and browser escape to private networks or cloud metadata endpoints.
- Credential leakage through logs, browser storage, model prompts or provider errors.
- Replaying or changing approval payloads.
- Unauthorized access to a lost device's session token.
- Malicious or compromised model-provider responses.
- Resource exhaustion and quota exhaustion.
- Database loss or silent corruption.

## Emergency controls required before production

- Global pause/kill switch for all agents.
- Revoke all owner sessions and internal tokens.
- Stop browser workers and block outbound network traffic.
- Disable the model provider by setting `AI_PROVIDER=disabled` and recreating the API container.
- Export audit history and preserve evidence.
- Restore memory from a verified backup.
