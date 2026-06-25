# Scripts — Operational tooling

```
scripts/
├── deploy.sh                # Production deploy: validate, secrets, models, stack, migrate, health-check
├── health-check.sh          # curl every /healthz; non-zero exit on failure
└── verify_multitenant.ps1   # Auth + tenant-isolation smoke test (dev-login, IDOR-safe 404s, share links)
```

Every script:

- Is idempotent (re-running causes no harm).
- Sets `set -euo pipefail` (bash) or `$ErrorActionPreference = 'Stop'` (PS).
- Logs to stdout in plain text; never writes to arbitrary paths.
