# Security model and owner permission contract

## Permission contract

The clone may read and analyze information within the explicitly configured scope. The following operations require a fresh owner approval for the exact operation and payload:

- Add, update or delete persistent memory or files.
- Send messages or submit forms.
- Create, update or delete external resources.
- Commit, push, merge, publish or deploy code.
- Spend money, make purchases or trigger billable usage.
- Change permissions, credentials, security settings or infrastructure.

An approval is one-time and payload-specific. It cannot authorize a different payload, target, resource or later action. No component may approve its own proposal. The application does not have a generic shell-execution endpoint.

## Implemented in this starter

- Owner bearer token protects application APIs.
- Browser agent has a separate internal token.
- Browser agent only navigates public HTTP(S) URLs.
- Only GET requests are routed; other methods are aborted.
- Non-global/private, loopback, link-local, reserved and multicast IP destinations are blocked.
- Memory add/update/delete operations are proposals until the owner approves them.
- Approval decision and memory mutation occur in one database transaction.
- Audit events record approvals, rejections and executed memory changes.
- API and browser services are not published directly to the host.

## Important gaps before remote exposure

This is a development scaffold, not a production security certification. Before exposing it to the internet:

1. Replace static bearer tokens with passkeys/OIDC, short-lived sessions, CSRF protection and device/session management.
2. Put the application behind HTTPS and a hardened reverse proxy/WAF.
3. Add rate limiting, brute-force protection and token rotation.
4. Use a dedicated non-root browser runtime, strict seccomp/AppArmor, read-only filesystem where practical, resource limits and egress firewall rules.
5. Add a robust DNS-rebinding-resistant egress proxy. Application-level DNS checks alone are not sufficient for a hostile browser workload.
6. Keep browser sessions isolated; do not import personal cookies or password vaults by default.
7. Add encrypted backups, restore drills, retention controls and key management.
8. Add security tests for redirects, DNS rebinding, browser subresources, prompt injection and approval replay.
9. Ensure logs never include bearer tokens, credentials, full private documents or unnecessary personal data.
10. Review dependencies and container images, pin digests for production, and scan for known vulnerabilities.

## Threats to design against

- Prompt injection in web pages and uploaded documents.
- SSRF and browser escape to private networks or cloud metadata endpoints.
- Credential leakage through logs, screenshots, browser storage or model prompts.
- Replaying or changing approval payloads.
- Unauthorized access to a lost device's session token.
- Malicious or compromised model-provider responses.
- Resource exhaustion and quota exhaustion.
- Database loss or silent corruption.

## Emergency controls (required before production)

- Global pause/kill switch for all agents.
- Revoke all owner sessions and internal tokens.
- Stop browser workers and block outbound network traffic.
- Export audit history and preserve evidence.
- Restore memory from a verified backup.
