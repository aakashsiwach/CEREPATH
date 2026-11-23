# Security model and owner permission contract

Cerepath is a community platform for personal intelligence. Personal profiles, memories, credentials, tasks and browser sessions must remain isolated per user in any multi-user deployment.

## Permission contract

The system may read and analyze information only within the explicitly configured scope. The following operations require a fresh owner approval for the exact operation and payload:

- Add, update or delete persistent memory or files.
- Send messages or submit forms.
- Create, update or delete external resources.
- Commit, push, merge, publish or deploy code.
- Spend money, make purchases or trigger billable usage.
- Change permissions, credentials, security settings or infrastructure.

An approval is one-time and payload-specific. It cannot authorize a different payload, target, resource or later action. No component may approve its own proposal. The application does not have a generic shell-execution endpoint.

## Implemented in this starter

- Owner bearer token protects application APIs (local development only).
- Browser agent has a separate internal token.
- Browser uses a disposable context without retained cookies.
- Browser allows HTTPS on port 443 only.
- Browser route handling aborts non-GET requests.
- A separate CONNECT-only proxy resolves DNS, rejects non-public addresses and connects to the validated IP to reduce DNS-rebinding risk.
- Browser container runs as the non-root `pwuser`, with Chromium sandbox enabled, a read-only root filesystem, dropped Linux capabilities, process/memory limits and a seccomp profile.
- Browser container has no direct internet route; only the egress proxy is attached to the outbound network.
- Memory add/update/delete operations are proposals until the owner approves them.
- Approval decision and memory mutation occur in one database transaction.
- Audit events record approvals, rejections and executed memory changes.
- Database and control networks are marked internal; only the proxy has an outbound network.

## Important gaps before remote exposure

This is a development scaffold, not a production security certification. Before exposing it to the internet:

1. Replace static bearer tokens with passkeys/OIDC, short-lived sessions, CSRF protection and device/session management.
2. Put the application behind HTTPS and a hardened reverse proxy/WAF.
3. Add rate limiting, brute-force protection and token rotation.
4. Review the seccomp profile whenever the Playwright image is upgraded. It is based on the upstream Playwright Docker profile and must be tested on every target architecture.
5. Add egress controls at the host/firewall layer; Compose network separation is defense-in-depth, not a substitute for a hardened production network.
6. Review whether browser page content can reach control-plane peers on the shared control network; further isolate control traffic before untrusted browsing is publicly exposed.
7. Keep browser sessions isolated; do not import personal cookies or password vaults by default.
8. Add encrypted backups, restore drills, retention controls and key management.
9. Add security tests for redirects, DNS rebinding, browser subresources, prompt injection and approval replay.
10. Ensure logs never include bearer tokens, credentials, full private documents or unnecessary personal data.
11. Review dependencies and container images, pin digests for production, and scan for known vulnerabilities.

## Threats to design against

- Prompt injection in web pages and uploaded documents.
- SSRF, DNS rebinding and browser escape to private networks or cloud metadata endpoints.
- Credential leakage through logs, screenshots, browser storage or model prompts.
- Replaying or changing approval payloads.
- Unauthorized access to a lost device's session token.
- Malicious or compromised model-provider responses.
- Resource exhaustion and quota exhaustion.
- Database loss or silent corruption.

## Emergency controls required before production

- Global pause/kill switch for all agents.
- Revoke all owner sessions and internal tokens.
- Stop browser workers and block outbound network traffic.
- Export audit history and preserve evidence.
- Restore memory from a verified backup.
