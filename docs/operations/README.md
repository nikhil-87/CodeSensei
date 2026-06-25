# Operations Documentation

| Doc | Covers |
| --- | --- |
| [runbooks.md](runbooks.md) | Startup, shutdown, restart, and recovery procedures for every failure mode |

Related: [../troubleshooting/README.md](../troubleshooting/README.md) (symptom→fix),
[../deployment/](../deployment/) (env setup), [../backend/README.md](../backend/README.md)
(observability: `/metrics`, `/healthz`, `/readyz`).

## Observability quick reference
- **Liveness:** `GET /api/v1/healthz` (always 200 if the process is up).
- **Readiness:** `GET /api/v1/readyz` (200 only if Postgres + Redis reachable).
- **Metrics:** `GET /api/v1/metrics` (Prometheus); optional Grafana via
  `docker/docker-compose.observability.yml`.
- **Logs:** structlog JSON with `X-Request-ID`; `docker compose ... logs -f backend worker`.
