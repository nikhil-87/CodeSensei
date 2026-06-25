# Infrastructure — Service configuration files

Configuration for stateful services that ship in the compose stack. Mounted as
read-only volumes; never edit at runtime.

```
infrastructure/
├── postgres/
│   └── init/
│       └── 01-init.sql           # CREATE EXTENSION, role grants
├── redis/
│   └── redis.conf                # AOF persistence, memory policy
├── prometheus/
│   ├── prometheus.yml            # Scrape configs (backend, worker, postgres-exporter)
│   └── rules/
│       └── alerts.yml            # Alerting rules
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml
│   │   └── dashboards/
│   │       └── default.yml
│   └── dashboards/
│       ├── api-overview.json
│       ├── worker-pipeline.json
│       └── ai-latency.json
├── nginx/
│   └── nginx.conf                # Reverse proxy + gzip + SPA fallback
└── ollama/
    └── modelfile.deepseek        # Custom system prompt overlay
```
