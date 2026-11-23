# Infrastructure status

This directory currently contains only the PostgreSQL initialization SQL. **No cloud provisioning templates, account setup, Terraform, Bicep, Pulumi or CLI deployment commands are included.**

The future hosting decision must be validated against the provider's current perpetual free allowance, inactivity/idle policies, regional capacity, storage and outbound-transfer limits. Do not rely on trial credits or promotional balances. The service must fail closed when a free quota is exhausted and must never silently enable paid fallback.
