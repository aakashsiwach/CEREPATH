# Quota and cost policy

The target recurring infrastructure cost is ₹0. This starter does not connect to any paid API or cloud account.

Future components must carry a cost classification:

- `local_free`: runs on owner-controlled hardware / free allocation with no per-request bill.
- `perpetual_free_quota`: recurring free allowance with explicit limits and provider-specific availability caveats.
- `paid`: disabled unless the owner explicitly opts in.
- `trial_or_promo`: prohibited as a required dependency.

## Mandatory behavior

1. Disable automatic paid fallback and automatic plan upgrades.
2. Keep a usage ledger by provider, model, task, date and quota window.
3. Reserve quota before starting an operation when provider APIs support it.
4. Stop new calls at the configured free quota threshold; do not retry on a paid route.
5. Alert the owner before the remaining free allowance becomes insufficient.
6. Treat provider free plans as changeable; revalidate terms before deploying or changing adapters.
7. Do not claim always-on uptime from free compute. Persist task checkpoints and provide recovery instructions.
8. Never route private identity/memory data to a provider whose retention/training policy has not been reviewed and approved.
9. Never include a trial or promotional credit in the core availability calculation.

A ₹0 target is not a promise of unlimited compute, inference or guaranteed availability. When free capacity is unavailable, tasks wait or stop safely.
