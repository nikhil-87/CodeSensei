# Scripts — Operational tooling

```
scripts/
├── deploy.sh                # Production deploy: validate, secrets, models, stack, migrate, health-check
├── health-check.sh          # curl every /healthz; non-zero exit on failure
├── run-local.ps1            # Windows launcher: all / infra / backend / worker / frontend / health
├── run-local.cmd            # CMD wrapper for run-local.ps1
└── verify_multitenant.ps1   # Auth + tenant-isolation smoke test (dev-login, IDOR-safe 404s, share links)
```

Every script:

- Is idempotent (re-running causes no harm).
- Sets `set -euo pipefail` (bash) or `$ErrorActionPreference = 'Stop'` (PS).
- Logs to stdout in plain text; never writes to arbitrary paths.

For local Windows deployment, use `scripts/run-local.ps1` or `scripts/run-local.cmd` to start the full stack or individual service groups.

### Examples:
```
powershell -ExecutionPolicy Bypass -File .\scripts\run-local.ps1 -Action all
powershell -ExecutionPolicy Bypass -File .\scripts\run-local.ps1 -Action backend
powershell -ExecutionPolicy Bypass -File .\scripts\run-local.ps1 -Action frontend
powershell -ExecutionPolicy Bypass -File .\scripts\run-local.ps1 -Action health
```

### From cmd.exe, you can use:
```
scripts\run-local.cmd all
scripts\run-local.cmd backend
scripts\run-local.cmd frontend
scripts\run-local.cmd health
```